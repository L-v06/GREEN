# cog_help.py

import discord
from discord.ext import commands
from discord import app_commands

from utils_config import GUILD_ID


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
            "To get started, just use the command below and have fun 🎲"
        ),
        color=0x2ecc71,
    )
    e1.add_field(name="/stats", value="Your personal player stats, roles, streaks, and more!", inline=False)
    e1.add_field(name="/generalstats", value="Server-wide leaderboards — who's the most sus? who GMed the most?", inline=False)
    e1.set_footer(text="i have something to say next page but this was the command you needed")
    pages.append(e1)

    # ------------------------------------------------------------------
    # PAGE 2 — Credits
    # ------------------------------------------------------------------
    e2 = discord.Embed(
        title="💚  A Big Thank You",
        description="*(thanks for getting here!)*",
        color=0x1abc9c,
    )
    e2.add_field(
        name="🔵  Blue",
        value=(
            "Blue gathered all the data, scrolling through years of game histories, "
            "roles, players, outcomes, everything. The foundation of all of this is their work."
        ),
        inline=False,
    )
    e2.add_field(
        name="🟣  Sue",
        value=(
            "Sue made magic with that data. She organized everything in a way I can't even "
            "begin to fully understand, all the cool stats, all the percentages, role tracking "
            "was her doing. Without both of them none of this would exist."
        ),
        inline=False,
    )
    e2.add_field(
        name="🎮  You",
        value=(
            "And thank you, player, for having fun, playing the games, "
            "and creating this special place. 💚"
        ),
        inline=False,
    )
    # --- Nova nota de rodapé ---
    e2.add_field(
        name="  Silly",
        value=(
            "and thank you to Silly, your games broke the bot 90% of the time 🤣 "
            "but also it is better because of it"
        ),
        inline=False,
    )
    e2.set_footer(text="ps be patient with green, it may break sometimes. DM me with bugs and I'll get it fixed as soon as I can!  ~nix")
    pages.append(e2)

    # Footer numbering
    total = len(pages)
    for i, emb in enumerate(pages):
        old = emb.footer.text or ""
        sep = "  •  " if old else ""
        emb.set_footer(text=f"Page {i+1} / {total}  •  ⬅️ ➡️ to navigate{sep}{old}")

    return pages


# ==============================================================================
# Build Pages — Admin Help
# ==============================================================================

def build_help_admin_pages() -> list[discord.Embed]:
    pages = []

    # ------------------------------------------------------------------
    # PAGE 1 — GM Tracker & General Stats
    # ------------------------------------------------------------------
    e1 = discord.Embed(
        title="🛠️  GM Tracker & General Stats",
        description="How to use the GM-side commands.",
        color=0x9b59b6,
    )
    e1.add_field(
        name="/gm_track_roles  [signup message id]",
        value=(
            "The bot will fetch everyone who signed up in that message and return "
            "their last Evil / Good game — useful for spotting long streaks before "
            "you assign roles."
        ),
        inline=False,
    )
    e1.add_field(
        name="/generalstats",
        value="Server-wide leaderboards — available to everyone, useful for a quick overview before a session.",
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
            "Pass the ID of the pink log message that Green missed. "
            "The bot will re-read and process it.\n\n"
            "⚠️ Green may take a while to respond — this is normal, just wait it out."
        ),
        inline=False,
    )
    pages.append(e2)

    # ------------------------------------------------------------------
    # PAGE 3 — Adding a New Player ID
    # ------------------------------------------------------------------
    e3 = discord.Embed(
        title="➕  Adding a New Player ID",
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

    # Footer numbering
    total = len(pages)
    for i, emb in enumerate(pages):
        old = emb.footer.text or ""
        sep = "  •  " if old else ""
        emb.set_footer(text=f"Page {i+1} / {total}  •  ⬅️ ➡️ to navigate{sep}{old}")

    return pages


# ==============================================================================
# Pagination helper
# ==============================================================================

async def _paginate(client, interaction: discord.Interaction, pages: list[discord.Embed]):
    current = 0
    msg = await interaction.followup.send(embed=pages[current])
    await msg.add_reaction("⬅️")
    await msg.add_reaction("➡️")

    def check(reaction, u):
        return (
            u == interaction.user
            and str(reaction.emoji) in ("⬅️", "➡️")
            and reaction.message.id == msg.id
        )

    while True:
        try:
            reaction, u = await client.wait_for("reaction_add", timeout=60.0, check=check)
            if str(reaction.emoji) == "➡️":
                current = (current + 1) % len(pages)
            elif str(reaction.emoji) == "⬅️":
                current = (current - 1) % len(pages)
            await msg.edit(embed=pages[current])
            await msg.remove_reaction(reaction, u)
        except Exception:
            break


# ==============================================================================
# COGs
# ==============================================================================

class Help(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="help", description="Learn what Green can do for you!")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await _paginate(self.client, interaction, build_help_pages())


class HelpAdmin(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="help_admin", description="Admin guide — GM tracker, updates, and player management.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    
    async def help_admin(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await _paginate(self.client, interaction, build_help_admin_pages())


async def setup(client):
    await client.add_cog(Help(client))
    await client.add_cog(HelpAdmin(client))