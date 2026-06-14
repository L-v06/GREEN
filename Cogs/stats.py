import io
import json
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime

from utils_config import _fuzzy_match_name_local, GUILD_ID
from utils_sheets import nomes, get_player_stats
from utils_graphs import (
    make_page1_graph, make_votes_graph, make_gm_graphs,
    make_good_roles_graph, make_evil_roles_graph,
    GOOD_ROLES, EVIL_ROLES
)

load_dotenv()

with open("players_ids.json", "r", encoding="utf-8") as f:
    PLAYERS_IDS = json.load(f)


# ==============================================================================
# Helpers
# ==============================================================================

def _safe_int(v):
    try:
        return int(v) if v else 0
    except (ValueError, TypeError):
        return 0

def _add(embed: discord.Embed, name: str, value, inline: bool = True):
    embed.add_field(name=name, value=str(value) if value else "—", inline=inline)

def _row2(embed: discord.Embed, f1: tuple, f2: tuple):
    _add(embed, f1[0], f1[1], inline=True)
    _add(embed, f2[0], f2[1], inline=True)

def _row1(embed: discord.Embed, name: str, value):
    _add(embed, name, value, inline=False)

def _sep(embed: discord.Embed):
    embed.add_field(name="\u200b", value="\u200b", inline=False)

def get_time_ago(date_str) -> str:
    if not date_str:
        return "—"
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(str(date_str).strip(), fmt)
            now = datetime.now()
            diff_days = (now - dt).days
            if diff_days < 0:
                return "0 months"
            years = diff_days // 365
            months = (diff_days % 365) // 30
            if years > 0:
                if months > 0:
                    y_lbl = "years" if years > 1 else "year"
                    m_lbl = "months" if months > 1 else "month"
                    return f"{years} {y_lbl} and {months} {m_lbl}"
                y_lbl = "years" if years > 1 else "year"
                return f"{years} {y_lbl}"
            else:
                m_lbl = "months" if months > 1 else "month"
                return f"{months} {m_lbl}"
        except ValueError:
            continue
    return "—"


# ==============================================================================
# Monta as páginas — embeds + gráficos
# ==============================================================================

