import emoji
import discord
from discord.ext import commands
from typing import Optional

from ..db import search_db
from ..discord import EmbedColors

NUMBER_LOOKUP_TABLE = [
    ":keycap_1:", ":keycap_2:", ":keycap_3:",
    ":keycap_4:", ":keycap_5:", ":keycap_6:",
    ":keycap_7:", ":keycap_8:", ":keycap_9:",
]

class Music(commands.Cog):
    """Cog which holds the music commands"""

    def __init__(self, bot):
        self.bot = bot
        self.volume = 0.2
        self.latest_prompt_id = None
        self.latest_prompt_ctx = None
        self.latest_prompt_data = []

    #
    # ===== [ Private Functions ] =====
    #

    async def _join_channel(self, ctx, channel: discord.VoiceChannel):
        """Private function which joins a voice channel"""

        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()

    async def _leave_channel(self, ctx):
        """Private function which leaves a voice channel"""

        if ctx.voice_client is not None:
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
    
    async def _play_file(self, ctx, db_entry):
        """Plays a file, given a path"""

        # make sure we're in a voice channel
        if ctx.voice_client is None:
            await self._join_channel(ctx, ctx.author.voice.channel)

        # get the first song and play it
        audio_source = discord.FFmpegPCMAudio(db_entry['path'])

        # create a volume transformer
        volume_ctrl = discord.PCMVolumeTransformer(
            audio_source,
            volume = self.volume
        )

        # play file
        ctx.voice_client.play(
            volume_ctrl,
            after=lambda e: print(f'Player error: {e}') if e else None
        )

        # print an embed, saying that we're playing
        await ctx.send(embed=discord.Embed(
            title = "Now Playing:",
            description = f"{db_entry['artist']} - {db_entry['title']}",
            color = EmbedColors.SUCCESS
        ))

    #
    # ===== [ Commands ] =====
    #

    @commands.command(aliases=["j"])
    async def join(self, ctx, *, channel: Optional[discord.VoiceChannel]):
        """Command: Joins a voice channel"""

        # determine destination
        # if user is in a voice channel, use that
        if channel is None:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
            else:
                await ctx.send(embed=discord.Embed(
                    description = "You need to specify or join a channel!",
                    color = EmbedColors.DANGER
                ))
                return
        
        # are we already in the channel?
        if ctx.voice_client and ctx.voice_client.channel == channel:
            await ctx.send(embed=discord.Embed(
                    description = "I'm already in this channel!",
                    color = EmbedColors.DANGER
                ))
            return
        
        # make sure we can join
        if not channel.permissions_for(ctx.me).connect:
            await ctx.send(embed=discord.Embed(
                    description = "I don't have permission to connect to that channel!",
                    color = EmbedColors.DANGER
                ))
            return

        # cool, join it
        await self._join_channel(ctx, channel)

    @commands.command(aliases=["l", "dc"])
    async def leave(self, ctx):
        """Leaves a voice channel"""

        # make sure we're in a voice channel
        if ctx.voice_client is not None:

            # disconnect
            await self._leave_channel(ctx)

            # and add a reaction!
            await ctx.message.add_reaction(
                emoji.emojize(':OK_hand:')
            )

        # if not, send an embed
        else:
            await ctx.send(embed=discord.Embed(
                description = "I'm not in a channel right now!",
                color = EmbedColors.DANGER
            ))

    @commands.command(aliases=["p"])
    async def play(self, ctx, *, query: Optional[str]):
        """Play command"""

        # Since p is both pause and play, add that logic here
        if query is None:

            # if we're not in a channel, error out
            if ctx.voice_client is None:
                await ctx.send(embed=discord.Embed(
                    description = "I'm not in a channel right now, and no song was specified!",
                    color = EmbedColors.DANGER
                ))

            # if paused, play
            elif ctx.voice_client.is_paused():
                ctx.voice_client.resume()
                await ctx.message.add_reaction(
                    emoji.emojize(':play_button:')
                )
            
            # if playing and invoked with "p", pause
            elif ctx.voice_client.is_playing() and ctx.invoked_with == "p":
                ctx.voice_client.pause()
                await ctx.message.add_reaction(
                    emoji.emojize(':pause_button:')
                )
            
            # if neither, send an embed
            else:
                await ctx.send(embed=discord.Embed(
                    description = "I'm unable to understand what you " + \
                        "want me to do! Please pass in an argument!",
                    color = EmbedColors.DANGER
                ))

        # else, if a query was passed in, handle it
        else:

            # search for the song
            results = search_db(query)

            # if we found a song, play it
            if results:

                # if more than one result, send a prompt embed
                if len(results) > 1:
                    
                    # format embed string
                    e_str = ""
                    for i, v in enumerate(results):
                        e_str += f"**{i + 1}.)** {v['artist']} - {v['title']}\n"

                    # cache these results
                    self.latest_prompt_ctx = ctx
                    self.latest_prompt_data = results

                    # send embed
                    self.latest_prompt_message = await ctx.send(embed=discord.Embed(
                        title = "Multiple results found! Please select one:",
                        description = e_str,
                        color = EmbedColors.LIGHT
                    ))

                    # add reactions
                    for i in range(len(results)):
                        await self.latest_prompt_message.add_reaction(
                            emoji.emojize(NUMBER_LOOKUP_TABLE[i])
                        )

                # if there's only one song in the results, play it
                else:

                    # if in a song, stop it
                    if ctx.voice_client and ctx.voice_client.is_playing():
                        ctx.voice_client.stop()
                    
                    # play the song
                    await self._play_file(ctx, results[0])

            # if we couldnt find a song, send an embed
            else:
                await ctx.send(embed=discord.Embed(
                    description = "I couldn't find any song that matches your query!",
                    color = EmbedColors.DANGER
                ))

    @commands.command(aliases=["s"])
    async def stop(self, ctx):
        """Stop playing command"""

        # if we're in a channel...
        if ctx.voice_client:

            # stop the music...
            ctx.voice_client.stop()
            
            # and add a reaction!
            await ctx.message.add_reaction(
                emoji.emojize(':stop_button:')
            )
        
        # if we're not in a channel, send an embed
        else:
            await ctx.send(embed=discord.Embed(
                description = "I'm not playing anything right now!",
                color = EmbedColors.DANGER
            ))

    @commands.command()
    async def pause(self, ctx):
        """Pause command"""

        # if we're in a channel...
        if ctx.voice_client:

            # pause the music...
            ctx.voice_client.pause()

            # and add a reaction!
            await ctx.message.add_reaction(
                emoji.emojize(':pause_button:')
            )
        
        # if we're not in a channel, send an embed
        else:
            await ctx.send(embed=discord.Embed(
                description = "I'm not playing anything right now!",
                color = EmbedColors.DANGER
            ))

    @commands.command()
    async def search(self, ctx, *, query: str):
        """Search command"""

        # search for the songs
        results = search_db(query)

        # if we found songs, send an embed
        if results:

            # format embed string
            e_str = ""
            for i, v in enumerate(results):
                e_str += f"**{i + 1}.)** {v['artist']} - {v['title']}\n"

            # send embed
            await ctx.send(embed=discord.Embed(
                title = f"{len(results)} results found:",
                description = e_str,
                color = EmbedColors.DARK
            ))

        # if we didn't find any, send an embed
        else:

            # send embed
            await ctx.send(embed=discord.Embed(
                description = "I couldn't find any songs that match your query!",
                color = EmbedColors.DANGER
            ))

    @commands.command(aliases=["v", "vol"])
    async def volume(self, ctx, volume: Optional[int]):
        """Volume command"""

        # if no volume was passed in, send an embed
        if volume is None:
            cur_volume = int(ctx.voice_client.source.volume * 100)
            await ctx.send(embed=discord.Embed(
                description = f"Current Volume: {cur_volume}%",
                color = EmbedColors.DARK
            ))

        # if a volume was passed in, set it
        else:

            # Make sure we're in a channel
            if not ctx.voice_client:
                await ctx.send("I am not in a voice channel!")

            # Make sure we're within the range
            if volume > 100 or volume < 0:
                await ctx.send("Volume must be between 0 and 100!")
                return
            
            # make changes
            self.volume = volume / 100
            ctx.voice_client.source.volume = volume / 100

            # add a reaction!
            await ctx.message.add_reaction(
                emoji.emojize(':OK_hand:')
            )

    #
    # ===== [ Event Handlers ] =====
    #

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Listener to handle prompts"""

        # ignore bots :)
        if user.bot:
            return

        # if the message is the latest prompt message...
        if reaction.message.id == self.latest_prompt_message.id:

            # if the reaction is a number...
            emote_str = emoji.demojize(str(reaction.emoji))
            if emote_str in NUMBER_LOOKUP_TABLE:

                # get the index of the reaction
                index = NUMBER_LOOKUP_TABLE.index(emote_str)

                # if the index is within the range of the results...
                if index < len(self.latest_prompt_data):

                    # if already playing, stop it
                    if self.latest_prompt_ctx.voice_client and \
                        self.latest_prompt_ctx.voice_client.is_playing():
                        self.latest_prompt_ctx.voice_client.stop()

                    # play the song
                    await self._play_file(
                        self.latest_prompt_ctx,
                        self.latest_prompt_data[index]
                    )

                    # delete the message
                    await self.latest_prompt_message.delete()

                    # clear the cache
                    self.latest_prompt_id = None
                    self.latest_prompt_ctx = None
                    self.latest_prompt_data = None

                # if the index is not within the range of the results...
                else:

                    # remove the reaction
                    await reaction.remove(user)

            # if the reaction is not a number...
            else:

                # remove the reaction
                await reaction.remove(user)
    

def setup(bot):
    bot.add_cog(Music(bot))