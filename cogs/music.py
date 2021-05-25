import asyncio
import itertools
import sys
import traceback

import discord
from discord.ext import commands

from utils import youtube
from utils.player import Player


class VoiceConnectionError(commands.CommandError):
    pass


class InvalidVoiceChannel(VoiceConnectionError):
    pass


class Music(commands.Cog):
    __slots__ = (
        'bot',
        'players',
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild, message=''):
        try:
            await guild.voice_client.disconnect()

        except AttributeError:
            pass

        try:
            del self.players[guild.id]

        except KeyError:
            pass

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage

        return True

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command cannot be used in DM')

            except discord.HTTPException:
                pass

        elif isinstance(error, InvalidVoiceChannel):
            return await ctx.send('Error connecting to voice channel'
                                  'Please make sure you are in a voice channel which is visible to me')

        print(f'Ignoring exception in command {ctx.command}', file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]

        except KeyError:
            player = Player(ctx)
            self.players[ctx.guild.id] = player

        return player

    @commands.command(aliases=['stop',
                               'dc',
                               ])
    async def leave(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a voice channel", delete_after=20)

        await self.cleanup(ctx.guild)

    @commands.command(aliases=['yts',
                               'yt',
                               'p',
                               'sing'
                               ])
    async def play(self, ctx, *, query):
        player = self.get_player(ctx)

        source = await youtube.YTDLSource.create_source(ctx, query, loop=self.bot.loop)

        await player.queue.put(source)
        await ctx.send(f'{ctx.author.mention}, Enqueued: {source.title}') if player.queue.qsize() > 1 else None

    @commands.command(aliases=[
        'pa',
    ])
    async def pause(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            return await ctx.send("I'm not playing anything right now!", delete_after=20)

        elif vc.is_paused():
            return await ctx.send('Player is paused', delete_after=20)

        vc.pause()
        await ctx.send(f'{ctx.author.mention}, player paused.')

    @commands.command(aliases=[
        'res',
    ])
    async def resume(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a voice channel", delete_after=20)

        elif not vc.is_paused():
            return

        vc.resume()
        await ctx.send(f'{ctx.author.mention}, player resumed.')

    @commands.command(aliases=[
        'sk',
    ])
    async def skip(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a voice channel", delete_after=20)

        elif vc.is_paused():
            pass

        elif not vc.is_playing():
            return

        vc.stop()
        await ctx.send(f'{ctx.author.mention}, skipped')

    @commands.command(aliases=[
        'q',
    ])
    async def queue(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a voice channel", delete_after=20)

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send('Queue is empty.')

        upcoming = list(itertools.islice(player.queue._queue, 0, 5))

        fmt = '\n'.join(f'**{item["title"]}**' for item in upcoming)
        embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)

        await ctx.send(embed=embed)

    @commands.command(aliases=[
        'np',
        'current',
        'playing',
        'now'
    ])
    async def nowplaying(self, ctx):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a voice channel", delete_after=20)

        player = self.get_player(ctx)
        if not player.current:
            return await ctx.send("I'm not playing anything right now")

        try:
            await player.np.delete()

        except discord.HTTPException:
            pass

        player.np = await ctx.send(f'**Now Playing:** `{vc.source.title}` requested by '
                                   f'{vc.source.requster}')

    @commands.command(aliases=[
        'vol',
        'vl',
    ])
    async def volume(self, ctx, volume: int):
        """Change the player volume.
                Parameters
                ------------
                volume: float or int [Required]
        """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a voice channel", delete_after=20)

        if not 0 <= volume <= 100:
            return await ctx.send('Please enter a value between 0 and 100.')

        player = self.get_player(ctx)

        player.volume = volume / 100
        await ctx.send(f'{ctx.author.mention}, volume set to **{volume}%**')

    @commands.command(aliases=[
        'summon',
    ])
    @play.before_invoke
    async def join(self, ctx, *, channel: discord.VoiceChannel = None):
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise InvalidVoiceChannel('No channel to join. Please join a channel or specify one.')

        vc = ctx.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return

            try:
                await vc.move_to(channel)

            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Moving to channel `{channel}` timed out.')

        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Connecting to channel `{channel}` timed out.')

        await ctx.send(f'Connected to **{channel}**', delete_after=20)

    @play.error
    async def play_error(self, ctx, error):
        if isinstance(error, IndexError):
            await ctx.send("Couldn't find the matching query. Change your query or try again.")
        await ctx.send('An error occurred while playing the audio of the given query.')
        print(error)


def setup(bot):
    bot.add_cog(Music(bot))
