import discord
from discord.ext import commands
from discord.errors import Forbidden
from config import BOT_VERSION, OWNER_NAME, BOT_PREFIX
from utils.warnings import create_error_embed, create_warning_embed
from discord.ext.commands.core import guild_only
from utils.db import remove_all_offends, remove_offends


async def send_embed(ctx, embed):
    try:
        await ctx.send(embed=embed)
    except Forbidden:
        await ctx.send('Damn... Seems like I cannot send embeds, please contact server admins.\n\nhttps://youtu.be/dQw4w9WgXcQ')


class Help(commands.Cog):
    """Sends this help message"""

    def __init__(self, bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command(name='help', help="Shows command info")
    async def help(self, ctx, *input):

        if not input:
            emb = discord.Embed(title='Commands and modules',
                                color=discord.Color.green(),
                                description=f'Use `{BOT_PREFIX}help <module>` to get more info about module\n')

            cogs_desc = ''
            for cog in self.bot.cogs:
                cogs_desc += f'`{cog}` {self.bot.cogs[cog].__doc__}\n'

            emb.add_field(name='Modules', value=cogs_desc, inline=False)

            commands_desc = ''
            for command in self.bot.walk_commands():
                if not command.cog_name and not command.hidden:
                    commands_desc += f'{command.name} - {command.help}\n'

            if commands_desc:
                emb.add_field(name='Not belonging to a module',
                              value=commands_desc, inline=False)

            emb.add_field(name="About",
                          value=f'The bot is developed by `{OWNER_NAME}`, based on discord.py.\n\
                                Repo: (soon)')

            emb.set_footer(text=f"Bot is running {BOT_VERSION}")

        elif len(input) == 1:
            for cog in self.bot.cogs:
                if cog.lower() == input[0].lower():
                    emb = discord.Embed(title=f'{cog} - Commands',
                                        description=self.bot.cogs[cog].__doc__,
                                        color=discord.Color.green())
                    output = ''
                    for command in self.bot.get_cog(cog).get_commands():
                        if not command.hidden:
                            output += f"`{BOT_PREFIX}{command.name}` - {command.help}\n"

                    emb.add_field(name='Info:', value=output)
                    break
            else:
                emb = create_warning_embed(
                    f'Hmmm, never heard about module called `{input[0]}` before...')
        elif len(input) > 1:
            emb = create_warning_embed(
                'Please request only one module at once.')
        else:
            emb = create_error_embed(
                'Strange... very strange, IDK what happened 😰!')

        await send_embed(ctx, emb)


class Server_related(commands.Cog):
    """Server related commands"""

    def __init__(self, bot):
        self.bot = bot

    @guild_only()
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def forgive(self, ctx: commands.Context, member: discord.Member):
        """Forgive the user in channel"""

        guild_id = ctx.guild.id

        if member.id == self.bot.user.id:
            await ctx.message.reply('DUDE! LET ME IN!')
        else:
            remove_offends(member.id, ctx.message.channel.id, guild_id)

            await ctx.message.channel.set_permissions(
                member,
                add_reactions=True,
                send_messages=True,
                reason='Forgiven'
            )
            await ctx.message.reply(f'User {member.mention} was forgiven for current channel.')

    @guild_only()
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def forgive_all(self, ctx: commands.Context, member: discord.Member):
        """Forgive the user in server"""

        guild_id = ctx.guild.id

        if member.id == self.bot.user.id:
            await ctx.message.reply('DUDE! LET ME IN!')
        else:
            remove_all_offends(member.id, guild_id)

            await ctx.message.channel.set_permissions(
                member,
                add_reactions=True,
                send_messages=True,
                reason='Forgiven'
            )
            await ctx.message.reply(f'User {member.mention} was forgiven for current server.')

    @forgive.error
    @forgive_all.error
    async def forgive_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.message.reply(embed=create_warning_embed('Please specify user to forgive.'))

    @guild_only()
    @commands.has_permissions(administrator=True)
    @commands.command(name='clear', help='Clear messages in channel')
    async def clear(self, ctx: commands.Context, *, amount=5):
        if amount == 1:
            amount = 2
        await ctx.channel.purge(limit=amount)



def setup(bot):
    bot.add_cog(Help(bot))
    bot.add_cog(Server_related(bot))
