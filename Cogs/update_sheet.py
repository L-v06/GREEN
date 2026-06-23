# cog_update_sheet.py
import discord
from discord.ext import commands
from discord import app_commands
import re
import asyncio
import os
from dotenv import load_dotenv

from utils_config import GUILD_ID,STATS_CHANNEL_ID
from utils_sheets import nomes, load_all_players, load_all_gm_games
from utils_sheet_update import (
    add_one_day,
    determine_gm_type,
    determine_game_type,
    parse_death_info,
    build_game_log_rows,
    write_game_log_rows,
    build_death_log_rows,
    write_death_log_rows,
    remove_zeros,
)

load_dotenv()


PINK_BOT_ID = int(os.getenv("PINK_BOT_ID", 0))
TRIGGER_PHRASE = "Hey Green here is the log:"

# ==============================================================================
# Role lists
# ==============================================================================
GOOD_ROLES = [
    'merlin', 'apprentice', 'caelia', 'elaine', 'galahad', 'gawain',
    'guinevere', 'king arthur', 'palamedes', 'percival', 'sir kay',
    'tristan', 'iseult', 'loyal servant of arthur', 'penpingion',
    'good lancelot', 'nimue (g)','Untrustworthy Servant'
]
EVIL_ROLES = [
    'assassin', 'bertilak', 'dagonet', 'lucius', 'maduc', 'mark',
    'meleagant', 'mordred', 'morgana', 'oberon', 'puck', 'queen mab',
    'vortigern', 'the witch of caerlloyw', 'minion of morgana',
    'bad lancelot', 'nimue (e)'
]
NIMUE_MAP = {
    'evil nimue': 'Nimue (E)', 'bad nimue': 'Nimue (E)',
    'e nimue': 'Nimue (E)', 'b nimue': 'Nimue (E)',
    'nimue evil': 'Nimue (E)', 'nimue bad': 'Nimue (E)',
    'nimue e': 'Nimue (E)', 'nimue b': 'Nimue (E)',
    'good nimue': 'Nimue (G)', 'g nimue': 'Nimue (G)',
    'nimue good': 'Nimue (G)', 'nimue g': 'Nimue (G)',
}

def normalize_role(role: str) -> str:
    key = role.strip().lower()
    return NIMUE_MAP.get(key, role.strip())


# ==============================================================================
# Embed parser
# ==============================================================================
def parse_log_embed(embed: discord.Embed) -> dict | None:
    if not embed.description:
        return None

    desc = embed.description

    # Extrai ambas as datas do título: "Game dd/mm/yyyy - dd/mm/yyyy"
    date_match = re.search(r"(\d{2}/\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{2}/\d{4})", embed.title or "")
    if not date_match:
        return None
    raw_start = date_match.group(1)
    raw_end = date_match.group(2)
    d1, m1, y1 = raw_start.split("/")
    d2, m2, y2 = raw_end.split("/")
    start_date = f"{m1}/{d1}/{y1}"    # mm/dd/yyyy
    end_date = f"{m2}/{d2}/{y2}"

    # GM
    gm = None
    gm_match = re.search(r"GM:\s*(.+)", desc)
    if gm_match:
        gm = gm_match.group(1).strip()

    # Players
    players = []
    for line in desc.splitlines():
        stripped = line.strip().lstrip("*").lstrip("•").strip()
        if not stripped or "Round Table" in stripped or "Quest Chat" in stripped:
            continue
        player_match = re.match(r"^(.+?):\s*(.+)$", stripped)
        if player_match:
            name = player_match.group(1).strip()
            role = player_match.group(2).strip()
            role = normalize_role(role)
            if name.lower() == "gm":
                continue
            players.append({"name": name, "role": role})

    # Outcome
    outcome = None
    outcome_raw = ""
    for field in embed.fields:
        if "##" in (field.value or ""):
            outcome_raw = field.value.strip().lower()
            break
    if not outcome_raw:
        outcome_match = re.search(r"##\s*(.+)", desc)
        if outcome_match:
            outcome_raw = outcome_match.group(1).strip().lower()

    if "good wins" in outcome_raw or "good win" in outcome_raw:
        outcome = "good_wins"
    elif "evil wins" in outcome_raw or "evil win" in outcome_raw:
        outcome = "evil_wins"
    elif "gawain" in outcome_raw:
        outcome = "gawain_wins"
    elif "nimue" in outcome_raw or "draw" in outcome_raw:
        outcome = "nimue_killed"

    # Vote
    vote = "nc"
    footer_text = (embed.footer.text or "").lower()
    if "not collected" in footer_text or "was not collected" in footer_text:
        vote = "nc"
    elif "voted correctly" in footer_text:
        if "good voted correctly" in footer_text:
            vote = "vc_good"
        elif "evil voted correctly" in footer_text or "assassin vote" in footer_text:
            vote = "vc_evil"
        else:
            vote = "vc"
    elif "voted incorrectly" in footer_text or "incorrect" in footer_text:
        if "good voted incorrectly" in footer_text:
            vote = "vi_good"
        elif "evil voted incorrectly" in footer_text or "assassin vote" in footer_text:
            vote = "vi_evil"
        else:
            vote = "vi"

    if not players or not outcome:
        return None

    return {
        "start_date": start_date,
        "end_date": end_date,
        "gm": gm,
        "players": players,
        "outcome": outcome,
        "vote": vote,
    }


