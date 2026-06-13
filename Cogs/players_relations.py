import json
import discord
from discord.ext import commands
from discord import app_commands

from utils_config import _fuzzy_match_name_local, GUILD_ID
from utils_sheets import nomes, get_player_stats

with open("players_ids.json", "r", encoding="utf-8") as f:
    PLAYERS_IDS = json.load(f)


# ==============================================================================
# Helpers
# ==============================================================================
def _sep(embed: discord.Embed):
    embed.add_field(name="\u200b", value="\u200b", inline=False)


def _safe_int(v):
    try:
        return int(v) if v else 0
    except (ValueError, TypeError):
        return 0


def _top3(d: dict) -> list[tuple[str, int]]:
    """Retorna os top 3 do dicionário {nome: count}, ordenado por count desc."""
    if not d:
        return []
    sorted_items = sorted(d.items(), key=lambda x: _safe_int(x[1]), reverse=True)
    return sorted_items[:3]


def _top3_field(d: dict, label_games: str = "games") -> str:
    """Formata os top 3 em texto para um embed field."""
    top = _top3(d)
    if not top:
        return "No data yet."
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (name, count) in enumerate(top):
        medal = medals[i] if i < 3 else "▪️"
        lines.append(f"{medal} **{name}** — {count} {label_games}")
    return "\n".join(lines)


def _total_from_dict(d: dict) -> int:
    """Soma todos os valores do dicionário."""
    if not d:
        return 0
    return sum(_safe_int(v) for v in d.values())


# ==============================================================================
# Monta as páginas
# ==============================================================================

def build_relation_pages(name: str, stats: dict) -> list[discord.Embed]:
    pages = []
    s = stats

    # Dados de jogos totais (para contexto nos textos)

    gawain_won           = _safe_int(s.get("gawain_games_won"))
    nimue_win_good       = _safe_int(s.get("nimue_win_good"))
    nimue_Good_lost      = _safe_int(s.get("nimue_Good_lost"))
    gawain_good_lost     = _safe_int(s.get("gawain_good_lost"))
    good_won             = _safe_int(s.get("good_games_won"))
    good_lost            = _safe_int(s.get("good_games_lost"))

    total_good = good_won + good_lost + gawain_won + nimue_win_good + nimue_Good_lost + gawain_good_lost


    gawain_evil_lost     = _safe_int(s.get("gawain_evil_lost"))
    nimue_win_evil       = _safe_int(s.get("nimue_win_evil"))
    nimue_evil_lost      = _safe_int(s.get("nimue_evil_lost"))
    evil_won             = _safe_int(s.get("evil_games_won"))
    evil_lost            = _safe_int(s.get("evil_games_lost"))

    total_evil = evil_won + evil_lost + nimue_evil_lost + nimue_win_evil + gawain_evil_lost 



    d_nimue_won         = _safe_int(s.get("duo_nimue_games_won"))
    d_gwain_won         = _safe_int(s.get("duo_died_as_gawain"))
    d_nimue_lost        = _safe_int(s.get("duo_nimue_games_lost"))
    d_gawain_lost       = _safe_int(s.get("duo_gawain_games_lost"))
    duo_good_won        = _safe_int(s.get("duo_good_games_won"))
    duo_good_lost       = _safe_int(s.get("duo_good_games_lost"))
    duo_evil_won        = _safe_int(s.get("duo_evil_games_won"))
    duo_evil_lost       = _safe_int(s.get("duo_evil_games_lost"))

    total_duo = duo_good_won + duo_good_lost + duo_evil_won + duo_evil_lost + d_nimue_won + d_gwain_won + d_nimue_lost + d_gawain_lost

    total_games = total_good + total_evil  # approximação (pode ter sobreposição em nimue etc)


    most_played_good_with = s.get("most_played_good_with") or {}
    most_played_evil_with = s.get("most_played_evil_with") or {}
    played_with_the_most  = s.get("played_with_the_most") or {}
    paired_with_the_most  = s.get("paired_with_the_most") or {}
    duo_most_good         = s.get("duo_most_played_good_with") or {}
    duo_most_evil         = s.get("duo_most_played_evil_with") or {}

    # ------------------------------------------------------------------
    # PÁGINA 1 — Good Games
    # ------------------------------------------------------------------
    e1 = discord.Embed(
        title=f"{name.upper()}  —  Good Games",
        description=(
            f"You played **{total_good} good games** in total!\n"
            f"Here are the people you were most good with:"
        ),
        color=0x2ecc71,
    )
    e1.add_field(
        name="🛡️ Top Players",
        value=_top3_field(most_played_good_with),
        inline=False,
    )
    e1.set_footer(text="Good Games")
    pages.append(e1)

    # ------------------------------------------------------------------
    # PÁGINA 2 — Evil Games
    # ------------------------------------------------------------------
    e2 = discord.Embed(
        title=f"{name.upper()}  —  Evil Games",
        description=(
            f"You played **{total_evil} evil games** in total!\n"
            f"Here are the people you were most evil with:"
        ),
        color=0xe74c3c,
    )
    e2.add_field(
        name="🗡️ Top Players",
        value=_top3_field(most_played_evil_with),
        inline=False,
    )
    e2.set_footer(text="Evil Games")
    pages.append(e2)

    # ------------------------------------------------------------------
    # PÁGINA 3 — Played With (geral)
    # ------------------------------------------------------------------
    e3 = discord.Embed(
        title=f"{name.upper()}  —  Played With",
        description=(
            f"You played **{total_games} games** in total!\n"
            f"Here's who you shared the table with the most:"
        ),
        color=0x3498db,
    )
    e3.add_field(
        name="🎲 Top Players",
        value=_top3_field(played_with_the_most),
        inline=False,
    )
    e3.set_footer(text="Played With")
    pages.append(e3)

    # ------------------------------------------------------------------
    # PÁGINA 4 — Duo Partners
    # ------------------------------------------------------------------
    e4 = discord.Embed(
        title=f"{name.upper()}  —  Duo Partners",
        color=0x9b59b6,
    )

    if total_duo > 0:
        e4.description = (
            f"You shared a role with someone **{total_duo} times**!\n"
            f"Here's who you paired with the most:"
        )
        e4.add_field(
            name=" Most Paired With",
            value=_top3_field(paired_with_the_most),
            inline=False,
        )
        _sep(e4)
        if duo_most_good:
            e4.add_field(
                name="🛡️ Most Good as a Pair",
                value=_top3_field(duo_most_good),
                inline=False,
            )
        
            _sep(e4)

        if duo_most_evil:
            e4.add_field(
                name="🗡️ Most Evil as a Pair",
                value=_top3_field(duo_most_evil),
                inline=False,
            )

            _sep(e4)

    else:
        e4.description = "You haven't shared a role with anyone yet!"

    e4.set_footer(text="Duo Partners")
    pages.append(e4)

    # ------------------------------------------------------------------
    # Numeração dos footers
    # ------------------------------------------------------------------
    total_pages = len(pages)
    for i, emb in enumerate(pages):
        old_footer = emb.footer.text
        emb.set_footer(text=f"Page {i+1} / {total_pages}  •  {old_footer}  •  ⬅️ ➡️ to navigate")

    return pages


