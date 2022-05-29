import emoji
import random
import asyncio
import discord
import itertools
from typing import Optional
from discord.ext import commands
from async_timeout import timeout

from ..db import search_db
from ..discord import EmbedColors

NUMBER_LOOKUP_TABLE = [
    ":keycap_1:", ":keycap_2:", ":keycap_3:",
    ":keycap_4:", ":keycap_5:", ":keycap_6:",
    ":keycap_7:", ":keycap_8:", ":keycap_9:",
]

class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]

class Music(commands.Cog):
    """Cog which holds the music commands"""

    def __init__(self, bot):

        # constants
        self.bot = bot
        self.timeout = 180

        # prompt variables
        self.latest_prompt_id = None
        self.latest_prompt_ctx = None
        self.latest_prompt_data = None

        # audio player stuff
        self.audio_player_thread = None
        self.voice_client = None
        self.invoked_ctx = None
        self.player_loop = False
        self.player_volume = 0.2

        # song queue
        self.current_song = None
        self.start_next_song = asyncio.Event()
        self.song_queue = SongQueue(maxsize=10)

    
    def __del__(self):
        self.audio_player_thread.cancel()
    
    #
    # ===== [ Voice State Functions ] =====
    #

    async def _audio_player_task(self):
        """Main async task that handles playing songs"""

        # print that the audio player thread has started
        print("_audio_player_task started!")

        # put everything in a try block
        try:

            # loop forever
            while True:

                # clear the mutex
                self.start_next_song.clear()

                # if we're not set to loop, try getting next song
                if not self.player_loop:

                    # this will attempt to get a song from asyncio's queue
                    # it will time out after 3 minutes, disconnecting
                    # if no song is put in the quete
                    try:
                        async with timeout(self.timeout):
                            self.current = await self.song_queue.get()
                            print("Got next song!")
                    except asyncio.TimeoutError:
                        self.bot.loop.create_task(self._stop_audio_player())
                        return

                # prep the song
                audio_source = discord.FFmpegPCMAudio(self.current['path'])
                src_w_vol = discord.PCMVolumeTransformer(
                    audio_source, volume = self.player_volume
                )

                # race condition check
                if self.voice_client.is_playing():
                    print(
                        "Warning: Found weird race condition!\n" +\
                        "Started next song while currently playing, idk why"
                    )

                # play the song
                self.voice_client.play(
                    src_w_vol,
                    after=self._play_next_song
                )

                # set the volume
                self.voice_client.source.volume = self.player_volume

                # wait for song to finish playing
                # the callback should set this mutex,
                # allowing this loop to continue
                await self.start_next_song.wait()
        
        # catch all exceptions
        except BaseException as e:

            # if it's a CancelledError, ignore it
            if type(e) is asyncio.CancelledError:
                return
            
            # elsem its an actual error
            print(
                "_audio_player_task error: " + \
                type(e).__name__ + "\n" +\
                "text: " + str(e)
            )
            raise

    def _play_next_song(self, error: Optional[Exception]):
        """Called when a song is done playing"""

        # if there was an error
        if error:
            raise error

        # set the next event
        self.start_next_song.set()

    async def _stop_audio_player(self):
        """Stops the audio player"""

        # clear the queue
        self.song_queue.clear()

        # stop the player thread
        self.audio_player_thread.cancel()

        # disconnect, if connected
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None

    #
    # ===== [ Private Functions ] =====
    #

    async def _join_channel(self, ctx, channel: discord.VoiceChannel):
        """Private function which joins a voice channel"""

        # join or move a channel
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
        else:
            self.voice_client = await channel.connect()

        # now that we're connected, we can start the audio player thread
        self.audio_player_thread = self.bot.loop.create_task(
            self._audio_player_task()
        )

    async def _leave_channel(self):
        """Private function which leaves a voice channel"""

        if self.voice_client is not None:
            await self._stop_audio_player()

    async def _queue_file(self, ctx, db_entry):
        """Queues a file, given a path"""

        # get queue size
        q_size = self.song_queue.qsize()

        # if nothing's in the queue, put a playing embed
        if q_size == 0 and not self.voice_client.is_playing():

            # print an embed, saying that we're playing
            await ctx.send(embed=discord.Embed(
                title = "Now Playing:",
                description = f"{db_entry['artist']} - {db_entry['title']}",
                color = EmbedColors.SUCCESS
            ))

        # else, if stuff is in the queue, send a queued embed
        else:

            # send an embed, saying that we added the song
            await ctx.send(embed=discord.Embed(
                title = "Added to Queue:",
                description = f"{db_entry['artist']} - {db_entry['title']}",
                color = EmbedColors.DARK
            ))

        # add to queue
        await self.song_queue.put(db_entry)

    async def _send_prompt_embed(self, ctx, results):
        """Sends a prompt embed"""

        # format embed string
        e_str = ""
        for i, v in enumerate(results):
            e_str += f"**{i + 1}.)** {v['artist']} - {v['title']}\n"

        # cache results for further processing upon response
        self.latest_prompt_ctx = ctx
        self.latest_prompt_data = results

        # send embed
        self.latest_prompt_message = await ctx.send(embed=discord.Embed(
            title = "Multiple results found! Please select one:",
            description = e_str,
            color = EmbedColors.LIGHT
        ))

        # try to add reactions
        # if we get a NotFound error, it means we have
        # a quick responder. just ignore that for now.
        try:
            for i in range(len(results)):
                await self.latest_prompt_message.add_reaction(
                    emoji.emojize(NUMBER_LOOKUP_TABLE[i])
                )
        except discord.errors.NotFound:
            pass

    #
    # ===== [ Commands ] =====
    #

    @commands.command(name="join", aliases=["j"])
    async def _join(self, ctx, *, channel: Optional[discord.VoiceChannel]):
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

        # we're cool, join it
        await self._join_channel(ctx, channel)

    @commands.command(name="leave", aliases=["l", "dc"])
    async def _leave(self, ctx):
        """Leaves a voice channel"""

        # make sure we're in a voice channel
        if ctx.voice_client is not None:

            # disconnect
            await self._leave_channel()

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

    @commands.command(name="play", aliases=["p"])
    async def _play(self, ctx, *, query: Optional[str]):
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

            # join the channel if we're not in one
            if ctx.voice_client is None:
                await self._join_channel(ctx, ctx.author.voice.channel)

            # search for the song
            results = search_db(query)

            # if more than one result, send a prompt embed
            if len(results) > 1:
                
                # send embed
                await self._send_prompt_embed(ctx, results)

            # if there's only one song in the results...
            elif len(results) == 1:

                # add to queue
                await self._queue_file(ctx, results[0])

            # if we couldnt find a song, send an embed
            else:
                await ctx.send(embed=discord.Embed(
                    description = "I couldn't find any song that matches your query!",
                    color = EmbedColors.DANGER
                ))

    @commands.command(name="stop", aliases=["st"])
    async def _stop(self, ctx):
        """Stop playing command"""

        # if we're in a channel...
        if ctx.voice_client:

            # clear the queue
            for _ in range(self.song_queue.qsize()):
                self.song_queue.get_nowait()
                self.song_queue.task_done()

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

    @commands.command(name="pause")
    async def _pause(self, ctx):
        """Pause command"""

        # if we're in a channel...
        if ctx.voice_state.is_playing():

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

    @commands.command(name="search")
    async def _search(self, ctx, *, query: str):
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

    @commands.command(name="volume", aliases=["v", "vol"])
    async def _volume(self, ctx, volume: Optional[int]):
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
            self.player_volume = volume / 100
            ctx.voice_client.source.volume = self.player_volume

            # add a reaction!
            await ctx.message.add_reaction(
                emoji.emojize(':OK_hand:')
            )

    @commands.command(name="queue", aliases=["q"])
    async def _queue(self, ctx):
        """Queue command"""

        # temp vars
        embed_contents = ""
        now_playing_str = ""
        queue_str = ""

        # if not in channel, error out
        if not ctx.voice_client:
            await ctx.send(embed=discord.Embed(
                description = "I'm not in a voice channel!",
                color = EmbedColors.DANGER
            ))
            return

        # if something is playing, get that
        if ctx.voice_client.is_playing():
            now_playing_str = f"**Now Playing:**\n {self.current['artist']} - {self.current['title']}"

        # if there's stuff in the queue, get that too
        if self.song_queue.qsize() == 0:
            queue_str = "Queue is empty!"
        else:
            for i, song in enumerate(self.song_queue, start=0):
                queue_str += f"**{i + 1}.)** {song['artist']} - {song['title']}\n"

        # format embed contents
        if now_playing_str != "":
            embed_contents += now_playing_str + "\n\n"
        embed_contents += "**Queue:**\n"
        embed_contents += queue_str

        # send embed
        await ctx.send(embed=discord.Embed(
            description = embed_contents,
            color = EmbedColors.DARK
        ))

    @commands.command(name="clear", aliases=["c"])
    async def _clear(self, ctx):
        """Clears the queue"""

        # clear the queue
        self.song_queue.clear()

        # send an embed
        await ctx.send(embed=discord.Embed(
            description = "Queue cleared!",
            color = EmbedColors.DARK
        ))

    @commands.command(name="skip", aliases=["s"])
    async def _skip(self, ctx):
        """Skip command"""

        # if we're in a channel...
        if ctx.voice_client:

            # skip the current song
            ctx.voice_client.stop()

            # add a reaction!
            await ctx.message.add_reaction(
                emoji.emojize(':fast-forward_button:')
            )

        # if we're not in a channel, send an embed
        else:
            await ctx.send(embed=discord.Embed(
                description = "I'm not playing anything right now!",
                color = EmbedColors.DANGER
            ))

    @commands.command(name="nowplaying", aliases=["np"])
    async def _nowplaying(self, ctx):
        """Now Playing command"""

        # if we're not in a channel, send an embed
        if not ctx.voice_client:
            await ctx.send(embed=discord.Embed(
                description = "I'm not playing anything right now!",
                color = EmbedColors.DANGER
            ))
            return

        # if we're in a channel, handle
        else:

            # if something is playing, send an embed
            if ctx.voice_client.is_playing():
                await ctx.send(embed=discord.Embed(
                    description = f"**Now Playing:**\n {self.current['artist']} - {self.current['title']}",
                    color = EmbedColors.DARK
                ))

            # if nothing is playing, send an embed
            else:
                await ctx.send(embed=discord.Embed(
                    description = "I'm not playing anything right now!",
                    color = EmbedColors.DANGER
                ))

    @commands.command(name="loop")
    async def _loop(self, ctx):
        """Loop command"""

        # if we're not in a channel, send an embed
        if not ctx.voice_client:
            await ctx.send(embed=discord.Embed(
                description = "I'm not playing anything right now!",
                color = EmbedColors.DANGER
            ))
            return

        # if we're in a channel, handle
        else:

            # if looping is enabled, disable it
            if self.player_loop:
                self.player_loop = False
                await ctx.send(embed=discord.Embed(
                    description = "Looping disabled!",
                    color = EmbedColors.DARK
                ))

            # if looping is disabled, enable it
            else:
                self.player_loop = True
                await ctx.send(embed=discord.Embed(
                    description = "Looping enabled!",
                    color = EmbedColors.DARK
                ))

    @commands.command(name="shuffle", aliases=["sh"])
    async def _shuffle(self, ctx):
        """Shuffle command"""

        # if we're not in a channel, send an embed
        if not ctx.voice_client:
            await ctx.send(embed=discord.Embed(
                description = "I'm not playing anything right now!",
                color = EmbedColors.DANGER
            ))
            return

        # if we're in a channel, handle
        else:

            # shuffle the queue
            self.song_queue.shuffle()

            # send an embed
            await ctx.send(embed=discord.Embed(
                description = "Shuffled!",
                color = EmbedColors.DARK
            ))

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

                    # add to queue
                    await self._queue_file(
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