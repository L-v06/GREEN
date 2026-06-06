# cog_generalstats.py

import discord
from discord.ext import commands
from discord import app_commands

from utils_config import GUILD_ID
from utils_sheets import stats_cache, nomes


# ==============================================================================
# Helpers
# ==============================================================================

def _safe_int(v):
    try:
        return int(v) if v else 0
    except (ValueError, TypeError):
        return 0


def _medal(pos: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, f"**#{pos}**")


def _build_leaderboard(
    entries: list[tuple[str, int]],
    unit: str = "",
    limit: int = 5,
) -> str:
    """Recebe lista [(name, value), ...] já ordenada e monta o texto do embed."""
    if not entries:
        return "No data available."
    lines = []
    for i, (name, val) in enumerate(entries[:limit], start=1):
        medal = _medal(i)
        lines.append(f"{medal}  **{name}**  —  {val}{(' ' + unit) if unit else ''}")
    return "\n".join(lines)


def _get_all_players() -> list[tuple[str, dict]]:
    """Retorna todos os jogadores do cache como lista de (name, stats)."""
    return [(name, data) for name, data in stats_cache.items() if isinstance(data, dict)]


# ==============================================================================
# Builders de cada página
# ==============================================================================

def _page_games_played() -> discord.Embed:
    players = _get_all_players()
    ranked = sorted(
        [(name.title(), _safe_int(s.get("total_games_played"))) for name, s in players],
        key=lambda x: x[1], reverse=True
    )
    e = discord.Embed(
        title="🎲  GAMES PLAYED",
        description="The knights who showed up the most to the Round Table.",
        color=0x2ecc71,
    )
    e.add_field(name="Top 5 Most Games Played", value=_build_leaderboard(ranked, "games", 5), inline=False)
    return e


def _page_favorite_murder() -> discord.Embed:
    players = _get_all_players()
    ranked = sorted(
        [(name.title(), _safe_int(s.get("death_toll"))) for name, s in players],
        key=lambda x: x[1], reverse=True
    )
    e = discord.Embed(
        title="🔪  FAVORITE MURDER CHOICE",
        description="These people have a *suspicious* amount of deaths.",
        color=0xe74c3c,
    )
    e.add_field(name="Top 3 Highest Death Toll", value=_build_leaderboard(ranked, "kills", 3), inline=False)
    return e


def _page_def_not_sus() -> discord.Embed:
    players = _get_all_players()
    ranked = sorted(
        [(name.title(), _safe_int(s.get("longest_good_streak"))) for name, s in players],
        key=lambda x: x[1], reverse=True
    )
    e = discord.Embed(
        title="😇  DEF NOT SUS",
        description="Purest souls in Camelot. Probably.",
        color=0x3498db,
    )
    e.add_field(name="Top 3 Longest Good Streak", value=_build_leaderboard(ranked, "games", 3), inline=False)
    e.set_footer(text="did y'all temper the wheel?")
    return e


def _page_sus_people() -> discord.Embed:
    players = _get_all_players()
    ranked = sorted(
        [(name.title(), _safe_int(s.get("longest_evil_streak"))) for name, s in players],
        key=lambda x: x[1], reverse=True
    )
    e = discord.Embed(
        title="😈  SUS PEOPLE",
        description="Morgana's most dedicated followers.",
        color=0x9b59b6,
    )
    e.add_field(name="Top 3 Longest Evil Streak", value=_build_leaderboard(ranked, "games", 3), inline=False)
    return e


def _page_gm_podium() -> discord.Embed:
    players = _get_all_players()
    ranked = sorted(
        [(name.title(), _safe_int(s.get("total_games_gmed"))) for name, s in players if _safe_int(s.get("total_games_gmed")) > 0],
        key=lambda x: x[1], reverse=True
    )
    e = discord.Embed(
        title="👑  GM PODIUM",
        description="The amazing souls who made it all possible for everyone else ( there are many of you so here is a top 5 who gmed most).",
        color=0xf39c12,
    )
    e.add_field(name="Top 5 Most Games GM'd", value=_build_leaderboard(ranked, "games GM'd", 5), inline=False)
    return e


def _page_clown_honor() -> discord.Embed:
    players = _get_all_players()

    ranked = sorted(
        [
            (
                name.title(),
                _safe_int((s.get("roles_played") or {}).get("Penpingion", 0))
            )
            for name, s in players
        ],
        key=lambda x: x[1], reverse=True
    )
    # Filtra quem nunca jogou como Penpingion
    ranked = [(n, v) for n, v in ranked if v > 0]

    e = discord.Embed(
        title="🤡  CLOWN PAGE OF HONOR",
        description="Honoring those who were lied to.",
        color=0xe91e63,
    )
    value = _build_leaderboard(ranked, "times as Penpingion", 3) if ranked else "No one has played Penpingion yet!"
    e.add_field(name="Top 3 Penpingion Players", value=value, inline=False)
    return e


# ==============================================================================
# Monta as páginas
# ==============================================================================

def build_general_pages() -> list[discord.Embed]:
    pages = [
        _page_games_played(),
        _page_favorite_murder(),
        _page_def_not_sus(),
        _page_sus_people(),
        _page_gm_podium(),
        _page_clown_honor(),
    ]

    total = len(pages)
    for i, emb in enumerate(pages):
        old = emb.footer.text or ""
        separator = "  •  " if old else ""
        emb.set_footer(text=f"Page {i+1} / {total}{separator}{old}  •  ⬅️ ➡️ to navigate")

    return pages


# ==============================================================================
# COG
# ==============================================================================

class GeneralStats(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="generalstats", description="Server-wide stats for fun")
    @commands.has_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def generalstats(self, interaction: discord.Interaction):
        await interaction.response.defer()

        pages = build_general_pages()
        total_pages  = len(pages)
        current_page = 0

        msg = await interaction.followup.send(embed=pages[current_page])
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
                reaction, u = await self.client.wait_for(
                    "reaction_add", timeout=60.0, check=check
                )

                if str(reaction.emoji) == "➡️":
                    current_page = (current_page + 1) % total_pages
                elif str(reaction.emoji) == "⬅️":
                    current_page = (current_page - 1) % total_pages

                await msg.edit(embed=pages[current_page])
                await msg.remove_reaction(reaction, u)

            except Exception:
                break


async def setup(client):
    await client.add_cog(GeneralStats(client))