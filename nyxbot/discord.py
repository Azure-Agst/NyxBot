import discord
import logging
from enum import Enum
from datetime import datetime
from discord.ext import commands

from .env import env

cogs = [
    "nyxbot.cogs.music",
    "nyxbot.cogs.dbadmin",
]

botLogger = logging.getLogger('NyxBot.bot')

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
        """Event: Bot is ready"""

        # log ready
        botLogger.info(f"Logged in as {self.user}")

        # send embed
        # sorry for this mess lol
        await self.get_channel(env.admin_channel) \
            .send(embed=discord.Embed(
                description = "Started up at " + \
                    datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + \
                    "! :white_check_mark:",
                color = EmbedColors.INFO
            ))

    async def close(self):
        """Event: Close the bot"""

        # disconnect from all voice clients
        for vc in bot.voice_clients:
            await vc.disconnect()
        
        # log close
        botLogger.info(f'Logged out of {bot.user}!')

    async def on_command_error(self, ctx, error):
        """Event: Error in command"""

        # if command isn't found
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(embed=discord.Embed(
                description = "Command not found! " + \
                    "Please check your syntax and try again.",
                color = EmbedColors.DANGER
            ))
            return
        
        # if command is missing required arguments
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=discord.Embed(
                description = "You're missing some arguments! " + \
                    "Please check your syntax and try again.",
                color = EmbedColors.DANGER
            ))

        # if other unhandled error occurs
        else:
            await ctx.send(embed=discord.Embed(
                description = "An unhandled error occurred! " + \
                    "Please contact the administrator.\n" + \
                    f"Error: {error}",
                color = EmbedColors.DANGER
            ))
            botLogger.error(f"Error in command {ctx.command}: {error}")

intents = discord.Intents.default()
status = discord.Game(
    name="with my big nuts"
)
bot = SMBot(
    command_prefix=commands.when_mentioned_or(">"),
    description='Relatively simple music bot example',
    help_command=commands.DefaultHelpCommand(),
    intents=intents,
    activity=status
)
