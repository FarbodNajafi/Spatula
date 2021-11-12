import asyncio
from collections import OrderedDict
from itertools import cycle
from random import shuffle

import discord
from async_timeout import timeout

from utils import youtube


class Player:
    __slots__ = (
        'ctx',
        'bot',
        '_guild',
        '_channel',
        '_cog',
        'queue',
        'next',
        'current',
        'np',
        'volume',
        'history',
        'iter',
        'loop',
    )

    def __init__(self, ctx):
        self.ctx = ctx
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None
        self.volume = 1.0
        self.current = None
        self.history = OrderedDict()
        self.loop = ''

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            if not self.queue.empty():
                extracted_data = next(reversed(self.history)) if (
                        self.loop == 'this' and len(self.history) > 0) else await self.queue.get()

            else:
                if self.loop == 'this':
                    try:
                        extracted_data = next(reversed(self.history.items()))

                    except StopIteration as _:
                        extracted_data = await self.queue.get()

                elif self.loop == 'queue':
                    for k, v in self.history.items():
                        await self.queue.put((k, v))

                    self.history.clear()
                    extracted_data = await self.queue.get()

                else:
                    extracted_data = await self.queue.get()

            source = self.create_source(extracted_data[1])
            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._channel.send(f'**Now Playing:** `{source.title}` requested by '
                                               f'{source.requester}')

            await self.next.wait()

            source.cleanup()
            self.history.update({extracted_data[0]: extracted_data[1]})
            self.current = None

            try:
                await self.np.delete()

            except discord.HTTPException:
                pass

    def create_source(self, data):
        filename = data['url']
        return youtube.YTDLSource(self.ctx, discord.FFmpegPCMAudio(filename, **youtube.YTDLSource.FFMPEG_OPTIONS),
                                  data=data)

    def shuffle(self):
        shuffle(self.queue._queue)

    def remove(self, index: int):
        item = self.queue._queue[index - 1]
        del self.queue._queue[index - 1]
        return item

    def destroy(self, guild, message=''):
        return self.bot.loop.create_task(self._cog.cleanup(guild, message))
