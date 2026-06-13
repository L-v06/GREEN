import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button

from utils_config import GUILD_ID


# ==============================================================================
# Pagination View
# ==============================================================================

class HelpPaginatorView(View):
    def __init__(self, pages: list[discord.Embed], author_id: int, timeout=120):
        super().__init__(timeout=timeout)
        self.pages       = pages
        self.current     = 0
        self.author_id   = author_id
        self.message     = None
        self._refresh_buttons()

    def _refresh_buttons(self):
        self.clear_items()

        prev_btn = Button(emoji="⬅️", style=discord.ButtonStyle.secondary,
                          disabled=(self.current == 0))
        prev_btn.callback = self.previous_page
        self.add_item(prev_btn)

        next_btn = Button(emoji="➡️", style=discord.ButtonStyle.secondary,
                          disabled=(self.current == len(self.pages) - 1))
        next_btn.callback = self.next_page
        self.add_item(next_btn)

    async def _update(self, interaction: discord.Interaction):
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Not your command.", ephemeral=True)
            return
        if self.current > 0:
            self.current -= 1
            await self._update(interaction)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Not your command.", ephemeral=True)
            return
        if self.current < len(self.pages) - 1:
            self.current += 1
            await self._update(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass


# ==============================================================================
# Build Pages — Public Help
# ==============================================================================

def build_help_pages() -> list[discord.Embed]:
    pages = []

    # ------------------------------------------------------------------
    # PAGE 1 — Welcome
    # ------------------------------------------------------------------

    e1 = discord.Embed(
        title="🌿  Hi, I'm Green!",
        description=(
            "I'm not perfect, I might make mistakes — but I was made for you "
            "to enjoy the game!\n\n"
            "Here's everything I can do for you 🎲\n\n"
            "⬅️ ➡️ to navigate through the pages!"
        ),
        color=0x2ecc71,
    )
    e1.add_field(
        name="📖  What's in here?",
        value=(
            "**Page 2** — Your personal stats\n"
            "**Page 3** — Role stats\n"
            "**Page 4** — GM game logs\n"
            "**Page 5** — Credits 💚"
        ),
        inline=False,
    )
    e1.add_field(
        name="📊  How to navigate /stats",
        value=(
            "React with ⬅️ ➡️ to go page by page, or use the number reactions "
            "1️⃣ 2️⃣ 3️⃣ ... to jump directly to a specific page!\n"
            "The bot will remove your reaction automatically — just click again to keep going."
        ),
        inline=False,
    )

    pages.append(e1)

    # ------------------------------------------------------------------
    # PAGE 2 — Player Stats
    # ------------------------------------------------------------------
    e2 = discord.Embed(
        title="📊  Player Stats",
        description="Everything about your performance in Avalon.",
        color=0x2ecc71,
    )
    e2.add_field(
        name="/stats  [player]",
        value=(
            "Shows a full stats breakdown for any player — win rates, role history, "
            "streaks, duo stats, death logs, and more.\n\n"
            "Leave the player field empty to see your own stats!"
        ),
        inline=False,
    )
    e2.add_field(
        name="/generalstats",
        value=(
            "Server-wide leaderboards — who played the most games? "
            "who GMed the most? who's the most dangerous to vote for? "
            "Find out here."
        ),
        inline=False,
    )
    pages.append(e2)

    # ------------------------------------------------------------------
    # PAGE 3 — Role Stats
    # ------------------------------------------------------------------
    e3 = discord.Embed(
        title="🎭  Role Stats",
        description="Curious how a role performs across all games?",
        color=0x1abc9c,
    )
    e3.add_field(
        name="/role_stats  [role]",
        value=(
            "Shows stats for a specific role — how many times it's been played, "
            "win rate, which players have played it the most, and more.\n\n"
            "Use the autocomplete to search for any of the 34 roles!"
        ),
        inline=False,
    )
    pages.append(e3)

    # ------------------------------------------------------------------
    # PAGE 4 — GM Game Logs
    # ------------------------------------------------------------------
    e4 = discord.Embed(
        title="🎲  GM Game Logs",
        description="Relive every game, one session at a time.",
        color=0xD4AF37,
    )
    e4.add_field(
        name="/game_per_gm  [gm]",
        value=(
            "Shows all games GMed by a specific player.\n\n"
            "You'll get a summary with all game numbers and titles, "
            "then you can jump to any game using **View Game** — "
            "it'll show the date, outcome, co-GMs, notes, and the full player/role list.\n\n"
            "Use **Switch GM** to jump to another GM without running the command again!"
        ),
        inline=False,
    )
    e4.add_field(
        name="✏️  Edit Game  *(GMs only)*",
        value=(
            "If you GMed a game, you can add a title and notes to it directly from the embed. "
            "Changes are saved to the sheet and shared with any co-GMs automatically."
        ),
        inline=False,
    )
    pages.append(e4)

    # ------------------------------------------------------------------
    # PAGE 5 — Credits
    # ------------------------------------------------------------------
    e5 = discord.Embed(
        title="💚  A Big Thank You",
        description="*(thanks for getting here!)*",
        color=0x1abc9c,
    )
    e5.add_field(
        name="🔵  Blue",
        value=(
            "Blue gathered all the data, scrolling through years of game histories, "
            "roles, players, outcomes, everything. The foundation of all of this is their work."
        ),
        inline=False,
    )
    e5.add_field(
        name="🟣  Sue",
        value=(
            "Sue made magic with that data. She organized everything in a way I can't even "
            "begin to fully understand — all the cool stats, all the percentages, role tracking "
            "was her doing. Without both of them none of this would exist."
        ),
        inline=False,
    )
    e5.add_field(
        name="🎮  You",
        value=(
            "And thank you, player, for having fun, playing the games, "
            "and creating this special place. 💚"
        ),
        inline=False,
    )
    e5.add_field(
        name="🃏  Silly",
        value=(
            "and thank you to Silly, your games broke the bot 90% of the time 🤣 "
            "but also it is better because of it"
        ),
        inline=False,
    )
    e5.set_footer(text="ps be patient with green, it may break sometimes. DM me with bugs and I'll get it fixed as soon as I can!  ~nix")
    pages.append(e5)

    # footer numbering
    total = len(pages)
    for i, emb in enumerate(pages):
        old = emb.footer.text or ""
        sep = "  •  " if old else ""
        emb.set_footer(text=f"Page {i+1}/{total}{sep}{old}")

    return pages


# ==============================================================================
# Build Pages — Admin Help
# ==============================================================================

def build_help_admin_pages() -> list[discord.Embed]:
    pages = []

    # ------------------------------------------------------------------
    # PAGE 1 — GM Streak Tracker
    # ------------------------------------------------------------------
    e1 = discord.Embed(
        title="🛠️  GM Streak Tracker",
        description="Useful before assigning roles for a new game.",
        color=0x9b59b6,
    )
    e1.add_field(
        name="/gm_track_roles  [signup message id]",
        value=(
            "Fetch everyone who signed up in that message and return "
            "their last Evil / Good game — useful for spotting long streaks "
            "before you assign roles."
        ),
        inline=False,
    )
    pages.append(e1)

    # ------------------------------------------------------------------
    # PAGE 2 — Updating the Sheet
    # ------------------------------------------------------------------
    e2 = discord.Embed(
        title="🔄  Updating the Sheet",
        description="Use this if Green missed a log or the data looks stale.",
        color=0xe67e22,
    )
    e2.add_field(
        name="/update  [log message id]",
        value=(
            "Pass the ID of the Pink log message that Green missed. "
            "The bot will re-read and process it.\n\n"
            "⚠️ Green may take a while to respond — this is normal, just wait it out."
        ),
        inline=False,
    )
    pages.append(e2)

    # ------------------------------------------------------------------
    # PAGE 3 — Adding a New Player
    # ------------------------------------------------------------------
    e3 = discord.Embed(
        title="➕  Adding a New Player",
        description="Link a Discord account to a player name in the system.",
        color=0x3498db,
    )
    e3.add_field(
        name="/newplayerid  [name]  [discord id]",
        value=(
            "Use the name the player is most commonly called as — "
            "this is what Green will use to look them up.\n\n"
            "The Discord account ID can be copied by right-clicking their profile "
            "with Developer Mode enabled."
        ),
        inline=False,
    )
    pages.append(e3)

    # footer numbering
    total = len(pages)
    for i, emb in enumerate(pages):
        old = emb.footer.text or ""
        sep = "  •  " if old else ""
        emb.set_footer(text=f"Page {i+1}/{total}{sep}{old}")

    return pages


# ==============================================================================
# Cogs
# ==============================================================================

class Help(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="help", description="Learn what Green can do for you!")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pages = build_help_pages()
        view  = HelpPaginatorView(pages, interaction.user.id)
        msg   = await interaction.followup.send(embed=pages[0], view=view)
        try:
            view.message = await interaction.original_response()
        except:
            view.message = msg


class HelpAdmin(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="help_admin", description="Admin guide — GM tracker, updates, and player management.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def help_admin(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        pages = build_help_admin_pages()
        view  = HelpPaginatorView(pages, interaction.user.id)
        msg   = await interaction.followup.send(embed=pages[0], view=view, ephemeral=True)
        try:
            view.message = await interaction.original_response()
        except:
            view.message = msg


async def setup(client):
    await client.add_cog(Help(client))
    await client.add_cog(HelpAdmin(client))