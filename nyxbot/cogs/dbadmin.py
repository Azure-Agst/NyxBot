import discord
from discord.ext import commands, tasks

from ..env import env
from ..db import poll_new_files
from ..discord import EmbedColors

class DBAdmin(commands.Cog):
    """Cog which helps keep database up to date"""

    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.update_db_task.start()

    @tasks.loop(minutes=30)
    async def update_db_task(self):
        """Private function which updates the database"""

        print("Running scheduled polling!")

        # print a warning on first run
        if env.first_run:
            await self.bot \
                .get_channel(env.admin_channel) \
                .send(embed=discord.Embed(
                    description=f"Just started indexing your library! " + \
                    "Since this is the first time you've run this bot, " + \
                    "it may take a while to index your library. " + \
                    "Please be patient!",
                    color=EmbedColors.WARNING
                ))
            env.first_run = False

        # poll new files
        new_cnt = await poll_new_files()
        print("Done!")

        if new_cnt > 0:
            await self.bot \
                .get_channel(env.admin_channel) \
                .send(embed=discord.Embed(
                    description=f"{new_cnt} new files were just indexed!",
                    color=EmbedColors.INFO
                ))

    @commands.command()
    async def update(self, ctx):
        """Command: Updates the database"""

        print("Update command called manually...")
        await ctx.send("Updating database...")
        new_cnt = await poll_new_files()
        await ctx.send("Done! Indexed {} new files!".format(new_cnt))

def setup(bot):
    bot.add_cog(DBAdmin(bot))