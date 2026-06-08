import json
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
from utils_config import GUILD_ID, ROUND_TABLE_ID, _fuzzy_match_name_local
from utils_sheets import nomes, get_player_stats

with open("players_ids.json", "r", encoding="utf-8") as f:
    PLAYERS_IDS = json.load(f)


class PaginatorView(View):
    def __init__(self, embeds: list, author_id: int, timeout=120):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.total_pages = len(embeds)
        self.author_id = author_id

        # Previous / Next buttons
        self.prev_button = Button(emoji="⬅️", style=discord.ButtonStyle.secondary)
        self.prev_button.callback = self.previous_page
        self.add_item(self.prev_button)

        self.next_button = Button(emoji="➡️", style=discord.ButtonStyle.secondary)
        self.next_button.callback = self.next_page
        self.add_item(self.next_button)

        # Dropdown menu for page selection (max 25 options)
        options = []
        for i, embed in enumerate(self.embeds):
            if i == 0:
                label = "📋 Summary"
            else:
                # Extract player name from embed title (format "📊 PlayerName")
                title = embed.title
                player_name = title.replace("📊", "").strip()
                label = f"{player_name} (page {i+1})"
            options.append(discord.SelectOption(label=label, value=str(i)))
        self.select_menu = Select(placeholder="Jump to page...", options=options, row=1)
        self.select_menu.callback = self.jump_to_page
        self.add_item(self.select_menu)

    async def update_message(self, interaction: discord.Interaction):
        embed = self.embeds[self.current_page]
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == self.total_pages - 1)
        await interaction.response.edit_message(embed=embed, view=self)

    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You are not the command author.", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You are not the command author.", ephemeral=True)
            return
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.update_message(interaction)

    async def jump_to_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You are not the command author.", ephemeral=True)
            return
        selected = int(self.select_menu.values[0])
        if 0 <= selected < self.total_pages:
            self.current_page = selected
            await self.update_message(interaction)

    async def on_timeout(self):
        # Disable all components after timeout (no message stored, just disable safely)
        for item in self.children:
            item.disabled = True
        # We can't edit the original message here because we don't have its reference.
        # Discord will keep the view active but disabled – that's fine.


class gm_track_role(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(
        name="gm_track_role",
        description="Show last role and streaks for each player who reacted to a sign‑up message"
    )
    #@app_commands.checks.has_role(1126393102291185744)  # role ID
    #@app_commands.default_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=int(GUILD_ID)))
    async def track_role(self, interaction: discord.Interaction, sign_up_message_id: str):
        # Try to defer – if it fails, the interaction is dead, we can only log.
        try:
            await interaction.response.defer(ephemeral=False)
        except discord.NotFound:
            print("[ERROR] Interaction expired / not found – cannot defer.")
            return

        try:
            sign_up_message_id = int(sign_up_message_id)
        except ValueError:
            await interaction.followup.send("❌ Invalid message ID.", ephemeral=True)
            return

        target_channel = self.client.get_channel(int(ROUND_TABLE_ID))
        if not target_channel:
            await interaction.followup.send("❌ Round Table channel not found. Check ROUND_TABLE_ID.", ephemeral=True)
            return

        try:
            message = await target_channel.fetch_message(sign_up_message_id)
        except discord.NotFound:
            await interaction.followup.send("❌ Message not found. Verify the ID.", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to read that message.", ephemeral=True)
            return

        reactions = message.reactions
        if not reactions:
            await interaction.followup.send("❌ This message has no reactions.", ephemeral=True)
            return

        # Collect unique human users from all reactions
        all_user_ids = set()
        for reaction in reactions:
            async for user in reaction.users():
                if not user.bot:
                    all_user_ids.add(user.id)

        if not all_user_ids:
            await interaction.followup.send("❌ No human users reacted to this message.", ephemeral=True)
            return

        # Map Discord IDs to canonical player names (via players_ids.json)
        players = []
        for uid in all_user_ids:
            nick = PLAYERS_IDS.get(str(uid))
            if not nick:
                continue
            matched = _fuzzy_match_name_local(nick, nomes)
            if matched:
                players.append(matched)

        if not players:
            await interaction.followup.send(
                "❌ None of the reacting users are registered in `players_ids.json`. "
                "Check your mapping or run `/update` first.",
                ephemeral=True
            )
            return

        # Fetch stats for each player
        players_stats = []
        for name in players:
            stats = get_player_stats(name)
            if stats is None:
                await interaction.followup.send(
                    f"❌ Stats for **{name}** not loaded. Run `/update` first.",
                    ephemeral=True
                )
                return
            players_stats.append((name, stats))

        players_stats.sort(key=lambda x: x[0].lower())  # alphabetical order

        # ------------------------------------------------------------------
        # PAGE 1 – SUMMARY (only player names and page numbers)
        # ------------------------------------------------------------------
        summary_lines = []
        for idx, (name, _) in enumerate(players_stats, start=2):  # page 1 = summary, players start at 2
            summary_lines.append(f"• **{name}** → page {idx}")

        summary_embed = discord.Embed(
            title="📋 Player Summary",
            color=discord.Color.gold(),
            description="\n".join(summary_lines) if summary_lines else "No players found."
        )
        summary_embed.set_footer(text="Use the buttons or dropdown menu below to navigate")

        # ------------------------------------------------------------------
        # INDIVIDUAL PAGES (one embed per player)
        # ------------------------------------------------------------------
        embeds = [summary_embed]
        for name, stats in players_stats:
            embed = discord.Embed(
                title=f"📊 {name}",
                color=discord.Color.blue(),
                description=f"Last played: **{stats.get('date_last_played', 'Unknown')}**"
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
            embeds.append(embed)

        # Send with navigation view
        view = PaginatorView(embeds, interaction.user.id, timeout=120)
        await interaction.followup.send(embed=embeds[0], view=view)

    @track_role.error
    async def track_role_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        # If the interaction was never responded to, we can still send an ephemeral message.
        if not interaction.response.is_done():
            if isinstance(error, app_commands.MissingRole):
                role_id = error.missing_role
                await interaction.response.send_message(
                    f"❌ You need the <@&{role_id}> role to use `/gm_track_role`.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)
        else:
            # Interaction already responded, use followup
            try:
                if isinstance(error, app_commands.MissingRole):
                    role_id = error.missing_role
                    await interaction.followup.send(
                        f"❌ You need the <@&{role_id}> role to use `/gm_track_role`.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(f"❌ An error occurred: {error}", ephemeral=True)
            except:
                pass  # Nothing we can do


async def setup(client):
    await client.add_cog(gm_track_role(client))