# cog_reload_caches.py

import os
import discord
from discord import app_commands
from discord.ext import commands

from utils_config import (
    CACHE_FILE,
    CACHE_GAMES_FILE,
    CACHE_ROLES_FILE,
    GUILD_ID
)


class ReloadCaches(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="reload_caches",
        description="Delete local cache files and rebuild them with updated data."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))

    async def reload_caches(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # --- Deleta os arquivos de cache ---
        deleted = []
        failed_delete = []

        for cache_path in [CACHE_FILE, CACHE_GAMES_FILE, CACHE_ROLES_FILE]:
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                    deleted.append(cache_path)
                except Exception as e:
                    failed_delete.append(f"`{cache_path}`: {e}")

        # --- Reconstrói chamando as mesmas funções do on_ready ---
        from utils_sheets import load_all_players, load_all_gm_games
        from utils_roles import load_all_roles

        rebuilt = []
        errors = []

        loop = discord.utils.asyncio.get_event_loop()

        for label, fn in [
            ("stats_cache", load_all_players),
            ("roles_cache", load_all_roles),
            ("games_cache", load_all_gm_games),
        ]:
            try:
                await loop.run_in_executor(None, fn)
                rebuilt.append(label)
            except Exception as e:
                errors.append(f"`{label}`: {e}")

        # --- Monta resposta ---
        lines = []

        if deleted:
            lines.append("🗑️ **Deleted files:**")
            lines += [f"  • `{p}`" for p in deleted]
        if failed_delete:
            lines.append("⚠️ **Failed to delete:**")
            lines += [f"  • {e}" for e in failed_delete]
        if rebuilt:
            lines.append("✅ **Caches rebuilt:**")
            lines += [f"  • {r}" for r in rebuilt]
        if errors:
            lines.append("❌ **Errors during rebuild:**")
            lines += [f"  • {e}" for e in errors]

        if not lines:
            lines.append("ℹ️ No cache files found to delete.")

        lines.append("")
        lines.append("⏳ **Note:** the bot may take up to 15 minutes to fully reflect updated data.")

        await interaction.followup.send("\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReloadCaches(bot))
