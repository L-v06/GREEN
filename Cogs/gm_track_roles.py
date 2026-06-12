import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput

from utils_config import GUILD_ID
from utils_sheets import nomes, get_gm_games, update_game_info


# ==============================================================================
# Helpers
# ==============================================================================

PLAYER_DISPLAY = {"Null": "Player 1", "Emma": "Player 2"}


def _format_players(players: dict) -> str:
    if not players:
        return "—"
    lines = []
    for name, role in players.items():
        display = PLAYER_DISPLAY.get(name, name)
        lines.append(f"• **{display}** — {role}")
    return "\n".join(lines) if lines else "—"


# ==============================================================================
# Embeds
# ==============================================================================

def build_summary_embed(gm_name: str, jogos: list) -> discord.Embed:
    e = discord.Embed(
        title=f"🎲 {gm_name}",
        color=0xD4AF37,
        description=(
            f"**{len(jogos)} games GMed**\n\n"
            "Use **View Game** to jump to a specific game.\n"
            "⬅️ ➡️ to navigate between games."
        ),
    )

    chunk = ""
    field_count = 1
    for jogo in jogos:
        num   = jogo.get("game_number")
        title = jogo.get("title") or "no title"
        line  = f"`{num}` — {title}\n"
        if len(chunk) + len(line) > 1024:
            e.add_field(name=f"Games {field_count}", value=chunk.strip(), inline=False)
            chunk = ""
            field_count += 1
        chunk += line

    if chunk:
        label = "Games" if field_count == 1 else f"Games {field_count}"
        e.add_field(name=label, value=chunk.strip(), inline=False)

    e.set_footer(text=f"Summary  •  {gm_name}")
    return e


def build_game_embed(gm_name: str, jogo: dict, current: int, total: int) -> discord.Embed:
    num     = jogo.get("game_number")
    date    = jogo.get("date") or "—"
    title   = jogo.get("title") or "no title"
    notes   = jogo.get("notes")
    players = jogo.get("players", {})

    e = discord.Embed(
        title=f"🎲 {gm_name}  •  Game #{num} — {title}",
        color=0xD4AF37,
    )
    co_gms = jogo.get("co_gms", [])

    e.add_field(name="📅 Date", value=date, inline=False)
    if co_gms:
        e.add_field(name="💚 Co-GMs", value=", ".join(co_gms), inline=False)
    if notes:
        e.add_field(name="📝 Notes", value=notes, inline=False)
    e.add_field(name="👥 Players & Roles", value=_format_players(players), inline=False)
    e.set_footer(text=f"Game {current}/{total}  •  {gm_name}")
    return e


# ==============================================================================
# Modal — jump to game by number
# ==============================================================================

class JumpToGameModal(Modal, title="Jump to Game"):
    game_number = TextInput(
        label="Game number",
        placeholder="e.g. 7",
        min_length=1,
        max_length=4,
        required=True,
    )

    def __init__(self, view: "GMGamesView"):
        super().__init__()
        self.gm_view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            num = int(self.game_number.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)
            return

        jogos = self.gm_view.jogos
        idx = next((i for i, j in enumerate(jogos) if j.get("game_number") == num), None)

        if idx is None:
            await interaction.response.send_message(
                f"❌ Game #{num} not found. Valid range: 1–{len(jogos)}.",
                ephemeral=True,
            )
            return

        self.gm_view.current_game     = idx
        self.gm_view._showing_summary = False
        await self.gm_view._update(interaction)


# ==============================================================================
# Modal — swap GM
# ==============================================================================

class SwapGMModal(Modal, title="Switch GM"):
    gm_name = TextInput(
        label="GM name",
        placeholder="e.g. Blue",
        min_length=1,
        max_length=30,
        required=True,
    )

    def __init__(self, view: "GMGamesView"):
        super().__init__()
        self.gm_view = view

    async def on_submit(self, interaction: discord.Interaction):
        from utils_sheets import games_cache
        gm_lower = self.gm_name.value.strip().lower()
        jogos    = games_cache.get(gm_lower)

        if not jogos:
            await interaction.response.send_message(
                f"❌ No games found for **{self.gm_name.value}**.", ephemeral=True
            )
            return

        gm_display = next((n for n in nomes if n.lower() == gm_lower), self.gm_name.value.title())

        self.gm_view.gm_name          = gm_display
        self.gm_view.jogos            = jogos
        self.gm_view.current_game     = 0
        self.gm_view._showing_summary = True
        await self.gm_view._update(interaction)


# ==============================================================================
# Modal — edit game title & notes
# ==============================================================================