# ==============================================================================
# View para mapear nomes desconhecidos
# ==============================================================================
class NameMappingView(discord.ui.View):
    def __init__(self, unknown_names: list[str], known_names: list[str]):
        super().__init__(timeout=120)
        self.unknown_names = list(set(unknown_names))
        self.known_names = known_names
        self.mapping = {}
        self.finished = asyncio.Event()

        for i, uname in enumerate(self.unknown_names):
            select = discord.ui.Select(
                placeholder=f"Quem é '{uname}'?",
                options=[discord.SelectOption(label=name) for name in known_names[:24]],
                custom_id=f"map_{i}"
            )
            select.callback = self.make_callback(uname, select)
            self.add_item(select)

    def make_callback(self, unknown: str, select: discord.ui.Select):
        async def callback(interaction: discord.Interaction):
            self.mapping[unknown] = select.values[0]
            await interaction.response.defer()
            if len(self.mapping) == len(self.unknown_names):
                self.finished.set()
                self.stop()
        return callback

    async def wait_for_mapping(self):
        await self.finished.wait()
        return self.mapping


# ==============================================================================
# ConfirmView (escreve ambas as planilhas + recarrega cache em thread separada)
# ==============================================================================
class ConfirmView(discord.ui.View):
    def __init__(self, game_log_rows: list[list], death_log_rows: list[list],
                 original_embed: discord.Embed, warnings: list[str]):
        super().__init__(timeout=120)
        self.game_log_rows = game_log_rows
        self.death_log_rows = death_log_rows
        self.original_embed = original_embed
        self.warnings = warnings
        self.responded = False

    @discord.ui.button(label="✅ Yes, update sheet", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.responded:
            return
        self.responded = True
        self.clear_items()
        await interaction.response.edit_message(content="⏳ Writing to sheets...", embed=None, view=self)

        try:
            write_game_log_rows(self.game_log_rows)
            write_death_log_rows(self.death_log_rows)

            await interaction.followup.send(
                "✅ Sheets updated! Reloading all caches (this may take a few minutes)...",
                ephemeral=True
            )

            # Recarrega stats + deaths
            await asyncio.to_thread(load_all_players, force=True)
            # Recarrega GM games (depende do stats cache já atualizado)
            await asyncio.to_thread(load_all_gm_games, force=True)

            await interaction.edit_original_response(
                content=f"✅ Sheets updated! Game Log: {len(self.game_log_rows)} rows, "
                        f"Death Log: {len(self.death_log_rows)} rows.\n"
                        f"📊 All caches reloaded (stats, deaths, GM games).",
                embed=None,
                view=None
            )
        except Exception as e:
            await interaction.edit_original_response(
                content=f"❌ Error: `{e}`", embed=None, view=None
            )

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.responded:
            return
        self.responded = True
        self.clear_items()
        await interaction.response.edit_message(
            content="🚫 Update cancelled. Nothing was written.",
            embed=None,
            view=None
        )


# ==============================================================================
# Processamento central
# ==============================================================================
async def process_log_message(
    client: commands.Bot,
    log_msg: discord.Message,
    reply_target,
    is_interaction: bool,
):
    stats_channel = client.get_channel(STATS_CHANNEL_ID)
    if not stats_channel:
        err = "❌ Couldn't find the `stats` channel. Check `STATS_CHANNEL_ID` in `.env`."
        if is_interaction:
            await reply_target.followup.send(err, ephemeral=True)
        else:
            await reply_target.channel.send(err)
        return

    if not log_msg.embeds:
        err = "❌ That message has no embeds."
        if is_interaction:
            await reply_target.followup.send(err, ephemeral=True)
        else:
            await reply_target.channel.send(err)
        return

    original_embed = log_msg.embeds[0]
    data = parse_log_embed(original_embed)
    if not data:
        err = "❌ Couldn't parse the log embed. Check its format."
        if is_interaction:
            await reply_target.followup.send(err, ephemeral=True)
        else:
            await reply_target.channel.send(err)
        return

    # --- Separar nomes dos GMs (pode ser múltiplos) ---
    gm_names = [n.strip() for n in data["gm"].split(",")] if data["gm"] else []

    # --- Coletar todos os nomes individuais (GMs e jogadores) ---
    all_individual_names = gm_names + [p["name"] for p in data["players"]]
    unknown = [name for name in all_individual_names if name and name not in nomes]

    if unknown:
        view = NameMappingView(unknown, nomes)
        if is_interaction:
            await reply_target.followup.send(
                "Alguns nomes não foram reconhecidos. Selecione o nome correto:",
                view=view,
                ephemeral=True
            )
        else:
            await reply_target.channel.send(
                "Alguns nomes não foram reconhecidos. Selecione o nome correto:",
                view=view
            )
        mapping = await view.wait_for_mapping()

        # Aplica mapeamento nos GMs
        gm_names = [mapping.get(name, name) for name in gm_names]
        # Aplica nos jogadores
        for p in data["players"]:
            if p["name"] in mapping:
                p["name"] = mapping[p["name"]]

    # --- Tipos de jogo ---
    gm_type = determine_gm_type(gm_names)
    game_type = determine_game_type(data["players"])

    outcome_map = {
        "good_wins": "Good",
        "evil_wins": "Evil",
        "gawain_wins": "Gawain",
        "nimue_killed": "Nimue"
    }
    who_wins = outcome_map.get(data["outcome"], "Unknown")

    # --- Construir linhas ---
    game_log_rows = build_game_log_rows({
        "date": data["start_date"],
        "players": data["players"],
        "outcome": data["outcome"],
        "vote": data["vote"]
    })

    death_info = parse_death_info(original_embed)
    death_log_rows = build_death_log_rows(
        date=data["start_date"],
        end_date=data["end_date"],
        gm=", ".join(gm_names),
        gm_type=gm_type,
        game_type=game_type,
        who_wins=who_wins,
        deaths=death_info
    )

    # --- Warnings ---
    warnings = []
    if not gm_names:
        warnings.append("⚠️ GM name not found.")
    if data.get("vote") == "nc":
        warnings.append("⚠️ Vote was not collected.")
    if not death_info:
        warnings.append("⚠️ No death information found in embed.")

    warning_text = "\n".join(warnings) if warnings else "✅ No issues found."

    preview = (
        f"📋 **Game ready to write**\n"
        f"**Start:** {remove_zeros(add_one_day(data['start_date']))} | **End:** {data['end_date']}\n"
        f"**GM:** {', '.join(gm_names)} ({gm_type}) | **Type:** {game_type}\n"
        f"**Outcome:** {who_wins}\n"
        f"{warning_text}"
    )

    view = ConfirmView(game_log_rows, death_log_rows, original_embed, warnings)

    await stats_channel.send(
        content=preview,
        embed=original_embed,
        view=view,
    )


# ==============================================================================
# Cog
# ==============================================================================
class UpdateSheet(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id != PINK_BOT_ID:
            return
        if message.channel.id != STATS_CHANNEL_ID:
            return
        if TRIGGER_PHRASE not in message.content:
            return

        id_match = re.search(r"\b(\d{17,20})\b", message.content)
        if not id_match:
            await message.channel.send("⚠️ Green couldn't find a message ID in Pink's trigger.")
            return

        log_msg_id = int(id_match.group(1))
        try:
            log_msg = await message.channel.fetch_message(log_msg_id)
        except discord.NotFound:
            await message.channel.send(f"⚠️ Couldn't find message `{log_msg_id}` in this channel.")
            return

        await process_log_message(self.client, log_msg, message, is_interaction=False)

    @app_commands.command(name="update", description="Manually update the sheet from a log message ID.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def update(self, interaction: discord.Interaction, message_id: str, channel_id: str = None):
        await interaction.response.defer(ephemeral=True)

        if channel_id:
            channel = self.client.get_channel(int(channel_id))
        else:
            channel = self.client.get_channel(STATS_CHANNEL_ID)

        if not channel:
            await interaction.followup.send("❌ Couldn't find that channel.", ephemeral=True)
            return

        try:
            log_msg = await channel.fetch_message(int(message_id))
        except discord.NotFound:
            await interaction.followup.send(f"❌ Message `{message_id}` not found.", ephemeral=True)
            return

        await interaction.followup.send("✅ Log found — check the `#stats` channel for the preview.", ephemeral=True)
        await process_log_message(self.client, log_msg, interaction, is_interaction=True)

    @update.error
    async def update_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("🔒 You don't have permission to use this command.", ephemeral=True)
        else:
            try:
                await interaction.followup.send(f"⚠️ Something went wrong: `{error}`", ephemeral=True)
            except:
                await interaction.response.send_message(f"⚠️ Something went wrong: `{error}`", ephemeral=True)


async def setup(client):
    await client.add_cog(UpdateSheet(client))
