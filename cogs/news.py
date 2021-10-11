import discord
from discord.ext import commands
from utils.weather import get_weather


class News(commands.Cog):
    """Grab some news"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def weather(self, ctx: commands.Context):
        """Shows weather in Ternopil for current day"""
        await ctx.send(get_weather())


def setup(bot):
    bot.add_cog(News(bot))

