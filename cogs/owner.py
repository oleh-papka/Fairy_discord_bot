import discord
from discord import Colour
from discord.embeds import Embed
from discord.ext import commands
from config import BOT_PREFIX, BOT_VERSION, BOT_STARTED_AT, time, OWNER_NAME
from datetime import datetime


class Stats(commands.Cog):
    """Bot statistic commnads"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['stats'])
    async def stats_bot(self, ctx: commands.Context):
        bot = self.bot
        guild_count = len(bot.guilds)
        users_count = 0
        for guild in bot.guilds:
            users_count += guild.member_count
        
        latency = round(bot.latency, 2)
        up_time = time.time() - BOT_STARTED_AT
        up_time = datetime.utcfromtimestamp(up_time).strftime('%H:%M:%S')

        embed = Embed(
            colour=Colour.greyple(),
            title='ℹ️  Bot info'
        )

        embed.add_field(name='Managing servers:',
                        value=guild_count)

        embed.add_field(name='Users sum:',
                        value=users_count)

        embed.add_field(name='Bot latency:',
                        value=f'{latency}s')

        embed.add_field(name='Bot uptime:',
                        value=up_time)

        embed.add_field(name='Bot prefix:',
                        value=f'For commands use: `{BOT_PREFIX}`')

        embed.add_field(name='Additional',
                        value=f'The bot is developed by `{OWNER_NAME}`, based on discord.py\nCurrently running {BOT_VERSION}\nRepo: (soon)',
                        inline=False)

        embed.set_footer(
            text=f"Need help? Use -'{BOT_PREFIX}help' to get more info about commands.")

        embed.set_author(name=bot.user, url='https://youtu.be/dQw4w9WgXcQ')
        embed.set_thumbnail(url=bot.user.avatar_url)

        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Stats(bot))
