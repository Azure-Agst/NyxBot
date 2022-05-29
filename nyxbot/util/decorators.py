import discord
import functools

from ..discord import EmbedColors

def ensure_bot_in_channel(func):
    """Decorator to ensure bot is within a channel"""

    @functools.wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):

        # if not in a channel, return an embed
        if ctx.voice_client is None:
            await ctx.send(embed=discord.Embed(
                description = "I'm not in a voice channel!",
                color = EmbedColors.DANGER
            ))
            return

        # return result of normal coroutine
        return await func(self, ctx, *args, **kwargs)

    # return wrapped function
    return wrapper