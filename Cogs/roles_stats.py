# role_stats.py (ou roles_stats.py)

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select

from utils_config import GUILD_ID
from utils_roles import get_role_stats, ROLE_MAP, load_all_roles
from utils_graphs import GOOD_ROLES, EVIL_ROLES


# ==============================================================================
# Helpers
# ==============================================================================

GOOD_ROLES_SET = {r.lower() for r in GOOD_ROLES}
EVIL_ROLES_SET = {r.lower() for r in EVIL_ROLES}

ALL_ROLES = sorted(ROLE_MAP.keys())

def _role_color(role_name: str) -> int:
    if role_name.lower() in EVIL_ROLES_SET:
        return 0xe74c3c  # red
    return 0x2ecc71      # green

def _safe_int(v) -> int:
    try:
        return int(v) if v else 0
    except (ValueError, TypeError):
        return 0

def _pct(won: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{(won / total * 100):.1f}%"

def _names_list(names: list) -> str:
    if not names:
        return "—"
    return "\n".join(f"• {n}" for n in names)


# ==============================================================================
# Builds all pages for a role
# ==============================================================================

def build_role_pages(role_name: str, stats: dict) -> list[discord.Embed]:
    s = stats
    color = _role_color(role_name)
    pages = []

    how_many   = _safe_int(s.get("how_many_played"))
    won        = _safe_int(s.get("games_won"))
    lost       = _safe_int(s.get("games_lost"))
    total      = won + lost
    win_pct    = _pct(won, total)
    duo        = _safe_int(s.get("duo_games"))
    april      = _safe_int(s.get("april_fools"))
    killed     = _safe_int(s.get("killed_how_many"))
    oops       = _safe_int(s.get("oops_all_pen"))
    gawain     = _safe_int(s.get("gawain_loss"))
    nimue      = _safe_int(s.get("nimue_tie_loss"))
    p_most     = s.get("player_most", [])
    p_least    = s.get("player_least", [])

    # ------------------------------------------------------------------
    # PAGE 1 — Overview
    # ------------------------------------------------------------------
    e1 = discord.Embed(
        title=f"⚔️ {role_name}",
        color=color,
    )

    side = "Evil" if role_name.lower() in EVIL_ROLES_SET else "Good"
    e1.description = f"**Side:** {'💀 Evil' if side == 'Evil' else '✨ Good'}"

    e1.add_field(
        name="🎮 Games Played",
        value=f"**{how_many}** total\n**{duo}** duo games",
        inline=True,
    )
    e1.add_field(
        name="📊 Results",
        value=f"Won: **{won}**\nLost: **{lost}**\nWin rate: **{win_pct}**",
        inline=True,
    )
    e1.add_field(name="\u200b", value="\u200b", inline=False)

    specials = []
    if gawain > 0:
        specials.append(f"Gawain loss: **{gawain}**")
    if nimue > 0:
        specials.append(f"Nimue tie/loss: **{nimue}**")
    if april > 0:
        specials.append(f"April Fools: **{april}**")
    if oops > 0:
        specials.append(f"Oops All Pen: **{oops}**")

    if specials:
        e1.add_field(name="✨ Special Games", value="\n".join(specials), inline=False)

    e1.add_field(name="☠️ Killed by vote", value=f"**{killed}** times", inline=False)

    pages.append(e1)

    # ------------------------------------------------------------------
    # PAGE 2 — Players
    # ------------------------------------------------------------------
    e2 = discord.Embed(
        title=f"⚔️ {role_name}  —  Players",
        color=color,
    )

    e2.add_field(
        name="🏆 Played Most",
        value=_names_list(p_most) if p_most else "—",
        inline=True,
    )
    e2.add_field(
        name="📉 Played Least",
        value=_names_list(p_least) if p_least else "—",
        inline=True,
    )

    pages.append(e2)

    # ------------------------------------------------------------------
    # Footer with page numbers
    # ------------------------------------------------------------------
    total_pages = len(pages)
    labels = ["Overview", "Players"]
    for i, emb in enumerate(pages):
        emb.set_footer(text=f"Page {i+1}/{total_pages}  •  {labels[i]}  •  ⬅️ ➡️ to navigate")

    return pages


# ==============================================================================
# Paginator View (same style as general stats)
# ==============================================================================

class RolePaginatorView(View):
    def __init__(self, embeds: list, author_id: int, timeout=120):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.total_pages = len(embeds)
        self.author_id = author_id
        self.message = None

        self.prev_button = Button(emoji="⬅️", style=discord.ButtonStyle.secondary)
        self.prev_button.callback = self.previous_page
        self.add_item(self.prev_button)

        self.next_button = Button(emoji="➡️", style=discord.ButtonStyle.secondary)
        self.next_button.callback = self.next_page
        self.add_item(self.next_button)

        options = []
        labels = ["Overview", "Players"]
        for i in range(len(embeds)):
            label = labels[i] if i < len(labels) else f"Page {i+1}"
            options.append(discord.SelectOption(label=label, value=str(i)))

        self.select_menu = Select(placeholder="Jump to page...", options=options, row=1)
        self.select_menu.callback = self.jump_to_page
        self.add_item(self.select_menu)

    async def _update(self, interaction: discord.Interaction):
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
            await self._update(interaction)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You are not the command author.", ephemeral=True)
            return
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self._update(interaction)

    async def jump_to_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You are not the command author.", ephemeral=True)
            return
        selected = int(self.select_menu.values[0])
        if 0 <= selected < self.total_pages:
            self.current_page = selected
            await self._update(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except:
            pass


# ==============================================================================
# COG
# ==============================================================================

class RoleStats(commands.Cog):
    def __init__(self, client):
        self.client = client
        # Start background cache loading (non-blocking)
        self.client.loop.create_task(self._ensure_cache())

    async def _ensure_cache(self):
        """Load role cache in background using an executor."""
        await self.client.loop.run_in_executor(None, load_all_roles)

    @app_commands.command(name="role_stats", description="Show stats for a specific Avalon role")
    @app_commands.describe(role="The role name to look up")
    @app_commands.guilds(discord.Object(id=int(GUILD_ID)))
    async def role_stats(self, interaction: discord.Interaction, role: str):
        await interaction.response.defer()

        # Ensure cache is loaded (if still empty, load synchronously in executor)
        if not get_role_stats(role):
            await self.client.loop.run_in_executor(None, load_all_roles)

        # Fuzzy match: case-insensitive, partial
        role_lower = role.strip().lower()
        matched = None
        for r in ROLE_MAP:
            if r.lower() == role_lower:
                matched = r
                break
        if not matched:
            for r in ROLE_MAP:
                if role_lower in r.lower():
                    matched = r
                    break

        if not matched:
            role_list = "\n".join(f"• {r}" for r in ALL_ROLES)
            await interaction.followup.send(
                f"❌ Role **{role}** not found. Available roles:\n{role_list}",
                ephemeral=True,
            )
            return

        stats = get_role_stats(matched)
        if stats is None:
            await interaction.followup.send(
                f"❌ Stats for **{matched}** could not be loaded. Please try again later.",
                ephemeral=True,
            )
            return

        embeds = build_role_pages(matched, stats)
        view = RolePaginatorView(embeds, interaction.user.id, timeout=120)
        view.prev_button.disabled = True  # first page

        msg = await interaction.followup.send(embed=embeds[0], view=view)
        try:
            view.message = await interaction.original_response()
        except:
            view.message = msg

    @role_stats.autocomplete("role")
    async def role_autocomplete(self, interaction: discord.Interaction, current: str):
        current_lower = current.lower()
        matches = [
            app_commands.Choice(name=r, value=r)
            for r in ALL_ROLES
            if current_lower in r.lower()
        ]
        return matches[:25]

    @role_stats.error
    async def role_stats_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)


async def setup(client):
    await client.add_cog(RoleStats(client))