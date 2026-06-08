import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select

from utils_config import GUILD_ID
from utils_roles import get_role_stats, ALL_ROLES
from utils_graphs import GOOD_ROLES, EVIL_ROLES


# ==============================================================================
# Helpers (unchanged)
# ==============================================================================

GOOD_ROLES_SET = {r.lower() for r in GOOD_ROLES}
EVIL_ROLES_SET = {r.lower() for r in EVIL_ROLES}

IGNORED_PLAYERS = {"Null", "Emma"}

def _role_color(role_name: str) -> int:
    if role_name.lower() in EVIL_ROLES_SET:
        return 0xe74c3c  # vermelho
    return 0x2ecc71      # verde

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
# Builds all pages for a SINGLE role
# (now accepts an optional custom footer prefix)
# ==============================================================================

def build_role_pages(role_name: str, stats: dict, custom_footer_prefix: str = None) -> list[discord.Embed]:
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

    p_most = [name for name in p_most if name not in IGNORED_PLAYERS]
    p_least = [name for name in p_least if name not in IGNORED_PLAYERS]

    # PAGE 1 — Overview
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

    # PAGE 2 — Players
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

    # Footers: either custom prefix (for multi-role) or default single-role labels
    total_pages = len(pages)
    labels = ["Overview", "Players"]
    for i, emb in enumerate(pages):
        if custom_footer_prefix:
            emb.set_footer(text=f"{custom_footer_prefix}  •  Page {i+1}/{total_pages}  •  {labels[i]}  •  ⬅️ ➡️ to navigate")
        else:
            emb.set_footer(text=f"Page {i+1}/{total_pages}  •  {labels[i]}  •  ⬅️ ➡️ to navigate")

    return pages


# ==============================================================================
# Paginator View for single-role command (unchanged)
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
            await self.message.edit(view=self)
        except:
            pass


# ==============================================================================
# Paginator View for multi-role commands (good / evil)
# ==============================================================================

class MultiRolePaginatorView(View):
    def __init__(self, embeds: list, role_page_map: dict, author_id: int, timeout=180):
        """
        embeds: full list of embeds (summary + all role pages).
        role_page_map: dict mapping role_name -> 0-based index of its first page.
        """
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
        for role_name, start_idx in role_page_map.items():
            label = role_name
            options.append(discord.SelectOption(label=label, value=str(start_idx)))

        self.select_menu = Select(placeholder="Jump to a role...", options=options, row=1)
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
            await self.message.edit(view=self)
        except:
            pass


# ==============================================================================
# Multi-role helper: build all pages for a side + summary
# ==============================================================================

def build_side_pages(role_list: list, side_name: str, side_emoji: str, color: int):
    """
    Returns (embeds, role_page_map)
      - embeds: [summary_page, role1_page1, role1_page2, role2_page1, ...]
      - role_page_map: {role_name: 0-based start page idx}
    """
    embeds = []
    role_page_map = {}

    # ---------- Summary page ----------
    summary = discord.Embed(
        title=f"{side_emoji} {side_name} Roles — Summary",
        color=color,
        description="Use the **Select** menu to jump directly to a role.\n"
                    "⬅️ ➡️ to navigate pages.",
    )

    lines = []
    for idx, role_name in enumerate(role_list):
        stats = get_role_stats(role_name)
        if stats is None:
            # Skip roles without stats; we won't add them to the summary.
            continue

        # Build role's own pages (prefix with the role name for the footer)
        prefix = f"{role_name}"
        role_pages = build_role_pages(role_name, stats, custom_footer_prefix=prefix)

        # Record the starting index of this role's first page in the full list
        start_idx = len(embeds)  # summary hasn't been added yet, but we add after.
        # We'll store a temporary tuple and resolve after summary is finalised.
        role_page_map[role_name] = start_idx  # but this is before adding summary, so it will be off by 1 later.
        # Fix later.

        # Add the role's pages to the list
        embeds.extend(role_pages)

  
    adjusted_role_page_map = {}
    for role, idx in role_page_map.items():
        adjusted_role_page_map[role] = idx + 1  # because summary will be inserted at index 0

    # Now build the summary lines with the adjusted indices (1-based page numbers for display)
    lines = []
    for role, start_idx in adjusted_role_page_map.items():
        page_number = start_idx + 1  # 1-based for user display
        lines.append(f"• **{role}** – page {page_number}")

    if not lines:
        summary.description = "No role stats loaded yet. Run `/update` first."
    else:
        summary.add_field(name="Roles", value="\n".join(lines), inline=False)

    # Insert summary at the beginning
    embeds.insert(0, summary)

    # Now adjust the footers of all embeds to show correct global page numbers
    total = len(embeds)
    for i, emb in enumerate(embeds):
     
        if i == 0:
            emb.set_footer(text=f"Page {i+1}/{total}  •  Summary  •  ⬅️ ➡️ to navigate")
        else:
            
            old_footer = emb.footer.text
          
            parts = old_footer.split("  •  ")
            if len(parts) >= 4:
                # parts[0] = RoleName, parts[1] = "Page X/2", parts[2] = Label, parts[3] = navigation
                new_page = f"Page {i+1}/{total}"
                new_footer = f"{parts[0]}  •  {new_page}  •  {parts[2]}  •  {parts[3]}"
                emb.set_footer(text=new_footer)
            else:
                # fallback
                emb.set_footer(text=f"Page {i+1}/{total}  •  {old_footer}")

    return embeds, adjusted_role_page_map


