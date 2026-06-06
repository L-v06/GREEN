import ssl_fix
import discord
from discord import app_commands
from discord.ext import commands

import sys
import os

from dotenv import load_dotenv
load_dotenv()

discord_token = os.getenv('TOKEN')
guild_id = int(os.getenv('SERVER_ID'))

intents = discord.Intents.all()
client = commands.Bot(command_prefix=':', intents=intents)

caminho_pasta = "C:/Users/luiza/Downloads/Green/Cogs"
sys.path.append(caminho_pasta)


@client.command()
async def sync(ctx: commands.Context):
    if ctx.author.id in (1055256389422940200, 756666042733953175):
        server = discord.Object(id=guild_id)
        sincs = await client.tree.sync(guild=server)
        await ctx.send(f'{len(sincs)} commands synced')
    else:
        await ctx.reply("You don't have authorization to sync this bot, please contact Blue or Nix")


async def load():
    for filename in os.listdir(caminho_pasta):
        if filename.endswith('.py'):
            cog_name = filename[:-3]
            await client.load_extension(f'Cogs.{cog_name}')
            print(f'Loaded {cog_name}')


@client.event
async def on_ready():
    await client.change_presence(
        status=discord.Status.online,
        activity=discord.CustomActivity(name="shhhhhhhh I'm counting")
    )
    await load()

    # carrega o cache do Sheets — roda uma vez no startup
    print('[bot] Carregando cache do Google Sheets...')
    from utils_sheets import load_all_players
    await discord.utils.asyncio.get_event_loop().run_in_executor(None, load_all_players)
    print('[bot] Cache pronto!')

    print('----------------------')
    print('here we go')


client.run(discord_token)