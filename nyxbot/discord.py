import discord
from enum import Enum
from datetime import datetime
from discord.ext import commands

from .env import env

cogs = [
    "nyxbot.cogs.music",
    "nyxbot.cogs.dbadmin",
]

class EmbedColors(int, Enum):
    """Main Color Enum, used in Discord embeds"""

    # If you havent noticed already, yes this is literally
    # getbootstrap.com's button color scheme, lmfao
    
    PRIMARY = int(0x0069d9)
    SECONDARY = int(0x5a6268)
    SUCCESS = int(0x218838)
    DANGER = int(0xc82333)
    WARNING = int(0xe0a800)
    INFO = int(0x138496)
    LIGHT = int(0xe2e6ea)
    DARK = int(0x23272b)

class SMBot(commands.Bot):
    """Custom Discord Bot"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for cog in cogs:
            self.load_extension(cog)

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        await self.get_channel(env.admin_channel) \
            .send(embed=discord.Embed(
                description = "Started up at " + \
                    datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + \
                    "! :white_check_mark:",
                color = EmbedColors.INFO
            )) # sorry for this mess lol

    async def close(self):
        for vc in bot.voice_clients:
            await vc.disconnect()
        print(f'Logged out of {bot.user}!')


intents = discord.Intents.default()
status = discord.Game(
    name="with my big nuts"
)
bot = SMBot(
    command_prefix=commands.when_mentioned_or(">"),
    description='Relatively simple music bot example',
    intents=intents,
    activity=status
)
