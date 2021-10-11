from discord.ext.commands.core import guild_only
from config import *
import re
import discord
from discord.ext import commands
from utils.profanity_checker import profanity_check
from utils.db import *
from utils.warnings import create_error_embed, create_warning_embed
from utils.custom_exceptions import *


bot = commands.Bot(command_prefix=BOT_PREFIX, owner_id=OWNER_ID, activity=discord.Game(name=f"{BOT_PREFIX}help"), help_command=None)


async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename == '__init__.py':
            continue
        if filename.endswith(".py"):
            bot.load_extension(f"cogs.{filename[:-3]}")


async def unload_extensions():
    for filename in os.listdir('./cogs'):
        if filename == '__init__.py':
            continue
        if filename.endswith(".py"):
            bot.unload_extension(f"cogs.{filename[:-3]}")


@bot.command(hidden=True)
async def reload_extensions(ctx):
    """Reloads Cogs"""
    author = ctx.message.author

    if str(author.id) != OWNER_ID:
        await ctx.reply(
            f'{author.mention} you have no permission to use this command.')
    else:
        await unload_extensions()
        await load_extensions()
        await ctx.reply('Cogs reloaded.', delete_after=5)
        await ctx.message.delete()


@bot.event
async def on_ready():
    await load_extensions()

    logger.info("Logged in as '{0.user}' successfully!".format(bot))


@guild_only()
@bot.event
async def on_message(message):
    await bot.process_commands(message)

    msg = message.content
    author = message.author

    if message.author == bot.user:
        return
    else:
        add_guild_data(author.guild)
        add_member_data(author)

    if msg.startswith(BOT_PREFIX):
        return

    message_words = re.findall(r"[\w']+|[.,!?;]", msg)

    for word in message_words:
        if profanity_check(word):
            if str(author.id) == OWNER_ID:
                return await message.channel.send(f'Oww 😨, BOSS {message.author.mention} !')

            warnings = get_member_warnings_count(author.id) + 1

            if warnings < 3:
                await message.reply(f'{author.mention}, hey, really?! Please write without bad words, ok? This is `{warnings}` warning!')
            elif warnings >= 3:
                await message.reply(f'{author.mention}, seems like u ignore my requests! Soooo, whole chat now ignore yours messages. Happy now?')
                await message.channel.set_permissions(
                    message.author,
                    add_reactions=False,
                    send_messages=False,
                    reason='Bad words in chat'
                )
                await message.channel.send(f'User `{message.author}` cannot write into this channel now.')

            return add_offend(message.author, message.channel.id, msg)


@bot.command()
async def ping(ctx: commands.Context):
    """Pong! Shows the client latency"""
    await ctx.send('Pong!({}ms)'.format(round(bot.latency*1000)))
    logger.info(f'Ping command call by {ctx.message.author}')


@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.errors.CommandNotFound):
        await ctx.message.reply(embed=create_warning_embed('There are no such command!'))
    elif isinstance(error, commands.MissingRequiredArgument):
        pass
    elif isinstance(error, NotConnected):
        return await ctx.message.reply(embed=create_warning_embed('Nope!\n\nConnect to voice, to do that.'))
    elif isinstance(error, IncorrectVoiceChannel):
        channel_name = ctx.voice_client.channel.name
        return await ctx.message.reply(embed=create_warning_embed(f"Nope!\n\nConnect to my - **{channel_name}** voice, to do that."))
    elif isinstance(error, commands.MissingPermissions):
        return await ctx.message.reply(embed=create_warning_embed(f"Nope!\n\You don't have such permissions."))
    else:
        await ctx.send(embed=create_error_embed('Nice! You found a bug...'))
        logger.error(error)


bot.run(BOT_TOKEN)