# ==============================================================================
# COG
# ==============================================================================

class Relations(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="relations", description="See who you've played with the most!")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def relations(self, interaction: discord.Interaction):

        target_id_str = str(interaction.user.id)
        player_nick   = PLAYERS_IDS.get(target_id_str)

        if player_nick:
            player_in_list = _fuzzy_match_name_local(player_nick, nomes)
        else:
            player_in_list = _fuzzy_match_name_local(interaction.user.display_name, nomes)

        if not player_in_list:
            await interaction.response.send_message(
                "Couldn't find your name in the player list. "
                "Are you registered in `players_ids.json`?",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        stats = get_player_stats(player_in_list)
        if not stats:
            await interaction.followup.send(
                f"Stats for **{player_in_list}** not loaded yet. Try again in a moment.",
                ephemeral=True,
            )
            return

        pages = build_relation_pages(player_in_list, stats)
        total_pages  = len(pages)
        current_page = 0

        msg = await interaction.followup.send(embed=pages[current_page])

        # Reações de navegação
        await msg.add_reaction("⬅️")
        await msg.add_reaction("➡️")

        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "0️⃣"]
        for i in range(min(total_pages, 10)):
            await msg.add_reaction(number_emojis[i])

        def check(reaction, u):
            return (
                u == interaction.user
                and reaction.message.id == msg.id
                and (
                    str(reaction.emoji) in ("⬅️", "➡️")
                    or str(reaction.emoji) in number_emojis
                )
            )

        while True:
            try:
                reaction, u = await self.client.wait_for(
                    "reaction_add", timeout=1200.0, check=check
                )

                emoji = str(reaction.emoji)
                if emoji == "➡️":
                    current_page = (current_page + 1) % total_pages
                elif emoji == "⬅️":
                    current_page = (current_page - 1) % total_pages
                else:
                    digit = emoji[0]
                    target_page_num = 10 if digit == "0" else int(digit)
                    if 1 <= target_page_num <= total_pages:
                        current_page = target_page_num - 1

                await msg.edit(embed=pages[current_page])
                await msg.remove_reaction(reaction, u)

            except Exception:
                break


async def setup(client):
    await client.add_cog(Relations(client))