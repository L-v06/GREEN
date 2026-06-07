import asyncio
import logging
import ssl
import traceback

import aiohttp
import discord
from discord.ext import commands
from discord.app_commands import errors as app_errors   # alias for clarity

from utils_config import GUILD_ID

# ==============================================================================
# LOGGING (unchanged)
# ==============================================================================

_log = logging.getLogger("bot.errors")

_file_handler = logging.FileHandler("bot_errors.log", encoding="utf-8")
_file_handler.setLevel(logging.ERROR)
_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.WARNING)
_console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

_log.setLevel(logging.DEBUG)
_log.addHandler(_file_handler)
_log.addHandler(_console_handler)
_log.propagate = False

# ==============================================================================
# NETWORK ERROR DETECTION (unchanged)
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
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    if cause and isinstance(cause, _NETWORK_EXC):
        return True
    return False

# ==============================================================================
# RETRY UTILITY (unchanged)
# ==============================================================================

async def safe_discord_call(coro, *, max_retries: int = 4, base_delay: float = 2.0):
    for attempt in range(1, max_retries + 1):
        try:
            return await coro
        except Exception as exc:
            if not _is_network_error(exc):
                raise
            if attempt == max_retries:
                _log.error("safe_discord_call: all %d attempts failed. Last: %s: %s", max_retries, type(exc).__name__, exc)
                return None
            delay = base_delay ** attempt
            _log.warning("safe_discord_call: attempt %d/%d failed (%s). Retrying in %.0fs...", attempt, max_retries, type(exc).__name__, delay)
            await asyncio.sleep(delay)
    return None

# ==============================================================================
# INTERACTION RESPONSE HELPER (unchanged)
# ==============================================================================

async def safe_respond(
    interaction: discord.Interaction,
    content: str = None,
    *,
    embed: discord.Embed = None,
    ephemeral: bool = True,
):
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
        _log.warning("safe_respond: interaction expired. Ignoring.")
    except Exception as e:
        _log.error("safe_respond: unexpected error: %s", e)

# ==============================================================================
# ENHANCED ERROR HANDLER COG
# ==============================================================================

class ErrorHandler(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        original = getattr(error, "original", error)

        # ---- 1. Player not found (TypeError from your fuzzy logic) ----
        if isinstance(original, TypeError) and "NoneType" in str(original):
            await safe_respond(interaction, "❌ Couldn't find your name in the player list. Try using `/stats` with your in-game name.")
            return

        # ---- 2. Network errors ----
        if _is_network_error(original):
            _log.warning("Network error in command '%s': %s", interaction.command.name if interaction.command else "unknown", original)
            await safe_respond(interaction, "⚠️ A network error occurred. Please try again in a moment.")
            return

        # ---- 3. Missing required role (single role) ----
        if isinstance(original, app_errors.MissingRole):
            role_id = original.missing_role
            await safe_respond(interaction, f"❌ You need the <@&{role_id}> role to use `/{interaction.command.name}`.", ephemeral=True)
            return

        # ---- 4. Missing any of the required roles ----
        if isinstance(original, app_errors.MissingAnyRole):
            roles = ", ".join(f"<@&{role_id}>" for role_id in original.missing_roles)
            await safe_respond(interaction, f"❌ You need one of the following roles: {roles}", ephemeral=True)
            return

        # ---- 5. Command on cooldown ----
        if isinstance(original, app_errors.CommandOnCooldown):
            await safe_respond(interaction, f"⏳ Command on cooldown. Try again in {original.retry_after:.1f} seconds.", ephemeral=True)
            return

        # ---- 6. Bot missing permissions (not user) ----
        if isinstance(original, app_errors.BotMissingPermissions):
            missing = ", ".join(original.missing_permissions)
            await safe_respond(interaction, f"🤖 I'm missing required permissions: {missing}. Please check my role permissions.", ephemeral=True)
            return

        # ---- 7. Generic check failure (e.g., custom check) ----
        if isinstance(original, app_errors.CheckFailure):
            await safe_respond(interaction, "❌ You don't have permission to use this command.", ephemeral=True)
            return

        # ---- 8. MissingPermissions (Discord native permissions) ----
        if isinstance(original, discord.app_commands.MissingPermissions):
            missing = ", ".join(original.missing_permissions)
            await safe_respond(interaction, f"🚫 You're missing required permissions: {missing}", ephemeral=True)
            return

        # ---- 9. Any other unexpected error ----
        cmd_name = interaction.command.name if interaction.command else "unknown"
        _log.error("Unhandled error in app command '%s':\n%s", cmd_name, traceback.format_exc())
        await safe_respond(interaction, f"❌ An unexpected error occurred in `/{cmd_name}`. It has been logged.")

    # ---------- Prefix command error handling (unchanged, but I'll add a few more) ----------
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return

        # Missing required role (prefix commands use `commands.has_role`)
        if isinstance(error, commands.MissingRole):
            await ctx.send(f"❌ You need the <@&{error.missing_role}> role to use this command.", delete_after=10)
            return

        if isinstance(error, commands.MissingAnyRole):
            roles = ", ".join(f"<@&{role_id}>" for role_id in error.missing_roles)
            await ctx.send(f"❌ You need one of the following roles: {roles}", delete_after=10)
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Command on cooldown. Try again in {error.retry_after:.1f} seconds.", delete_after=10)
            return

        if isinstance(error, commands.BotMissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await ctx.send(f"🤖 I'm missing permissions: {missing}", delete_after=10)
            return

        if isinstance(error, commands.MissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await ctx.send(f"🚫 You're missing permissions: {missing}", delete_after=10)
            return

        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You don't have permission to use this command.", delete_after=10)
            return

        original = getattr(error, "original", error)
        if _is_network_error(original):
            _log.warning("Network error in prefix command '%s': %s", ctx.command, original)
            return

        _log.error("Unhandled error in prefix command '%s':\n%s", ctx.command, traceback.format_exc())
        await ctx.send("❌ An unexpected error occurred. It has been logged.", delete_after=10)

    @commands.Cog.listener()
    async def on_error(self, event_method: str, *args, **kwargs):
        _log.error("Error in event '%s':\n%s", event_method, traceback.format_exc())

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ ErrorHandler active — logging to bot_errors.log")


async def setup(client: commands.Bot):
    await client.add_cog(ErrorHandler(client))