def build_pages(name: str, stats: dict) -> list[tuple[discord.Embed, list]]:
    pages = []
    s = stats

    # ------------------------------------------------------------------
    # PÁGINA 1 — General Stats (graph)
    # ------------------------------------------------------------------
    e1 = discord.Embed(title=f"{name.upper()}", color=0x2ecc71)
    e1.set_image(url="attachment://graph.png")
    e1.set_footer(text="General Stats")
    pages.append((e1, [make_page1_graph(s)]))

    # ------------------------------------------------------------------
    # PÁGINA 2 — Streaks & Voting (graph)
    # ------------------------------------------------------------------
    e2 = discord.Embed(title=f"{name.upper()}  —  Streaks & Voting", color=0x3498db)

    _row1(e2, "Current Game Streak", s.get("current_game_streak"))

    def streak_format(evil_val, good_val):
        e_val = str(evil_val) if evil_val else "-"
        g_val = str(good_val) if good_val else "-"
        return f"```\nAs Evil      As Good\n{e_val:<12} {g_val}\n```"

    e2.add_field(
        name="Longest Streak",
        value=streak_format(s.get("longest_evil_streak"), s.get("longest_good_streak")),
        inline=False,
    )

    death_toll = s.get("death_toll") or "0"
    votes_in = s.get("how_many_times_voted") or "0"

    gawain_deaths = _safe_int(s.get("died_as_gawain")) + _safe_int(s.get("duo_died_as_gawain"))
    nimue_deaths  = _safe_int(s.get("died_as_nimue")) + _safe_int(s.get("duo_died_as_nimue"))

    death_lines = [f"You were killed **{death_toll} TIMES**"]
    if gawain_deaths > 0:
        death_lines.append(f" As Gawain (you won!): **{gawain_deaths}**")
    if nimue_deaths > 0:
        death_lines.append(f" As Nimue (draw): **{nimue_deaths}**")

    e2.add_field(name="Deaths", value="\n".join(death_lines), inline=False)
    _row1(e2, "Votes", f"Team votes you were in : **{votes_in}**")
    e2.set_image(url="attachment://graph.png")
    e2.set_footer(text="Streaks & Voting")
    pages.append((e2, [make_votes_graph(s)]))

    # ------------------------------------------------------------------
    # PÁGINA 3 — GM Stats (só aparece se o jogador tiver mestrado algo)
    # ------------------------------------------------------------------
    gm_games = _safe_int(s.get("total_games_gmed"))
    if gm_games > 0:
        gm_bar_buf, gm_pie_buf = make_gm_graphs(s)

        e3a = discord.Embed(title=f"{name.upper()}  —  GM Stats", color=0x9b59b6)
        _row1(e3a, "Total Games GM'd", s.get("total_games_gmed"))
        e3a.set_image(url="attachment://graph.png")
        e3a.set_footer(text="GM Modes: Single / Duo / Triple")
        pages.append((e3a, [gm_bar_buf]))

        e3b = discord.Embed(title=f"{name.upper()}  —  Player Modes", color=0x9b59b6)
        e3b.set_image(url="attachment://graph.png")
        e3b.set_footer(text="Player Modes: Solo / Pairs / Mixed")
        pages.append((e3b, [gm_pie_buf]))

    # ------------------------------------------------------------------
    # PÁGINA 4 — Extra Info (Dates and Roles)
    # ------------------------------------------------------------------
    e4 = discord.Embed(title=f"{name.upper()}  —  Extra Info", color=0xf39c12)

    started_date = s.get("date_started_playing") or "—"
    time_ago = get_time_ago(started_date)

    _row1(e4, "You started playing in", started_date)
    _row1(e4, "That's...", f"**{time_ago}** ago !!!")
    _row1(e4, "Your last game was in", s.get("date_last_played") or "—")
    _sep(e4)

    def dates_format(good_date, evil_date):
        g_date = str(good_date) if good_date else "-"
        e_date = str(evil_date) if evil_date else "-"
        return f"```\nGood         Evil\n{g_date:<12} {e_date}\n```"

    e4.add_field(
        name="Last played date",
        value=dates_format(s.get("last_date_good"), s.get("last_date_evil")),
        inline=False,
    )
    _sep(e4)
    _row2(
        e4,
        ("Last Good Role", s.get("last_good_role")),
        ("Last Evil Role", s.get("last_evil_role")),
    )
    _sep(e4)
    _row1(e4, "Everyone Wins Games", s.get("everyone_wins_games"))
    e4.set_footer(text="Extra Info")
    pages.append((e4, []))

    # ------------------------------------------------------------------
    # PÁGINA 5 — Duo Stats
    # ------------------------------------------------------------------
    e5 = discord.Embed(title=f"{name.upper()}  —  Duo Stats", color=0xe91e63)

    def duo_format(evil_val, good_val):
        e_val = str(evil_val) if evil_val else "-"
        g_val = str(good_val) if good_val else "-"
        return f"```\nEvil         Good\n{e_val:<12} {g_val}\n```"

    e5.add_field(
        name="Duo Games Won",
        value=duo_format(s.get("duo_evil_games_won"), s.get("duo_good_games_won")),
        inline=False,
    )
    e5.add_field(
        name="Duo Games Lost",
        value=duo_format(s.get("duo_evil_games_lost"), s.get("duo_good_games_lost")),
        inline=False,
    )

    evil_role_most = s.get("duo_evil_role_won_most") or "-"
    good_role_most = s.get("duo_good_role_won_most") or "-"
    e5.add_field(
        name="Duo Won Most As",
        value=f"**Evil:** {evil_role_most}\n**Good:** {good_role_most}",
        inline=False,
    )

    d_g_won       = _safe_int(s.get("duo_good_games_won"))
    d_e_won       = _safe_int(s.get("duo_evil_games_won"))
    d_nimue_won   = _safe_int(s.get("duo_nimue_games_won"))
    d_gwain_won   = _safe_int(s.get("duo_died_as_gawain"))
    d_g_lost      = _safe_int(s.get("duo_good_games_lost"))
    d_e_lost      = _safe_int(s.get("duo_evil_games_lost"))
    d_nimue_lost  = _safe_int(s.get("duo_nimue_games_lost"))
    d_gawain_lost = _safe_int(s.get("duo_gawain_games_lost"))

    total_duo_won   = d_g_won + d_e_won + d_nimue_won + d_gwain_won
    total_duo_games = d_g_won + d_e_won + d_g_lost + d_e_lost + d_nimue_lost + d_gawain_lost + d_gwain_won + d_nimue_won
    duo_ratio = f"{(total_duo_won / total_duo_games * 100):.1f}%" if total_duo_games > 0 else "0%"

    e5.add_field(name="Duo Mixed Win Ratio", value=f"**{duo_ratio}**", inline=False)

    e5.add_field(
        name="Duo Died For",
        value=duo_format(s.get("duo_died_for_evil"), s.get("duo_died_for_good")),
        inline=False,
    )

    duo_died = (
        _safe_int(s.get("duo_died_for_good"))
        + _safe_int(s.get("duo_died_for_evil"))
        + d_gwain_won
        + _safe_int(s.get("duo_died_as_nimue"))
    )
    duo_killed_correctly = _safe_int(s.get("duo_was_killed_correctly"))
    if duo_died > 0:
        e5.add_field(
            name="Duo Deaths",
            value=f"You died **{duo_died}** times in duo games.",
            inline=False,
        )
        e5.add_field(
            name="Duo Correct Kills",
            value=f"You were killed correctly **{duo_killed_correctly}** times.",
            inline=False,
        )
    else:
        e5.add_field(name="Duo Deaths", value="No deaths in duo games.", inline=False)

    e5.set_footer(text="Duo Stats")
    pages.append((e5, []))

    # ------------------------------------------------------------------
    # PÁGINA 6 — Good Roles (graph)
    # ------------------------------------------------------------------
    e6 = discord.Embed(title=f"{name.upper()}  —  Good Roles", color=0x1abc9c)

    good_won   = _safe_int(s.get("good_games_won"))
    good_lost  = _safe_int(s.get("good_games_lost"))
    total_good = good_won + good_lost
    good_pct   = f"{(good_won / total_good * 100):.1f}%" if total_good > 0 else "0%"

    e6.description = (
        f"You played more good games as: **{s.get('good_role_played_most', '-')}**\n"
        f"You won **{good_pct}** of the times you were good!\n\n"
        f"You won most as: **{s.get('good_role_won_most', '-')}**\n"
        f"You lost most when you were: **{s.get('good_role_lost_most', '-')}**"
    )
    e6.set_image(url="attachment://graph.png")
    e6.set_footer(text="Good Roles")
    pages.append((e6, [make_good_roles_graph(s)]))

    # ------------------------------------------------------------------
    # PÁGINA 7 — Evil Roles (graph)
    # ------------------------------------------------------------------
    e7 = discord.Embed(title=f"{name.upper()}  —  Evil Roles", color=0xe74c3c)

    evil_won   = _safe_int(s.get("evil_games_won"))
    evil_lost  = _safe_int(s.get("evil_games_lost"))
    total_evil = evil_won + evil_lost
    evil_pct   = f"{(evil_won / total_evil * 100):.1f}%" if total_evil > 0 else "0%"

    e7.description = (
        f"You played more evil games as: **{s.get('evil_role_played_most', '-')}**\n"
        f"You won **{evil_pct}** of the times you were evil!\n\n"
        f"You won most as: **{s.get('evil_role_won_most', '-')}**\n"
        f"You lost most when you were: **{s.get('evil_role_lost_most', '-')}**"
    )
    e7.set_image(url="attachment://graph.png")
    e7.set_footer(text="Evil Roles")
    pages.append((e7, [make_evil_roles_graph(s)]))

    # ------------------------------------------------------------------
    # PÁGINA 8 — Died as Good (Single + Duo, incluindo Gawain)
    # ------------------------------------------------------------------
    died_as_good_single = _safe_int(s.get("died_for_good"))
    died_as_gawain      = _safe_int(s.get("died_as_gawain"))
    duo_died_good       = _safe_int(s.get("duo_died_for_good"))
    total_good_deaths   = died_as_good_single + died_as_gawain + duo_died_good

    good_roles_set = {r.strip().lower() for r in GOOD_ROLES}
    good_roles_set.add("gawain")

    combined_good_death_roles = {}

    def add_roles(from_dict, multiplier=1):
        for role, count in from_dict.items():
            clean = role.strip().strip('"').strip("'").lower()
            if clean in good_roles_set:
                combined_good_death_roles[role] = combined_good_death_roles.get(role, 0) + count * multiplier

    add_roles(s.get("roles_that_died_with", {}))
    if died_as_gawain > 0:
        combined_good_death_roles["Gawain"] = combined_good_death_roles.get("Gawain", 0) + died_as_gawain
    add_roles(s.get("duo_roles_that_died_with", {}))

    if total_good_deaths > 0:
        e8 = discord.Embed(title=f"{name.upper()}  —  Died as Good", color=0x2ecc71)
        e8.description = f"You were killed **{total_good_deaths}** times while playing as Good.\n"
        e8.set_image(url="attachment://graph.png")
        e8.set_footer(text="Died as Good")
        graph_data = {"roles_played": combined_good_death_roles} if combined_good_death_roles else None
        if graph_data:
            pages.append((e8, [make_good_roles_graph(graph_data)]))
        else:
            pages.append((e8, []))

    # ------------------------------------------------------------------
    # PÁGINA 9 — Died as Evil (Single + Duo)
    # ------------------------------------------------------------------
    died_as_evil_single = _safe_int(s.get("died_for_evil"))
    duo_died_evil       = _safe_int(s.get("duo_died_for_evil"))
    total_evil_deaths   = died_as_evil_single + duo_died_evil

    evil_roles_set = {r.strip().lower() for r in EVIL_ROLES}

    combined_evil_death_roles = {}

    def add_evil_roles(from_dict, multiplier=1):
        for role, count in from_dict.items():
            clean = role.strip().strip('"').strip("'").lower()
            if clean in evil_roles_set:
                combined_evil_death_roles[role] = combined_evil_death_roles.get(role, 0) + count * multiplier

    add_evil_roles(s.get("roles_that_died_with", {}))
    add_evil_roles(s.get("duo_roles_that_died_with", {}))

    if total_evil_deaths > 0:
        e9 = discord.Embed(title=f"{name.upper()}  —  Died as Evil", color=0xe74c3c)
        e9.description = f"You were killed **{total_evil_deaths}** times while playing as Evil.\n"
        e9.set_image(url="attachment://graph.png")
        e9.set_footer(text="Died as Evil")
        graph_data_evil = {"roles_played": combined_evil_death_roles} if combined_evil_death_roles else None
        if graph_data_evil:
            pages.append((e9, [make_evil_roles_graph(graph_data_evil)]))
        else:
            pages.append((e9, []))

    # ------------------------------------------------------------------
    # Numeração dos footers
    # ------------------------------------------------------------------
    total_pages = len(pages)
    for i, (emb, _) in enumerate(pages):
        old_footer = emb.footer.text
        emb.set_footer(text=f"Page {i+1} / {total_pages}  •  {old_footer}  •  ⬅️ ➡️ to navigate")

    return pages


