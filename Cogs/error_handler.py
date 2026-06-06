# error_handler.py
"""
Centralized error handling for the bot.

Features:
  - Retries Discord API calls that fail due to network/SSL errors (up to 4 attempts,
    exponential backoff: 2s → 4s → 8s).
  - Distinguishes network errors (retry) from logic errors (log and move on).
  - Logs all errors to bot_errors.log with full tracebacks.
  - Sends a human-readable alert to the stats channel on critical failures.
  - Exposes safe_discord_call(coro)  — wraps any single Discord API call with retry.
  - Exposes run_protected(coro, label, client) — wraps an entire async pipeline so a
    crash there never takes down the bot loop.
  - Exposes safe_respond(interaction, ...) — responds to an interaction safely even
    if it already timed out or was already answered.
"""

import asyncio
import logging
import ssl
import traceback

import aiohttp
import discord
from discord.ext import commands

from utils_config import STATS_CHANNEL_ID

# ==============================================================================
# LOGGING
# ==============================================================================

_log = logging.getLogger("bot.errors")

_file_handler = logging.FileHandler("bot_errors.log", encoding="utf-8")
_file_handler.setLevel(logging.ERROR)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.WARNING)
_console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

_log.setLevel(logging.DEBUG)
_log.addHandler(_file_handler)
_log.addHandler(_console_handler)
_log.propagate = False

# ==============================================================================
# NETWORK ERROR DETECTION
# ==============================================================================

_NETWORK_EXC = (
    aiohttp.ClientConnectorSSLError,
    aiohttp.ClientConnectorError,
    aiohttp.ServerDisconnectedError,
    aiohttp.ClientOSError,
    aiohttp.ClientConnectionError,
    aiohttp.ClientPayloadError,
    asyncio.TimeoutError,
    ssl.SSLError,
    OSError,
    ConnectionError,
)


def _is_network_error(exc: BaseException) -> bool:
    if isinstance(exc, _NETWORK_EXC):
        return True
    if isinstance(exc, discord.HTTPException) and exc.status >= 500:
        return True
    if isinstance(exc, (discord.GatewayNotFound, discord.ConnectionClosed)):
        return True
    # SSLError sometimes surfaces wrapped inside a generic Exception on Python 3.14
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    if cause and isinstance(cause, _NETWORK_EXC):
        return True
    return False


# ==============================================================================
# RETRY UTILITY
# ==============================================================================

async def safe_discord_call(coro, *, max_retries: int = 4, base_delay: float = 2.0):
    """
    Awaits `coro` with automatic retry on transient network / SSL errors.

    Backoff: 2s → 4s → 8s → give up and return None.

    Usage:
        msg = await safe_discord_call(channel.send("hello"))
        await safe_discord_call(interaction.response.defer(ephemeral=True))
    """
    for attempt in range(1, max_retries + 1):
        try:
            return await coro
        except Exception as exc:
            if not _is_network_error(exc):
                raise
            if attempt == max_retries:
                _log.error(
                    "safe_discord_call: all %d attempts failed. Last: %s: %s",
                    max_retries, type(exc).__name__, exc,
                )
                return None
            delay = base_delay ** attempt
            _log.warning(
                "safe_discord_call: attempt %d/%d failed (%s). Retrying in %.0fs...",
                attempt, max_retries, type(exc).__name__, delay,
            )
            await asyncio.sleep(delay)

    return None


# ==============================================================================
# PROTECTED TASK RUNNER
# ==============================================================================

async def run_protected(coro, label: str = "task", client: discord.Client = None):
    """
    Runs `coro` so that any crash:
      1. Never propagates and crashes the bot.
      2. Is logged in full to bot_errors.log.
      3. Sends an alert embed to the stats channel (if `client` provided).
    """
    try:
        return await coro
    except Exception as exc:
        _log.error("run_protected [%s] crashed:\n%s", label, traceback.format_exc())
        print(f"❌ run_protected [{label}] crashed: {exc}")

        if client:
            try:
                stats_channel = client.get_channel(STATS_CHANNEL_ID)
                if stats_channel:
                    await stats_channel.send(
                        embed=discord.Embed(
                            title="⚠️ Internal Bot Error",
                            description=(
                                f"An error occurred in **{label}**:\n"
                                f"```{type(exc).__name__}: {str(exc)[:300]}```\n"
                                "The error has been logged. Some data may not have been saved — "
                                "please check the game log and use `/editgame` or `/addplayers` if needed."
                            ),
                            color=discord.Color.red(),
                        )
                    )
            except Exception:
                pass

        return None


# ==============================================================================
# INTERACTION RESPONSE HELPER
# ==============================================================================

async def safe_respond(
    interaction: discord.Interaction,
    content: str = None,
    *,
    embed: discord.Embed = None,
    ephemeral: bool = True,
):
    """
    Responds to an interaction safely:
      - Falls back to followup if already responded.
      - Retries on network errors.
      - Silently swallows InteractionExpired.
    """
    kwargs = {"ephemeral": ephemeral}
    if content:
        kwargs["content"] = content
    if embed:
        kwargs["embed"] = embed

    try:
        if interaction.response.is_done():
            await safe_discord_call(interaction.followup.send(**kwargs))
        else:
            await safe_discord_call(interaction.response.send_message(**kwargs))
    except discord.InteractionResponded:
        try:
            await safe_discord_call(interaction.followup.send(**kwargs))
        except Exception as e:
            _log.warning("safe_respond fallback failed: %s", e)
    except discord.NotFound:
        _log.warning("safe_respond: interaction expired (NotFound). Ignoring.")
    except Exception as e:
        _log.error("safe_respond: unexpected error: %s", e)


# ==============================================================================
# COG
# ==============================================================================

class ErrorHandler(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ):
        original = getattr(error, "original", error)

        if _is_network_error(original):
            _log.warning(
                "Network error in command '%s': %s",
                interaction.command.name if interaction.command else "unknown",
                original,
            )
            await safe_respond(
                interaction,
                "⚠️ A network error occurred. Please try again in a moment.",
            )
            return

        if isinstance(original, discord.app_commands.MissingPermissions):
            await safe_respond(interaction, "🚫 You don't have permission to use this command.")
            return

        cmd_name = interaction.command.name if interaction.command else "unknown"
        _log.error(
            "Unhandled error in app command '%s':\n%s",
            cmd_name,
            traceback.format_exc(),
        )
        await safe_respond(
            interaction,
            f"❌ An unexpected error occurred in `/{cmd_name}`. It has been logged.",
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You don't have permission to use this command.", delete_after=10)
            return
        original = getattr(error, "original", error)
        if _is_network_error(original):
            _log.warning("Network error in prefix command '%s': %s", ctx.command, original)
            return
        _log.error(
            "Unhandled error in prefix command '%s':\n%s",
            ctx.command,
            traceback.format_exc(),
        )

    @commands.Cog.listener()
    async def on_error(self, event_method: str, *args, **kwargs):
        _log.error("Error in event '%s':\n%s", event_method, traceback.format_exc())

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ ErrorHandler active — logging to bot_errors.log")


async def setup(client: commands.Bot):
    await client.add_cog(ErrorHandler(client))