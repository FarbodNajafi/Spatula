import asyncio

import discord
from async_timeout import timeout


class Player:
    __slots__ = (
        'bot',
        '_guild',
        '_channel',
        '_cog',
        'queue',
        'next',
        'current',
        'np',
        'volume',
    )

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None
        self.volume = 1.0
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
#                 async with timeout(300):
                source = await self.queue.get()

            except asyncio.TimeoutError:
                await self._channel.send('Bot disconnected due to inactivity', delete_after=20)
#                 return self.destroy(self._guild)

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._channel.send(f'**Now Playing:** `{source.title}` requested by '
                                               f'{source.requester}')

            await self.next.wait()

            source.cleanup()
            self.current = None

            try:
                await self.np.delete()

            except discord.HTTPException:
                pass

    def destroy(self, guild, message=''):
        return self.bot.loop.create_task(self._cog.cleanup(guild, message))
