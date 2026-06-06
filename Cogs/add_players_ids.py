import json
import os
import discord
from discord.ext import commands
from discord import app_commands
from utils_config import GUILD_ID

PLAYER_IDS_FILE = "players_ids.json"

def load_ids():
    if not os.path.exists(PLAYER_IDS_FILE):
        return {}
    with open(PLAYER_IDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_ids(data):
    with open(PLAYER_IDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class AddPlayersId(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="add_player_id", description="Add a Discord ID to player name mapping (admin only) ")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=int(GUILD_ID)))
    async def add_player_id(self, interaction: discord.Interaction, player_id: str, player_name: str):
        await interaction.response.defer(ephemeral=True)

        data = load_ids()
        data[player_id] = player_name
        save_ids(data)

        await interaction.followup.send("Player added to the list.", ephemeral=True)

async def setup(client):
    await client.add_cog(AddPlayersId(client))