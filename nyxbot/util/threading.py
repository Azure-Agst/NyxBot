import functools
import typing
import asyncio

def to_thread(func: typing.Callable) -> typing.Coroutine:

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):

        loop = asyncio.get_event_loop()

        wrapped = functools.partial(func, *args, **kwargs)

        return await loop.run_in_executor(None, wrapped)
    
    return wrapper

async def run_blocking(bot, blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
    """Runs a blocking function in a non-blocking way"""

    # `run_in_executor` doesn't support kwargs, `functools.partial` does
    func = functools.partial(blocking_func, *args, **kwargs)

    return await bot.loop.run_in_executor(None, func)