class EditGameModal(Modal, title="Edit Game Info"):
    game_title = TextInput(
        label="Title",
        placeholder="e.g. The Apocalypse Game",
        min_length=0,
        max_length=80,
        required=False,
    )
    game_notes = TextInput(
        label="Notes",
        placeholder="e.g. That time we had a fake Elaine",
        style=discord.TextStyle.paragraph,
        min_length=0,
        max_length=300,
        required=False,
    )

    def __init__(self, view: "GMGamesView"):
        super().__init__()
        self.gm_view = view
        jogo = view.jogos[view.current_game]
        if jogo.get("title"):
            self.game_title.default = jogo["title"]
        if jogo.get("notes"):
            self.game_notes.default = jogo["notes"]

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        jogo        = self.gm_view.jogos[self.gm_view.current_game]
        gm_name     = self.gm_view.gm_name
        game_number = jogo["game_number"]

        new_title = self.game_title.value.strip() or None
        new_notes = self.game_notes.value.strip() or None

        try:
            update_game_info(gm_name, game_number, new_title, new_notes)
        except Exception as ex:
            await interaction.followup.send(f"❌ Failed to save: {ex}", ephemeral=True)
            return

        await interaction.followup.send("✅ Game info saved!", ephemeral=True)

        await self.gm_view.message.edit(
            embed=build_game_embed(
                gm_name, jogo,
                self.gm_view.current_game + 1,
                len(self.gm_view.jogos),
            ),
            view=self.gm_view,
        )


# ==============================================================================
# View principal
# ==============================================================================

class GMGamesView(View):
    def __init__(self, gm_name: str, jogos: list, author_id: int, timeout=180):
        super().__init__(timeout=timeout)
        self.gm_name          = gm_name
        self.jogos            = jogos
        self.author_id        = author_id
        self.current_game     = 0
        self._showing_summary = True
        self.message          = None
        self._refresh_buttons()

    def _refresh_buttons(self):
        self.clear_items()

        # --- row 0 ---
        summary_btn = Button(label="📋 Summary", style=discord.ButtonStyle.secondary, row=0)
        summary_btn.callback = self.show_summary
        self.add_item(summary_btn)

        jump_btn = Button(label="🎮 View Game", style=discord.ButtonStyle.primary, row=0)
        jump_btn.callback = self.open_jump_modal
        self.add_item(jump_btn)

        swap_btn = Button(label="🔄 Switch GM", style=discord.ButtonStyle.secondary, row=0)
        swap_btn.callback = self.open_swap_modal
        self.add_item(swap_btn)

        # --- row 1 — only on game embed ---
        if not self._showing_summary:
            prev_btn = Button(
                emoji="⬅️", style=discord.ButtonStyle.secondary, row=1,
                disabled=(self.current_game == 0),
            )
            prev_btn.callback = self.previous_game
            self.add_item(prev_btn)

            next_btn = Button(
                emoji="➡️", style=discord.ButtonStyle.secondary, row=1,
                disabled=(self.current_game == len(self.jogos) - 1),
            )
            next_btn.callback = self.next_game
            self.add_item(next_btn)

            edit_btn = Button(label="✏️ Edit Game", style=discord.ButtonStyle.secondary, row=1)
            edit_btn.callback = self.open_edit_modal
            self.add_item(edit_btn)

    def _current_embed(self) -> discord.Embed:
        if self._showing_summary:
            return build_summary_embed(self.gm_name, self.jogos)
        jogo = self.jogos[self.current_game]
        return build_game_embed(self.gm_name, jogo, self.current_game + 1, len(self.jogos))

    async def _update(self, interaction: discord.Interaction):
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self._current_embed(), view=self)

    async def show_summary(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Not your command.", ephemeral=True)
            return
        self._showing_summary = True
        await self._update(interaction)

    async def open_jump_modal(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Not your command.", ephemeral=True)
            return
        await interaction.response.send_modal(JumpToGameModal(self))

    async def open_swap_modal(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Not your command.", ephemeral=True)
            return
        await interaction.response.send_modal(SwapGMModal(self))

    async def open_edit_modal(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Not your command.", ephemeral=True)
            return
        await interaction.response.send_modal(EditGameModal(self))

    async def previous_game(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Not your command.", ephemeral=True)
            return
        if self.current_game > 0:
            self.current_game -= 1
            await self._update(interaction)

    async def next_game(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Not your command.", ephemeral=True)
            return
        if self.current_game < len(self.jogos) - 1:
            self.current_game += 1
            await self._update(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass


# ==============================================================================
# Cog
# ==============================================================================

class GmGames(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="game_per_gm", description="Show games GMed by a specific player")
    @app_commands.describe(gm="The GM name to look up")
    @app_commands.guilds(discord.Object(id=int(GUILD_ID)))
    async def game_per_gm(self, interaction: discord.Interaction, gm: str):
        await interaction.response.defer()

        gm_lower = gm.strip().lower()
        jogos    = get_gm_games(gm_lower)

        if not jogos:
            await interaction.followup.send(
                f"❌ No games found for **{gm}**. Run `/update` first or check the name.",
                ephemeral=True,
            )
            return

        gm_display = next((n for n in nomes if n.lower() == gm_lower), gm.title())

        view  = GMGamesView(gm_display, jogos, interaction.user.id)
        embed = build_summary_embed(gm_display, jogos)

        msg = await interaction.followup.send(embed=embed, view=view)
        try:
            view.message = await interaction.original_response()
        except:
            view.message = msg

    @game_per_gm.autocomplete("gm")
    async def gm_autocomplete(self, interaction: discord.Interaction, current: str):
        from utils_sheets import games_cache
        current_lower = current.lower()
        matches = [
            app_commands.Choice(name=name.title(), value=name.lower())
            for name in games_cache.keys()
            if current_lower in name.lower()
        ]
        return matches[:25]

    @game_per_gm.error
    async def game_per_gm_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)


async def setup(client):
    await client.add_cog(GmGames(client))