# ==============================================================================
# COG
# ==============================================================================

class RoleStats(commands.Cog):
    def __init__(self, client):
        self.client = client

    # ----------------------------------------------------------------
    # Original single-role command (unchanged)
    # ----------------------------------------------------------------
    @app_commands.command(name="role_stats", description="Show stats for a specific Avalon role")
    @app_commands.describe(role="The role name to look up")
    @app_commands.guilds(discord.Object(id=int(GUILD_ID)))
    async def role_stats(self, interaction: discord.Interaction, role: str):
        await interaction.response.defer()

        role_lower = role.strip().lower()
        matched = None
        for r in ALL_ROLES:
            if r.lower() == role_lower:
                matched = r
                break
        if not matched:
            for r in ALL_ROLES:
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
                f"❌ Stats for **{matched}** not loaded. Run `/update` first.",
                ephemeral=True,
            )
            return

        embeds = build_role_pages(matched, stats)  # no custom prefix
        view = RolePaginatorView(embeds, interaction.user.id, timeout=120)
        view.prev_button.disabled = True

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

    # ----------------------------------------------------------------
    # Good roles command
    # ----------------------------------------------------------------
    @app_commands.command(name="role_stats_good", description="Show stats for all Good roles in one paginated embed")
    @app_commands.guilds(discord.Object(id=int(GUILD_ID)))
    async def role_stats_good(self, interaction: discord.Interaction):
        await interaction.response.defer()

        embeds, role_map = build_side_pages(
            GOOD_ROLES,
            side_name="Good",
            side_emoji="✨",
            color=0x2ecc71,
        )
        if not embeds:
            await interaction.followup.send("No Good role stats available. Run `/update` first.", ephemeral=True)
            return

        view = MultiRolePaginatorView(embeds, role_map, interaction.user.id, timeout=180)
        view.prev_button.disabled = True
        msg = await interaction.followup.send(embed=embeds[0], view=view)
        try:
            view.message = await interaction.original_response()
        except:
            view.message = msg

    # ----------------------------------------------------------------
    # Evil roles command
    # ----------------------------------------------------------------
    @app_commands.command(name="role_stats_evil", description="Show stats for all Evil roles in one paginated embed")
    @app_commands.guilds(discord.Object(id=int(GUILD_ID)))
    async def role_stats_evil(self, interaction: discord.Interaction):
        await interaction.response.defer()

        embeds, role_map = build_side_pages(
            EVIL_ROLES,
            side_name="Evil",
            side_emoji="💀",
            color=0xe74c3c,
        )
        if not embeds:
            await interaction.followup.send("No Evil role stats available. Run `/update` first.", ephemeral=True)
            return

        view = MultiRolePaginatorView(embeds, role_map, interaction.user.id, timeout=180)
        view.prev_button.disabled = True
        msg = await interaction.followup.send(embed=embeds[0], view=view)
        try:
            view.message = await interaction.original_response()
        except:
            view.message = msg


async def setup(client):
    await client.add_cog(RoleStats(client))