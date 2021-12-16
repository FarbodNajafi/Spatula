import asyncio
from urllib import parse

import discord
import yt_dlp

from discord.ext import commands

yt_dlp.utils.bug_reports_message = lambda: ''


class YTDLException(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'outtmpl': './media/%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': False,
        'default_search': 'auto',
        'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 30',
        'options': '-vn',
    }

    ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data, volume=1.0):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __getitem__(self, item):
        return self.__getattribute__(item)

    def __str__(self):
        return self.title

    @classmethod
    async def extract_data(cls, query, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(query, download=False))

        query_params = dict(parse.parse_qs(parse.urlsplit(query).query))

        filenames = []
        if not data:
            raise YTDLException("Couldn't find the youtube video matching the given query")

        if 'index' not in query_params:
            if 'entries' in data:
                for entry in data['entries']:
                    if entry:
                        filenames.append(entry)

            elif 'url' in data:
                filenames.append(data)

        else:
            filenames.append(data['entries'][
                                 int(query_params['index'][0]) - 1
                                 ])

        if not data:
            raise YTDLException("Couldn't find the youtube video matching the given query")

        for data in filenames:
            yield data

    @classmethod
    async def search_source(cls, ctx: commands.Context, query: str, *,
                            loop: asyncio.BaseEventLoop = None):
        channel = ctx.channel
        bot = ctx.bot
        author = ctx.author
        loop = loop or asyncio.get_event_loop()

        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(f'ytsearch10:"{query}"', download=False))

        cls.search = {
            'title': f'Search result for: {query}',
            'type': 'rich',
            'color': 0xf1c417,
            'author': {
                'name': f'{ctx.author.name}',
                'url': f'{ctx.author.avatar_url}',
                'icon_url': f'{ctx.author.avatar_url}',
            },
        }

        list_ = ['Type a number to pick the file or type `c` to cancel operation. \n\n']
        count = 0
        for entry in data['entries']:
            count += 1
            list_.append(
                f'**{count}**. [{entry.get("title")}]({entry["webpage_url"]}) - '
                f'{cls.parse_duration(entry.get("duration"))}')

        cls.search['description'] = '\n'.join(list_)

        em = discord.Embed.from_dict(cls.search)
        await ctx.send(embed=em, delete_after=60)

        try:
            message = await bot.wait_for('message',
                                         check=lambda msg: msg.author == author and msg.channel == channel,
                                         timeout=60)

        except asyncio.TimeoutError:
            return 'timeout'

        else:
            if message.content.isdigit():
                selection = int(message.content)
                if 0 < selection <= 10:
                    for key, val in data.items():
                        if key == 'entries':
                            video_url = val[selection - 1]['webpage_url']
                            data = await loop.run_in_executor(None,
                                                              lambda: cls.ytdl.extract_info(video_url, download=False))
                            return data

                else:
                    return 'invalid_selection'
            else:
                return 'canceled'

    @staticmethod
    def parse_duration(duration: int):
        if duration > 0:
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)

            duration = []
            if days > 0:
                duration.append(f'{days}')
            if hours > 0:
                duration.append(f'{hours}')
            if minutes > 0:
                duration.append(f'{minutes}')
            if seconds > 0:
                duration.append(f'{seconds}')

        return ':'.join(duration) if duration else 'Live'
