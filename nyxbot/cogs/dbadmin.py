import logging
import discord
import asyncio
from discord.ext import commands, tasks

from ..env import env
from ..db import file_poll_thread
from ..discord import EmbedColors

dbadminLogger = logging.getLogger('NyxBot.cogs.DBAdmin')

class DBAdmin(commands.Cog):
    """Cog which helps keep database up to date"""

    def __init__(self, bot):
        self.bot = bot

    #
    # ===== [ Task Related Stuff ] =====
    #

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.update_db_task.start()

    @tasks.loop(minutes=30)
    async def update_db_task(self):
        """Private function which updates the database"""

        dbadminLogger.info("Running scheduled polling!")

        # get channel
        adminChannel = self.bot.get_channel(env.admin_channel)

        # print a warning on first run
        if env.first_run:
            dbadminLogger.warn("First run detected! This may take a while...")
            await adminChannel.send(embed=discord.Embed(
                    description=f"Just started indexing your library! " + \
                    "Since this is the first time you've run this bot, " + \
                    "it may take a while to index your library. " + \
                    "Please be patient!",
                    color=EmbedColors.WARNING
                ))
            env.first_run = False

        # start new polling thread
        files_added = await file_poll_thread()

        # send report to channel
        if files_added > 0:
            message = f"{files_added} new files were just indexed!"
            dbadminLogger.info(message)
            await adminChannel.send(embed=discord.Embed(
                description=message,
                color=EmbedColors.DARK
            ))

        # if no new files, say so
        else:
            message = "No new files were found."
            dbadminLogger.info(message)

    @commands.command(name="reindex", hidden=True)
    @commands.has_guild_permissions(administrator=True)
    async def _update(self, ctx):
        """Forcefully triggers a database update"""

        # print warnings
        dbadminLogger.warn("Update command called manually...")
        await ctx.send(embed=discord.Embed(
            description=f"Beginning library scan...",
            color=EmbedColors.DARK
        ))

        # start new polling thread
        files_added = await file_poll_thread()

        # send report to channel if files were added
        if files_added > 0:
            message = f"{files_added} new files were just indexed!"
            dbadminLogger.info(message)
            await ctx.send(embed=discord.Embed(
                description=message,
                color=EmbedColors.DARK
            ))
        
        # if no new files, say so
        else:
            message = "No new files were found."
            dbadminLogger.info(message)
            await ctx.send(embed=discord.Embed(
                description=message,
                color=EmbedColors.DARK
            ))

def setup(bot):
    bot.add_cog(DBAdmin(bot))