# ==============================================================================
# COG
# ==============================================================================

class Stats(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="stats", description="Get your player stats from Avalon Games! (Admins can check other players)")
    @app_commands.describe(player="(Admin only) Player name to look up")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def stats(self, interaction: discord.Interaction, player: str = None):

        # --- Resolve who we're looking up ---
        if player is not None:
            # Only admins can look up other players
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "You need administrator permissions to view another player's stats.",
                    ephemeral=True,
                )
                return
            player_nick = player.strip()
            if not player_nick:
                await interaction.response.send_message(
                    "Please provide a valid player name.", ephemeral=True
                )
                return
        else:
            # Self-lookup: prefer players_ids.json, fall back to display name
            target_id_str = str(interaction.user.id)
            player_nick = PLAYERS_IDS.get(target_id_str) or interaction.user.display_name

        # --- Fuzzy match ---
        player_in_list = _fuzzy_match_name_local(player_nick, nomes)

        if not player_in_list:
            msg = (
                f"Couldn't find **{player_nick}** in the player list."
                if player is not None
                else "Couldn't find your name in the player list. Are you registered in `players_ids.json`?"
            )
            await interaction.response.send_message(msg, ephemeral=True)
            return

        # --- Defer before any heavy work ---
        await interaction.response.defer()

        stats = get_player_stats(player_in_list)
        if not stats:
            await interaction.followup.send(
                f"Stats for **{player_in_list}** not loaded yet. Try again in a moment.",
                ephemeral=True,
            )
            return

        pages = build_pages(player_in_list, stats)
        total_pages  = len(pages)
        current_page = 0

        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "0️⃣"]

        def make_files(bufs: list) -> list[discord.File]:
            files = []
            for i, buf in enumerate(bufs):
                if buf is None:
                    continue
                buf.seek(0)
                fname = "graph.png" if i == 0 else f"graph{i+1}.png"
                files.append(discord.File(buf, filename=fname))
            return files

        # --- Send first page ---
        embed, bufs = pages[current_page]
        files = make_files(bufs)

        if files:
            msg = await interaction.followup.send(embed=embed, files=files)
        else:
            msg = await interaction.followup.send(embed=embed)

        # --- Add navigation reactions ---
        await msg.add_reaction("⬅️")
        await msg.add_reaction("➡️")

        for i in range(min(total_pages, 9)):
            await msg.add_reaction(number_emojis[i])
        if total_pages >= 10:
            await msg.add_reaction(number_emojis[9])  # '0️⃣' for page 10

        # --- Reaction check: only the invoking user, on this message ---
        def check(reaction, u):
            return (
                u.id == interaction.user.id
                and reaction.message.id == msg.id
                and str(reaction.emoji) in (["⬅️", "➡️"] + number_emojis)
            )

        # --- Navigation loop ---
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
                elif emoji in number_emojis:
                    digit = emoji[0]
                    target_page_num = 10 if digit == "0" else int(digit)
                    if 1 <= target_page_num <= total_pages:
                        current_page = target_page_num - 1

                embed, bufs = pages[current_page]
                files = make_files(bufs)

                if files:
                    await msg.edit(embed=embed, attachments=files)
                else:
                    await msg.edit(embed=embed, attachments=[])

                try:
                    await msg.remove_reaction(reaction, u)
                except discord.HTTPException:
                    pass  # Missing permissions to remove reaction — not fatal

            except Exception:
                break  # Timeout or other error — stop listening


async def setup(client):
    await client.add_cog(Stats(client))