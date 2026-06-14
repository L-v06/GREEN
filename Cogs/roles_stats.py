import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select

from utils_config import GUILD_ID
from utils_roles import get_role_stats, ALL_ROLES
from utils_graphs import GOOD_ROLES, EVIL_ROLES


# ==============================================================================
# Helpers
# ==============================================================================

GOOD_ROLES_SET = {r.lower() for r in GOOD_ROLES}
EVIL_ROLES_SET = {r.lower() for r in EVIL_ROLES}

IGNORED_PLAYERS = {"Null", "Emma"}

def _role_color(role_name: str) -> int:
    if role_name.lower() in EVIL_ROLES_SET:
        return 0xe74c3c
    return 0x2ecc71

def _safe_int(v) -> int:
    try:
        return int(v) if v else 0
    except (ValueError, TypeError):
        return 0

def _pct(won: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{(won / total * 100):.1f}%"


def _games_block(single: int, duo: int, total: int) -> str:
    """
    Single      Duo       Total
       xx        xx         xx
    """
    w = 10
    header = f"{'Single'.center(w)}  {'Duo'.center(w)}  {'Total'.center(w)}"
    values = f"{str(single).center(w)}  {str(duo).center(w)}  {str(total).center(w)}"
    return "```\n" + header + "\n" + values + "\n```"


def _results_block(won: int, lost: int, ratio: str) -> str:
    """
    Won        Lost       Ratio
     xx         xx         xx%
    """
    w = 10
    header = f"{'Won'.center(w)}  {'Lost'.center(w)}  {'Ratio'.center(w)}"
    values = f"{str(won).center(w)}  {str(lost).center(w)}  {ratio.center(w)}"
    return "```\n" + header + "\n" + values + "\n```"


def _results_block2(gawain: int, nimue: int, april: int) -> str:
    """Retorna tabela formatada com os especiais (Gawain, Nimue, April Fools)."""
    header = f"{'Gawain':<10} {'Nimue':<10} {'April Fools':<10}"
    values = f"{gawain:<10} {nimue:<10} {april:<10}"
    return f"```\n{header}\n{values}\n```"


def _players_block(most: list, least: list, max_items: int = 5) -> str:
    """Gera um bloco de texto com listas de mais e menos jogados, sem emojis."""
    lines = []
    
    lines.append("**Most played:**")
    if most:
        for name in most[:max_items]:
            lines.append(f"- {name}")
    else:
        lines.append("*No data*")
    
    lines.append("")
    
    lines.append("**Least played:**")
    if least:
        for name in least[:max_items]:
            lines.append(f"- {name}")
    else:
        lines.append("*No data*")
    
    return "\n".join(lines)


# ==============================================================================
# Builds all pages for a SINGLE role
# ==============================================================================

def _sep(embed: discord.Embed):
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    
def build_role_pages(role_name: str, stats: dict, custom_footer_prefix: str = None) -> list[discord.Embed]:
    s = stats
    color = _role_color(role_name)
    pages = []

    # Dados brutos da planilha
    single = _safe_int(s.get("how_many_played"))   # a planilha chama de "total" mas é single
    won    = _safe_int(s.get("games_won"))
    lost   = _safe_int(s.get("games_lost"))
    total_win_loss = won + lost
    win_pct = _pct(won, total_win_loss)
    duo    = _safe_int(s.get("duo_games"))
    total_games = single + duo                     # Total real de partidas (single + duo)
    april  = _safe_int(s.get("april_fools"))
    killed = _safe_int(s.get("killed_how_many"))
    oops   = _safe_int(s.get("oops_all_pen"))
    gawain = _safe_int(s.get("gawain_loss"))
    nimue  = _safe_int(s.get("nimue_tie_loss"))

    # Players mais/menos frequentes
    p_most  = [n for n in s.get("player_most",  []) if n not in IGNORED_PLAYERS]
    p_least = [n for n in s.get("player_least", []) if n not in IGNORED_PLAYERS]

    side = "Evil" if role_name.lower() in EVIL_ROLES_SET else "Good"

    # ------------------------------------------------------------------
    # PAGE 1 — Overview
    # ------------------------------------------------------------------
    e1 = discord.Embed(
        title=f" ✨ {role_name}",
        color=color,
    )
    e1.description = f"**Side:** {' Evil' if side == 'Evil' else 'Good'}"

    # Games Played (Single, Duo, Total)
    e1.add_field(
        name="Games Played",
        value=_games_block(single, duo, total_games),
        inline=False,
    )

    # Results (Won / Lost / Ratio)
    e1.add_field(
        name="Results",
        value=_results_block(won, lost, win_pct),
        inline=False,
    )

    # Specials (só aparece se tiver algo)
    specials = []
    if gawain > 0:
        specials.append(f"Gawain loss: **{gawain}**")
    if nimue > 0:
        specials.append(f"Nimue tie/loss: **{nimue}**")
    if april > 0:
        specials.append(f"April Fools: **{april}**")
    if specials:
        e1.add_field(
            name="Special Games",
            value=_results_block2(gawain, nimue, april),
            inline=False,
        )
    if oops > 0:
        e1.add_field(name="Oops", value=f" All penpin game: {oops}", inline=False)

    e1.add_field(name=" Killed by vote", value=f"**{killed}** times", inline=False)

    pages.append(e1)

    # ------------------------------------------------------------------
    # PAGE 2 — Players
    # ------------------------------------------------------------------
    e2 = discord.Embed(
        title=f" {role_name}  —  Players",
        color=color,
    )

    e2.add_field(
        name="Players",
        value=_players_block(p_most, p_least),
        inline=False,
    )

    pages.append(e2)

    # ------------------------------------------------------------------
    # Footers
    # ------------------------------------------------------------------
    total_pages = len(pages)
    labels = ["Overview", "Players"]
    for i, emb in enumerate(pages):
        label = labels[i] if i < len(labels) else f"Page {i+1}"
        if custom_footer_prefix:
            emb.set_footer(text=f"{custom_footer_prefix}  •  Page {i+1}/{total_pages}  •  {label}  •  ⬅️ ➡️ to navigate")
        else:
            emb.set_footer(text=f"Page {i+1}/{total_pages}  •  {label}  •  ⬅️ ➡️ to navigate")

    return pages


# ==============================================================================
# Paginator View — single role
# ==============================================================================

class RolePaginatorView(View):
    def __init__(self, embeds: list, author_id: int, timeout=120):
        super().__init__(timeout=timeout)
        self.embeds       = embeds
        self.current_page = 0
        self.total_pages  = len(embeds)
        self.author_id    = author_id
        self.message      = None

        self.prev_button = Button(emoji="⬅️", style=discord.ButtonStyle.secondary)
        self.prev_button.callback = self.previous_page
        self.add_item(self.prev_button)

        self.next_button = Button(emoji="➡️", style=discord.ButtonStyle.secondary)
        self.next_button.callback = self.next_page
        self.add_item(self.next_button)

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

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass


# ==============================================================================
# Paginator View — multi-role (good / evil)
# ==============================================================================

class MultiRolePaginatorView(View):
    def __init__(self, embeds: list, role_page_map: dict, author_id: int, timeout=180):
        super().__init__(timeout=timeout)
        self.embeds       = embeds
        self.current_page = 0
        self.total_pages  = len(embeds)
        self.author_id    = author_id
        self.message      = None

        self.prev_button = Button(emoji="⬅️", style=discord.ButtonStyle.secondary)
        self.prev_button.callback = self.previous_page
        self.add_item(self.prev_button)

        self.next_button = Button(emoji="➡️", style=discord.ButtonStyle.secondary)
        self.next_button.callback = self.next_page
        self.add_item(self.next_button)

        options = [
            discord.SelectOption(label=role_name, value=str(start_idx))
            for role_name, start_idx in role_page_map.items()
        ]
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
    embeds       = []
    role_page_map = {}

    # Constrói as páginas de cada role primeiro
    for role_name in role_list:
        stats = get_role_stats(role_name)
        if stats is None:
            continue

        role_pages = build_role_pages(role_name, stats, custom_footer_prefix=role_name)
        role_page_map[role_name] = len(embeds)  # índice antes de adicionar summary
        embeds.extend(role_pages)

    # Ajusta índices (+1 por causa do summary que vai na frente)
    adjusted_map = {role: idx + 1 for role, idx in role_page_map.items()}

    # Summary page
    summary = discord.Embed(
        title=f"{side_emoji} {side_name} Roles — Summary",
        color=color,
        description="Use the **Select** menu to jump directly to a role.\n"
                    "⬅️ ➡️ to navigate pages.",
    )
    lines = [f"• **{role}** — page {idx + 1}" for role, idx in adjusted_map.items()]
    if lines:
        summary.add_field(name="Roles", value="\n".join(lines), inline=False)
    else:
        summary.description = "No role stats loaded yet. Run `/update` first."

    embeds.insert(0, summary)

    # Corrige footers com numeração global
    total = len(embeds)
    for i, emb in enumerate(embeds):
        if i == 0:
            emb.set_footer(text=f"Page {i+1}/{total}  •  Summary  •  ⬅️ ➡️ to navigate")
        else:
            old = emb.footer.text
            parts = old.split("  •  ")
            if len(parts) >= 4:
                emb.set_footer(text=f"{parts[0]}  •  Page {i+1}/{total}  •  {parts[2]}  •  {parts[3]}")
            else:
                emb.set_footer(text=f"Page {i+1}/{total}  •  {old}")

    return embeds, adjusted_map


# ==============================================================================
# COG
# ==============================================================================

class RoleStats(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="role_stats", description="Show stats for a specific Avalon role")
    @app_commands.describe(role="The role name to look up")
    @app_commands.guilds(discord.Object(id=int(GUILD_ID)))
    async def role_stats(self, interaction: discord.Interaction, role: str):
        await interaction.response.defer()

        role_lower = role.strip().lower()
        matched = next((r for r in ALL_ROLES if r.lower() == role_lower), None)
        if not matched:
            matched = next((r for r in ALL_ROLES if role_lower in r.lower()), None)

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

        embeds = build_role_pages(matched, stats)
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
        return [
            app_commands.Choice(name=r, value=r)
            for r in ALL_ROLES if current_lower in r.lower()
        ][:25]

    @role_stats.error
    async def role_stats_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)

    @app_commands.command(name="role_stats_good", description="Show stats for all Good roles in one paginated embed")
    @app_commands.guilds(discord.Object(id=int(GUILD_ID)))
    async def role_stats_good(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embeds, role_map = build_side_pages(GOOD_ROLES, "Good", 0x2ecc71)
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

    @app_commands.command(name="role_stats_evil", description="Show stats for all Evil roles in one paginated embed")
    @app_commands.guilds(discord.Object(id=int(GUILD_ID)))
    async def role_stats_evil(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embeds, role_map = build_side_pages(EVIL_ROLES, "Evil", "👿", 0xe74c3c)
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