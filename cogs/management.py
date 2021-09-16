from itertools import cycle

import discord
from discord.ext import commands, tasks

from utils.utils import BotModes, get_mode, get_prefix


class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._status = cycle([
            {'func': self.bot.change_presence, 'status': discord.Status.dnd,
             'activity': discord.Activity(name=f'{get_prefix()}ping', type=5)},
            {'func': self.bot.change_presence, 'status': discord.Status.idle,
             'activity': discord.Activity(
                 name=f'{get_prefix()}help must do something'
                      f'{" evil" if get_mode() == BotModes.DEV.value else " new" if get_mode() == BotModes.NIGHTLY.value else "spooky"}...',
                 type=2)},
            {'func': self.bot.change_presence, 'status': discord.Status.online,
             'activity': discord.Activity(name='API Documents', type=3)}
        ])

    @commands.Cog.listener()
    async def on_connect(self):
        print('Connected to Discord servers')

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Activity(name="Hi ✋", type=0))
        print('Logged on as', self.bot.user)
        await self.change_status.start()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f'{member} joined the server')

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        print(f'{member} left the server')

    @property
    def status(self):
        return next(self._status)

    @tasks.loop(seconds=10)
    async def change_status(self):
        status = self.status
        await status['func'](status=status['status'], activity=status['activity'])


def setup(bot):
    bot.add_cog(Management(bot))
