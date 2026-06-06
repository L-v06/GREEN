# gm_track_role.py

import json
import discord
from discord.ext import commands
from discord import app_commands
from utils_config import GUILD_ID, ROUND_TABLE_ID, _fuzzy_match_name_local
from utils_sheets import nomes, get_player_stats

# Load the mapping from Discord user ID (as string) to player name (as typed)
with open("players_ids.json", "r", encoding="utf-8") as f:
    PLAYERS_IDS = json.load(f)  # format: {"discord_user_id_str": "PlayerNick"}

class gm_track_role(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(
        name="gm_track_role",
        description="Track last role and streaks of a player based on message reactions"
    )
    @app_commands.checks.has_role(1126393102291185744)  # role ID
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=int(GUILD_ID)))
    async def track_role(self, interaction: discord.Interaction, sign_up_message_id: str):
        await interaction.response.defer()
        sign_up_message_id = int(sign_up_message_id)
        target_channel = self.client.get_channel(int(ROUND_TABLE_ID))
        if target_channel is None:
            await interaction.followup.send(
                "Could not find the round table channel. Check ROUND_TABLE_ID.",
                ephemeral=True
            )
            return

        try:
            message = await target_channel.fetch_message(sign_up_message_id)
        except discord.NotFound:
            await interaction.followup.send(
                "Message not found. Verify the ID and that it exists in the round table channel.",
                ephemeral=True
            )
            return
        except discord.Forbidden:
            await interaction.followup.send(
                "I don't have permission to read that message.",
                ephemeral=True
            )
            return

        reactions = message.reactions
        if not reactions:
            await interaction.followup.send(
                "This message has no reactions.",
                ephemeral=True
            )
            return

        # Collect unique human users from all reactions
        all_user_ids = set()
        for reaction in reactions:
            async for user in reaction.users():
                if not user.bot:
                    all_user_ids.add(user.id)

        if not all_user_ids:
            await interaction.followup.send(
                "No human users reacted to this message.",
                ephemeral=True
            )
            return

        
        print(f"[GM_TRACK] Found {len(all_user_ids)} unique human reactors.")

        # Map Discord IDs to canonical player names (using fuzzy matching)
        players = []
        unknown_ids = []
        for uid in all_user_ids:
            uid_str = str(uid)
            nick = PLAYERS_IDS.get(uid_str)
            if not nick:
                unknown_ids.append(uid)
                continue

            matched_name = _fuzzy_match_name_local(nick, nomes)
            if matched_name is None:
                await interaction.followup.send(
                    f"Could not find a close match for **{nick}** (ID: {uid}) in the players list. "
                    "Check `players_ids.json` or the sheet names.",
                    ephemeral=True
                )
                return
            players.append(matched_name)

        if not players:
            await interaction.followup.send(
                f"None of the reacting users are registered in `players_ids.json`. "
                f"Unknown IDs: {unknown_ids}",
                ephemeral=True
            )
            return

        # Fetch stats for each player
        players_stats = []
        for name in players:
            stats = get_player_stats(name)
            if stats is None:
                await interaction.followup.send(
                    f"Player **{name}** not found in stats cache. Run `/update` first.",
                    ephemeral=True
                )
                return
            players_stats.append((name, stats))

        # Sort players alphabetically for consistent pagination order
        players_stats.sort(key=lambda x: x[0].lower())

        # Build embeds with page numbers in footer
        embeds = []
        total_players = len(players_stats)
        for idx, (name, stats) in enumerate(players_stats):
            embed = self._build_player_embed(name, stats, idx + 1, total_players)
            embeds.append(embed)

        await self._paginate_embeds(interaction, embeds)

    def _build_player_embed(self, name: str, stats: dict, page_num: int, total_pages: int) -> discord.Embed:
        embed = discord.Embed(
            title=f"📊 {name}",
            color=discord.Color.blue(),
            description=f"Last play date: **{stats.get('date_last_played', 'Unknown')}**"
        )

        # Good streak
        good_streak = stats.get('good_streak', 0)
        last_good_role = stats.get('last_good_role', 'None')
        last_good_date = stats.get('last_date_good', 'Unknown')
        embed.add_field(
            name="✨ Good Streak",
            value=f"**{good_streak}** games\nLast role: {last_good_role} ({last_good_date})",
            inline=True
        )

        # Evil streak
        evil_streak = stats.get('evil_streak', 0)
        last_evil_role = stats.get('last_evil_role', 'None')
        last_evil_date = stats.get('last_date_evil', 'Unknown')
        embed.add_field(
            name="💀 Evil Streak",
            value=f"**{evil_streak}** games\nLast role: {last_evil_role} ({last_evil_date})",
            inline=True
        )

        # Footer shows current player and total players
        embed.set_footer(text=f"Player {page_num} of {total_pages}")
        return embed

    async def _paginate_embeds(self, interaction: discord.Interaction, embeds: list):
        if not embeds:
            await interaction.followup.send("No data to display.", ephemeral=True)
            return

        current_page = 0
        total_pages = len(embeds)
        msg = await interaction.followup.send(embed=embeds[current_page])

        if total_pages == 1:
            return

        await msg.add_reaction("⬅️")
        await msg.add_reaction("➡️")

        def check(reaction, user):
            return (
                user == interaction.user
                and str(reaction.emoji) in ("⬅️", "➡️")
                and reaction.message.id == msg.id
            )

        while True:
            try:
                reaction, user = await self.client.wait_for(
                    "reaction_add", timeout=60.0, check=check
                )
                if str(reaction.emoji) == "➡️":
                    current_page = (current_page + 1) % total_pages
                elif str(reaction.emoji) == "⬅️":
                    current_page = (current_page - 1) % total_pages
                await msg.edit(embed=embeds[current_page])
                await msg.remove_reaction(reaction, user)
            except TimeoutError:
                try:
                    await msg.clear_reactions()
                except:
                    pass
                break
            except Exception:
                break

    # ------------------------------------------------------------
    # ERROR HANDLER – captura MissingRole e outros erros
    # ------------------------------------------------------------
    @track_role.error
    async def track_role_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        # 1. Missing required role (has_role)
        if isinstance(error, app_commands.MissingRole):
            role_id = error.missing_role
            await interaction.response.send_message(
                f" You need the <@&{role_id}> role to use `/gm_track_role`.",
                ephemeral=True
            )
            return

        # 2. Missing any of several roles (caso mude para has_any_role)
        if isinstance(error, app_commands.MissingAnyRole):
            roles = ", ".join(f"<@&{role_id}>" for role_id in error.missing_roles)
            await interaction.response.send_message(
                f" You need one of these roles: {roles}",
                ephemeral=True
            )
            return

        # 3. Bot missing permissions (ex: não consegue ler o canal)
        if isinstance(error, app_commands.BotMissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await interaction.response.send_message(
                f" I'm missing permissions: `{missing}`. Please check my role/permissions.",
                ephemeral=True
            )
            return

        # 4. Qualquer outro erro inesperado
        await interaction.response.send_message(
            f" An unexpected error occurred: `{error}`",
            ephemeral=True
        )
        # Opcional: registrar no console/log
        print(f"[ERROR] gm_track_role: {error}")


async def setup(client):
    await client.add_cog(gm_track_role(client))