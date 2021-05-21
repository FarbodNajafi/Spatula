import asyncio

import discord
import youtube_dl
from discord.ext import commands

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': './media/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1.0):
        super().__init__(source, volume)

        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Player(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def play(self, ctx, player):
        ctx.voice_client.play(player, after=lambda e: print('player error: %s' % e) if e else None)

    @commands.command(aliases=['stop',
                               'dc',
                               ])
    async def leave(self, ctx):
        await ctx.voice_client.disconnect()

    @commands.command(aliases=['yts',
                               'play',
                               'p',
                               ])
    async def yt(self, ctx, *, query):
        async with ctx.typing():
            player = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
            await self.play(ctx, player)

        await ctx.send(f'Now playing: {player.title}')

    @commands.command()
    async def volume(self, ctx, volume: int):

        if not ctx.voice_client:
            return await ctx.send('Not connected to a voice channel.')

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    @yt.before_invoke
    async def join(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()

            else:
                await ctx.send("You're not connected to a voice channel.")
                raise commands.CommandError('Author not connected to a voice channel.')

        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @yt.error
    async def yt_error(self, ctx, error):
        if isinstance(error, IndexError):
            await ctx.send("Couldn't find the matching query. Change your query or try again.")
        await ctx.send('An error occurred while playing the audio of the given query.')
        print(error)


def setup(bot):
    bot.add_cog(Player(bot))
