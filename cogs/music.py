import re
import discord
import asyncio
from discord import channel
import youtube_dl
from config import BOT_PREFIX, logger
import tabulate
from discord.ext import commands, tasks
import functools
import typing
from utils.db import (add_playlist, add_playlists_tracks, add_track, check_if_playlist_name_taken, check_if_track_exists_by_url, get_all_guilds,
                      get_all_playlists, get_playlist_data, get_track_data, get_track_data_by_url, get_tracks_data_in_playlist, get_tracks_in_playlist, remove_playlist)
from utils.warnings import create_warning_embed
from utils.custom_exceptions import *
import random
import string
from pytube import YouTube, Playlist
from concurrent.futures import ThreadPoolExecutor, as_completed

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'skip_download': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'forceduration': True,
    'default_search': 'auto',
    # bind to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


def youtube_url_validation(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(music.youtube|youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=|playlist\?)([^&=%\?]{11}|list=[^&=%\?]{43}|list=[^&=%\?]{34})')

    if re.match(youtube_regex, url):
        return False
    return True


def get_video_info(link):
    if 'start_radio=1' in link:
        link = link[:43]

    if '&t=' in link:
        link = link.split('&t=', 1)[0]

    yt_obj = YouTube(link)
    title = yt_obj.title
    length = yt_obj.length
    return {'title': title, 'url': link, 'duration': length}


class Music(commands.Cog):
    """Music related commands"""

    def __init__(self, bot):
        self.bot = bot
        self.queues: dict[int: dict[    # guild_id : dict of guild queues
            # queue : list of tracks {'embed', 'source','title','duration'
            str: list,
            str: int,   # index : index of current playing track
            str: int,   # queue message id
            str: int,   # player message id
            str: int    # loop flag
        ]] = dict()
        self.check_if_bot_alone.start()

    async def run_blocking(self, blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
        """Runs a blocking function in a non-blocking way"""
        func = functools.partial(
            blocking_func, *args, **kwargs)  # `run_in_executor` doesn't support kwargs, `functools.partial` does
        return await self.bot.loop.run_in_executor(None, func)

    @staticmethod
    def parse_duration(duration):
        if duration == 0:
            return 'Livestream'

        m, s = divmod(duration, 60)
        h, m = divmod(m, 60)
        return f'{h:d}:{m:02d}:{s:02d}'

    @staticmethod
    def get_source(url: str):
        info = ytdl.extract_info(url, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        source = info['formats'][0]['url']

        return source

    @staticmethod
    def get_track(url: str):
        if check_if_track_exists_by_url(url):
            track = get_track_data_by_url(url)[0]
            title = track[0]
            duration = track[1]
            return [{'url': url, 'title': title, 'duration': duration}]

        try:
            if 'start_radio=1' in url:
                url = url[:43]
                data = [get_video_info(url)]
                return data

            video_links = Playlist(url)

            processes = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                for link in video_links:
                    processes.append(executor.submit(get_video_info, link))

            data = []
            for task in as_completed(processes):
                info = task.result()
                title = info['title']
                duration = info['duration']
                url = info['url']
                add_track(title, url, duration)
                data.append({'url': url, 'title': title, 'duration': duration})

            if data == []:
                raise Exception
            else:
                return data

        except:  # if its a stream
            info = ytdl.extract_info(url, download=False)
            if 'entries' in info:

                info = info['entries'][0]
            source = info['formats'][0]['url']
            title = info['title']
            duration = info['duration']

            if duration == 0.0:
                duration = 0

            return [{'source': source, 'url': url, 'title': title, 'duration': duration}]

    def create_queue_embed(self, ctx: commands.Context):
        headers = ['#', 'Name', 'Duration']
        guild = ctx.guild.id
        queue = self.queues[guild]['queue']
        index = self.queues[guild]['index']+1
        cntr = 1
        footer = None
        table = []
        max_queue_tracks = 10
        tracks_num = len(queue)

        if tracks_num > max_queue_tracks:
            queue = queue[index-1:]

            if index != 1:
                cntr = index

        for song in queue:
            if cntr > max_queue_tracks + index-1:
                footer = 'The pagination will be done as soon as the developer will write it...'
                break

            title = song['title']
            if len(title) > 17:
                title = title[:17] + '...'

            symb = cntr
            if index == cntr:
                symb = '▷'

                if self.queues[guild]['loop']:
                    symb = '⟳'

            table.append(
                [symb, title, self.parse_duration(song['duration'])])
            cntr += 1

        output_table = tabulate.tabulate(
            table, headers=headers, tablefmt='fancy_grid')

        # if index == tracks_num:
        #     index -= 1

        embed = discord.Embed(
            colour=discord.Color.blue(),
            title=f'🎵  Queue ({index} / {tracks_num}):',
            description=f'```{output_table}```'
        )

        if footer != None:
            embed.set_footer(text=footer)

        return embed

    def create_player_embed(self, ctx: commands.Context):

        guild = ctx.guild.id
        queue = self.queues[guild]['queue']
        index = self.queues[guild]['index']

        channel_name = ctx.voice_client.channel.name
        tracks_num = len(queue)

        voice = ctx.voice_client
        if voice.is_playing() or voice.is_paused():
            embed = discord.Embed(
                colour=discord.Colour.teal(),
                title=f'🎶  Player in **{channel_name}**',
                description=f'Playing: {index+1} / {tracks_num}'
            )
            current_track = queue[index]
            current_track_title = current_track['title']

            if len(current_track_title) > 30:
                current_track_title = current_track_title[:30] + '...'

            current_track_duration = Music.parse_duration(
                current_track['duration'])

            if not self.queues[guild]['loop']:
                embed.add_field(
                    name='🔊  Current track:',
                    value=f'{current_track_title} - ({current_track_duration})')
            else:
                embed.add_field(
                    name='🔊  Current track:',
                    value=f'{current_track_title} - ({current_track_duration})\n\n🔁 Повторне програвання ввмікнено!')

            if tracks_num > 1 and not self.queues[guild]['loop']:
                if index+1 == tracks_num:
                    return embed

                next_track = queue[index+1]
                next_track_title = next_track['title']

                if len(next_track_title) > 30:
                    next_track_title = next_track_title[:30] + '...'

                next_track_duration = Music.parse_duration(
                    next_track['duration'])

                embed.add_field(
                    name='➡️  Next track:',
                    value=f'{next_track_title} - ({next_track_duration})')
        else:
            embed = discord.Embed(
                colour=discord.Colour.teal(),
                title=f'🎶  Player in **{channel_name}**',
                description=f'Player reached the end of queue: {index} / {tracks_num}'
            )
            index -= 1
            prev_track = queue[index]
            prev_track_title = prev_track['title']

            if len(prev_track_title) > 30:
                prev_track_title = prev_track_title[:30] + '...'

            prev_track_duration = Music.parse_duration(
                prev_track['duration'])

            embed.add_field(
                name='🔊  Previous track:',
                value=f'{prev_track_title} - ({prev_track_duration})')

        return embed

    async def _join(self, ctx: commands.Context):
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    def play_next(self, error, voice, ctx: commands.Context):
        if error:
            logger.error(f'Player error: {error}')

        guild = ctx.guild.id

        try:
            queue = self.queues[guild].get('queue')
        except:
            return

        if queue is None:
            return

        index = self.queues[guild]['index']
        tracks_num = len(queue)-1

        if not self.queues[guild]['loop']:
            if tracks_num <= index:
                self.queues[guild]['index'] = index+1
                return
            elif tracks_num > index:
                self.queues[guild]['index'] = index+1

                index += 1

        track = self.queues[guild]['queue'][index]

        try:
            source = track['source']
        except:
            url = track['url']
            info = ytdl.extract_info(url, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            source = info['formats'][0]['url']

        voice.play(discord.FFmpegPCMAudio(source, **ffmpeg_options),
                   after=lambda e: self.play_next(e, voice, ctx))

        title = track['title']
        duration = track['duration']
        url = track['url']

        embed = (discord.Embed(title='Track:', description=title, color=discord.Color.gold()).add_field(
            name='Duration', value=Music.parse_duration(duration)).add_field(name='URL', value=(url)))

        asyncio.run_coroutine_threadsafe(ctx.send(
            embed=embed, delete_after=5), self.bot.loop)

    @commands.guild_only()
    @commands.command(aliases=['p'])
    async def play(self, ctx: commands.Context, *, url):
        """Stream audio from a YT url"""

        if youtube_url_validation(url):
            await ctx.message.reply('Please provide correct YT or YTMusic link.')
            await ctx.send(f'Usage example: \'{BOT_PREFIX}play https://www.youtube.com/watch?v=xr-uFewQzfY\'')
            return

        voice = ctx.voice_client
        guild = ctx.guild.id
        try:
            channel = ctx.message.author.voice.channel
        except:
            return

        async with ctx.typing():
            await ctx.reply('⏳ Processing, this could take some time...', delete_after=5)

            if channel:
                if guild in self.queues:
                    queue = self.queues[guild]['queue']
                    queue.extend(await self.run_blocking(self.get_track, url))
                    self.queues[guild]['loop'] = False
                else:
                    self.queues[guild] = {
                        'queue': await self.run_blocking(self.get_track, url), 'index': 0, 'loop': False}

                if voice and voice.is_connected():
                    await voice.move_to(channel)
                else:
                    voice = await channel.connect()

                if voice.is_playing() or voice.is_paused() and url:
                    await ctx.reply('⬆️ Track added to queue.', delete_after=5)

                if not voice.is_playing():
                    index = self.queues[guild]['index']
                    track = self.queues[guild]['queue'][index]
                    url = track['url']
                    title = track['title']
                    duration = track['duration']

                    source = await self.run_blocking(self.get_source, url)

                    embed = (discord.Embed(title='Track:', description=title, color=discord.Color.gold())
                             .add_field(name='Duration', value=Music.parse_duration(duration))
                             .add_field(name='URL', value=(url)))

                    voice.play(discord.FFmpegPCMAudio(
                        source, **ffmpeg_options), after=lambda e: self.play_next(e, voice, ctx))

                    await ctx.send(embed=embed, delete_after=30)

        logger.info(f'Play command call by {ctx.message.author}')

    @commands.guild_only()
    @commands.command(aliases=['pl'])
    async def player(self, ctx: commands.Context):
        """Player instance"""

        voice = ctx.voice_client
        guild = ctx.guild.id
        emojis = ['⏮️', '⏯️', '⏭️', '🔁', '🔀', '⏹️', '📄']

        if voice and voice.is_connected():

            await ctx.channel.purge(limit=1)
            if message_id := self.queues[guild].get('player_message_id'):
                try:
                    msg = await ctx.channel.fetch_message(message_id)
                    await msg.delete()
                except:
                    pass

            message = await ctx.send(embed=self.create_player_embed(ctx))
            self.queues[guild]['player_message_id'] = message.id
            for i in emojis:
                await message.add_reaction(i)
        else:
            await ctx.reply(embed=create_warning_embed('Queue not found!'))

    @commands.guild_only()
    @commands.command(name='pause')
    async def pause_command(self, ctx: commands.Context, flag=False):
        """Pause or resume playing"""
        voice = ctx.voice_client
        if voice.is_playing():
            voice.pause()
            await ctx.send('⏸️ Pause.', delete_after=5)
        elif voice.is_paused():
            voice.resume()
            await ctx.send("▶️ let's rock and roll.", delete_after=5)
        else:
            return await ctx.reply(embed=create_warning_embed('There are no tracks to play!'))

        if flag:
            await ctx.channel.purge(limit=1)

        logger.info(f'Pause command call by {ctx.message.author}')

    @commands.guild_only()
    @commands.command(aliases=['n', 'skip'])
    async def next(self, ctx: commands.Context, send_embed=False):
        """Play next song form queue"""

        guild = ctx.guild.id
        voice = ctx.voice_client

        if voice and voice.is_playing():
            self.queues[guild]['loop'] = False
            queue_len = len(self.queues[guild]['queue'])-1
            index = self.queues[guild]['index']
            await ctx.channel.purge(limit=1)

            if index == queue_len:
                await ctx.send(embed=create_warning_embed('You reached the end of the queue.'), delete_after=5)
                return

            await ctx.send('⏭️ Next track.', delete_after=5)
            voice.stop()

            if send_embed:
                await self.player(ctx)
        else:
            await ctx.send(embed=create_warning_embed("Hmm... I'm not playing anything!"), delete_after=5)

    @commands.guild_only()
    @commands.command(aliases=['prev'])
    async def previous(self, ctx: commands.Context, send_embed=False):
        """Play previous song form queue"""

        guild = ctx.guild.id
        voice = ctx.voice_client
        index = self.queues[guild]['index']
        # queue = self.queues[guild]
        tracks_num = len(self.queues[guild]['queue'])

        if voice and voice.is_playing() or index == tracks_num:
            self.queues[guild]['loop'] = False
            await ctx.channel.purge(limit=1)

            if index == 0:
                await ctx.send(embed=create_warning_embed('You reached the very begining of the queue.'), delete_after=5)
                return

            await ctx.send('⏮️ Previous track.', delete_after=5)
            self.queues[guild]['index'] = index-2

            if voice.is_playing():
                voice.stop()
            else:
                index -= 1
                self.queues[guild]['index'] = index
                voice.play(discord.FFmpegPCMAudio(
                    self.queues[guild]['queue'][index]['source'], **ffmpeg_options), after=lambda e: self.play_next(e, voice, ctx))

                await ctx.send(embed=self.queues[guild]['queue'][index]['embed'], delete_after=30)

            if send_embed:
                await self.player(ctx)
        else:
            await ctx.send(embed=create_warning_embed("Hmm... I'm not playing anything!"), delete_after=5)

    @commands.guild_only()
    @commands.command(aliases=['loop'])
    async def loop_command(self, ctx: commands.Context, send_embed=False):
        """Loop current song form queue"""

        guild = ctx.guild.id
        voice = ctx.voice_client

        if voice and voice.is_playing():
            await ctx.channel.purge(limit=1)

            if self.queues[guild]['loop']:
                self.queues[guild]['loop'] = False
                await ctx.send('➡️ Back to normal.', delete_after=5)
            else:
                self.queues[guild]['loop'] = True
                await ctx.send('🔁 Looping current track.', delete_after=5)

            if send_embed:
                await self.player(ctx)
        else:
            await ctx.send(embed=create_warning_embed("Hmm... I'm not playing anything!"), delete_after=5)

    @commands.guild_only()
    @commands.command(aliases=['shuffle'])
    async def shuffle_command(self, ctx: commands.Context, send_embed=False):
        """Shuffle songs in the queue"""

        guild = ctx.guild.id
        voice = ctx.voice_client

        if voice and voice.is_playing():
            self.queues[guild]['loop'] = False
            self.queues[guild]['index'] = -1
            queue = self.queues[guild]['queue']
            random.shuffle(queue)
            self.queues[guild]['queue'] = queue

            await ctx.channel.purge(limit=1)
            await ctx.send("🔀 Let's shuffle it.", delete_after=5)

            voice.stop()

            if send_embed:
                await self.queue(ctx, False)
        else:
            await ctx.send(embed=create_warning_embed("Hmm... I'm not playing anything!"), delete_after=5)

    @commands.guild_only()
    @commands.command(aliases=['q'])
    async def queue(self, ctx: commands.Context, del_prev_msg=True):
        """Display music queue"""

        voice = ctx.voice_client
        guild = ctx.guild.id

        if voice and voice.is_connected():
            if del_prev_msg:
                await ctx.channel.purge(limit=1)

            if message_id := self.queues[guild].get('queue_message_id'):
                try:
                    msg = await ctx.channel.fetch_message(message_id)
                    await msg.delete()
                except:
                    pass

            message = await ctx.send(embed=self.create_queue_embed(ctx))
            self.queues[guild]['queue_message_id'] = message.id
        else:
            await ctx.reply(embed=create_warning_embed('Queue not found!'))

    @commands.guild_only()
    @commands.command(aliases=['disconnect', 'leave', 's'])
    async def stop_command(self, ctx: commands.Context):
        """Stop and disconnect the bot from voice"""
        guild = ctx.guild.id

        if (voice := ctx.voice_client) is None:
            return await ctx.channel.purge(limit=1)

        if voice.is_connected():
            voice.stop()
            await voice.disconnect()

            try:
                if message_id := self.queues[guild].get('player_message_id'):
                    msg = await ctx.channel.fetch_message(message_id)
                    await msg.delete()
            except:
                pass

            try:
                if message_id := self.queues[guild].get('queue_message_id'):
                    msg = await ctx.channel.fetch_message(message_id)
                    await msg.delete()
            except:
                pass

            del self.queues[guild]

        await ctx.channel.purge(limit=1)
        await ctx.send('⏹️ Stopped.', delete_after=5)
        logger.info(f'Stop command call by {ctx.message.author}')

    @commands.guild_only()
    @commands.command(aliases=['current', 'np'])
    async def now_playing(self, ctx: commands.Context):
        """Display current playing song"""
        await ctx.channel.purge(limit=1)

        guild = ctx.guild.id
        index = self.queues[guild]['index']
        song = self.queues[guild]['queue'][index]['embed']

        await ctx.send(embed=song)

    @commands.guild_only()
    @commands.command(aliases=['del_queue'])
    async def delete_queue(self, ctx: commands.Context):
        """Remove tracks from queue"""
        await ctx.channel.purge(limit=1)
        guild = ctx.guild.id

        if self.queues.get(guild) is None:
            return await ctx.send(embed=create_warning_embed('No queue to delete!'), delete_after=5)

        if (voice := ctx.voice_client) is None:
            del self.queues[guild]
        else:
            if voice.is_connected():
                voice.stop()
                await voice.disconnect()
                if message_id := self.queues[guild].get('queue_message_id'):
                    msg = await ctx.channel.fetch_message(message_id)
                    await msg.delete()
                del self.queues[guild]

        await ctx.send('Queue deleted.', delete_after=5)

    @commands.guild_only()
    @commands.command(aliases=['d'])
    async def delete_track(self, ctx: commands.Context, *, num):
        """Delete track by number"""

        guild = ctx.guild.id
        queue = self.queues[guild]['queue']
        voice = ctx.voice_client

        try:
            num = int(num)-1
        except:
            return await ctx.send(embed=create_warning_embed('Please provide track number.'))

        tracks_num = len(queue)

        if num not in range(tracks_num):
            return await ctx.send(embed=create_warning_embed('Please provide correct track number!'))

        if queue is None:
            return await ctx.send(embed=create_warning_embed('No queue to delete track from!'), delete_after=5)
        else:
            if voice and voice.is_connected():
                self.queues[guild]['loop'] = False
                index = self.queues[guild]['index']
                message_id = self.queues[guild]['queue_message_id']

                if voice.is_playing() or voice.is_paused() and num:
                    if num == index:
                        # current song playing
                        if tracks_num-1 == index and index == 0:
                            # there are no songs left
                            await self.stop_command(ctx)
                            return
                        elif tracks_num-1 == index:
                            # song is a last in queue
                            index -= 1
                            queue.pop(index)
                            self.queues[guild]['index'] = index
                        elif index == 0:
                            queue.pop(index)
                            index -= 1
                            self.queues[guild]['index'] = index
                            voice.stop()
                        else:
                            index -= 1
                            queue.pop(index)
                            self.queues[guild]['index'] = index
                            voice.stop()
                    elif num > index:
                        queue.pop(index)
                    else:
                        index -= 1
                        queue.pop(index)
                        self.queues[guild]['index'] = index

                    msg = await ctx.channel.fetch_message(message_id)
                    await msg.delete()

                    await self.queue(ctx)

                    return await ctx.send('Ok song gone!.', delete_after=5)
                else:
                    return await ctx.send(embed=create_warning_embed("Hmm... I'm not playing anything!"), delete_after=5)
            else:
                return await ctx.send(embed=create_warning_embed("Hmm... I'm not playing anything!"), delete_after=5)

    @commands.guild_only()
    @commands.command(aliases=['j'])
    async def jump_to_track(self, ctx: commands.Context, *, num):
        """Jump to track by number"""

        guild = ctx.guild.id
        queue = self.queues[guild]['queue']
        voice = ctx.voice_client

        await ctx.channel.purge(limit=1)

        try:
            num = int(num)-1
        except:
            return await ctx.send(embed=create_warning_embed('Please provide track number.'))

        tracks_num = len(queue)

        if num not in range(tracks_num):
            return await ctx.send(embed=create_warning_embed('Please provide correct track number!'))

        if queue is None:
            return await ctx.send(embed=create_warning_embed('No queue to jump to track!'), delete_after=5)
        else:
            if voice and voice.is_connected():
                self.queues[guild]['loop'] = False
                index = self.queues[guild]['index']
                message_id = self.queues[guild]['queue_message_id']

                if voice.is_playing() or voice.is_paused() and num:
                    if num == index:
                        return await ctx.send(embed=create_warning_embed('This song is playing now.'), delete_after=5)
                    else:
                        self.queues[guild]['index'] = num-1
                        voice.stop()

                    msg = await ctx.channel.fetch_message(message_id)
                    await msg.delete()

                    await self.queue(ctx)

                    return await ctx.send('Ок, йдем до іншої пісеньки.', delete_after=5)
                else:
                    return await ctx.send(embed=create_warning_embed("Hmm... I'm not playing anything!"), delete_after=5)
            else:
                return await ctx.send(embed=create_warning_embed("Hmm... I'm not playing anything!"), delete_after=5)

    @commands.guild_only()
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        guild = user.guild.id

        if reaction.message.id != self.queues[guild]['player_message_id']:
            return

        if not user.bot:
            await reaction.remove(user)
        else:
            return

        if reaction.emoji == '⏮️':
            ctx = await self.bot.get_context(reaction.message)
            return await self.previous(ctx, True)

        elif reaction.emoji == '⏭️':
            ctx = await self.bot.get_context(reaction.message)
            return await self.next(ctx, True)

        elif reaction.emoji == '⏯️':
            ctx = await self.bot.get_context(reaction.message)
            return await self.pause_command(ctx)

        elif reaction.emoji == '📄':
            ctx = await self.bot.get_context(reaction.message)
            return await self.queue(ctx, False)

        elif reaction.emoji == '🔁':
            ctx = await self.bot.get_context(reaction.message)
            return await self.loop_command(ctx, True)

        elif reaction.emoji == '🔀':
            ctx = await self.bot.get_context(reaction.message)
            return await self.shuffle_command(ctx, True)

        elif reaction.emoji == '⏹️':
            ctx = await self.bot.get_context(reaction.message)
            return await self.stop_command(ctx)

    @commands.guild_only()
    @commands.command(aliases=['save_to_playlist', 'save_p', 'save'])
    async def queue_to_playlist(self, ctx: commands.Context, *, name):
        """Save tracks from queue to playlist"""

        guild_id = ctx.guild.id

        if check_if_playlist_name_taken(name, guild_id):
            rand_name = ''.join([random.choice(
                string.ascii_letters + string.digits + string.punctuation) for n in range(12)])

            return await ctx.reply(embed=create_warning_embed(f'Seems like playlist with that name already exists!\n\nWanna name it `{rand_name}`?'))

        await ctx.channel.purge(limit=1)

        queue = self.queues[guild_id]['queue']
        tracks_num = len(queue)
        sum_duration = 0
        tracks_ids = []

        non_duplicates = []

        for track in queue:
            if track['duration'] == 0:
                if tracks_num == 1:
                    return await ctx.send(embed=create_warning_embed('I cannot save the queue to playlist!'), delete_after=10)

                tracks_num -= 1
                continue

            title = track['title'].replace("'", "''")
            if len(title) >= 200:
                title = title[:190] + '...'

            if title not in non_duplicates:
                sum_duration += track['duration']
                non_duplicates.append(title)

            tracks_ids.append(get_track_data(title)[0][0])

        if tracks_num == 0:
            return await ctx.send(embed=create_warning_embed('I cannot save the queue to playlist!'), delete_after=10)

        tracks_num = len(non_duplicates)

        add_playlist(guild_id, name, sum_duration, tracks_num)

        for track_id in tracks_ids:
            add_playlists_tracks(name, guild_id, track_id)

        await ctx.send(f'Queue saved to playlist {name}.', delete_after=10)

    @commands.guild_only()
    @commands.command(aliases=['get_playlist', 'get_p', 'load_playlist'])
    async def play_playlist(self, ctx: commands.Context, *, name):
        """Load playlist to queue"""
        guild_id = ctx.guild.id

        if check_if_playlist_name_taken(name, guild_id):
            await ctx.channel.purge(limit=1)

            id = get_playlist_data(name, guild_id)[0][0]
            tracks = get_tracks_in_playlist(id)

            for track in tracks:
                url = track[0]

                if guild_id in self.queues:
                    queue = self.queues[guild_id]['queue']
                    queue.extend(await self.run_blocking(self.get_track, url))
                    self.queues[guild_id]['loop'] = False
                else:
                    self.queues[guild_id] = {
                        'queue': await self.run_blocking(self.get_track, url), 'index': 0, 'loop': False}

            await ctx.send(f'Playlist **{name}** added to queue.', delete_after=10)

            voice = ctx.voice_client
            guild = ctx.guild.id
            try:
                channel = ctx.message.author.voice.channel
            except:
                return

            if voice and voice.is_connected():
                await voice.move_to(channel)
            else:
                voice = await channel.connect()

            if voice.is_playing() or voice.is_paused() and url:
                await ctx.reply('⬆️ Track added to queue.', delete_after=5)

            if not voice.is_playing():
                index = self.queues[guild]['index']
                track = self.queues[guild]['queue'][index]
                url = track['url']
                title = track['title']
                duration = track['duration']

                source = await self.run_blocking(self.get_source, url)

                embed = (discord.Embed(title='Track:', description=title, color=discord.Color.gold())
                         .add_field(name='Duration', value=Music.parse_duration(duration))
                         .add_field(name='URL', value=(url)))

                voice.play(discord.FFmpegPCMAudio(
                    source, **ffmpeg_options), after=lambda e: self.play_next(e, voice, ctx))

                await ctx.send(embed=embed, delete_after=30)

        else:
            await ctx.send(embed=create_warning_embed(f'Seems like playlist with that name doesnt exist!\n\nShow all saved playlists: `{BOT_PREFIX}show_playlists`?'))

    @commands.guild_only()
    @commands.command(aliases=['show_playlist'])
    async def display_playlist(self, ctx: commands.Context, *, name):
        """Show choosen playlist"""

        guild_id = ctx.guild.id

        if check_if_playlist_name_taken(name, guild_id):
            await ctx.channel.purge(limit=1)

            playlist_info = get_playlist_data(name, guild_id)[0]
            duration = playlist_info[1]
            duration = Music.parse_duration(duration)
            tracks_count = playlist_info[2]

            headers = ['#', 'Назва', 'Час']
            cntr = 1
            footer = None
            table = []
            max_queue_tracks = 10
            id = get_playlist_data(name, guild_id)[0][0]
            queue = get_tracks_data_in_playlist(id)

            for song in queue:
                if cntr > max_queue_tracks:
                    footer = 'The pagination will be done as soon as the developer will write it...'
                    break

                title = song[0]
                if len(title) > 17:
                    title = title[:17] + '...'

                table.append(
                    [cntr, title, self.parse_duration(song[1])])
                cntr += 1

            output_table = tabulate.tabulate(
                table, headers=headers, tablefmt='fancy_grid')

            embed = discord.Embed(
                colour=discord.Color.blurple(),
                title=f'📜  Playlist **{name}**:',
                description=f'```{output_table}```\n\Tracks: {tracks_count} ({duration})'
            )

            if footer != None:
                embed.set_footer(text=footer)

            await ctx.send(embed=embed)
        else:
            await ctx.reply(embed=create_warning_embed(f'Seems like playlist with that name doesnt exist!\n\nShow all saved playlists: `{BOT_PREFIX}show_playlists`?'))

    @commands.guild_only()
    @commands.command(aliases=['show_playlists'])
    async def display_playlists(self, ctx: commands.Context):
        """Show all saved playlists"""
        guild_id = ctx.guild.id

        await ctx.channel.purge(limit=1)

        playlists = get_all_playlists(guild_id)

        playlists_count = len(playlists)

        embed = embed = discord.Embed(
            colour=discord.Color.blurple(),
            title=f'📜  Playlists in **{ctx.guild.name}**:',
            description=f'There are {playlists_count} playlists:'
        )

        for playlist in playlists:
            name = playlist[0]
            duration = Music.parse_duration(playlist[1])
            tracks_count = playlist[2]
            embed.add_field(
                name=name, value=f'Tracks: {tracks_count} - ({duration})', inline=False)

        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(aliases=['del_playlist', 'd_playlist'])
    async def delete_playlist(self, ctx: commands.Context, *, name):
        """Delete choosen playlist"""

        guild_id = ctx.guild.id

        if check_if_playlist_name_taken(name, guild_id):
            await ctx.channel.purge(limit=1)

            remove_playlist(name, guild_id)

            await ctx.send(f'Playlist **{name}** done, satisfied? You will never see it again.', delete_after=10)
        else:
            await ctx.reply(embed=create_warning_embed(f'Seems like playlist with that name doesnt exist!\n\nShow all saved playlists: `{BOT_PREFIX}show_playlists`?'))

    @play.before_invoke
    @player.before_invoke
    @pause_command.before_invoke
    @next.before_invoke
    @previous.before_invoke
    @queue.before_invoke
    @delete_queue.before_invoke
    @delete_track.before_invoke
    @jump_to_track.before_invoke
    @queue_to_playlist.before_invoke
    @play_playlist.before_invoke
    @loop_command.before_invoke
    @shuffle_command.before_invoke
    async def ensure_voice_member_used_command(self, ctx: commands.Context):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await self._join(ctx)
            else:
                raise NotConnected
        else:
            if ctx.author.voice:
                if ctx.author.voice.channel != ctx.voice_client.channel:
                    raise IncorrectVoiceChannel
            else:
                raise NotConnected

    @play.error
    async def play_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.message.reply(embed=create_warning_embed(f"No URL Provided!\n\nUsage example: '{BOT_PREFIX}play https://www.youtube.com/watch?v=xr-uFewQzfY'"))

    @delete_track.error
    async def delete_track_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.message.reply(embed=create_warning_embed(f"No track number specified!\n\nUsage example: '{BOT_PREFIX}d 1'"))

    @queue_to_playlist.error
    async def queue_to_playlist_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.message.reply(embed=create_warning_embed(f"No playlist name provided!\n\nUsage example: '{BOT_PREFIX}queue_to_playlist awesome_name'"))

    @play_playlist.error
    async def play_playlist_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.message.reply(embed=create_warning_embed(f"No playlist name provided!\n\nUsage example: '{BOT_PREFIX}play_playlist awesome_name'"))

    @display_playlist.error
    async def display_playlist_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.message.reply(embed=create_warning_embed(f"No playlist name provided!\n\nUsage example: '{BOT_PREFIX}display_playlist awesome_name'"))

    @delete_playlist.error
    async def delete_playlist_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.message.reply(embed=create_warning_embed(f"No playlist name provided!\n\nUsage example: '{BOT_PREFIX}delete_playlist awesome_name'"))

    @tasks.loop(minutes=5.0)
    async def check_if_bot_alone(self):
        voices = self.bot.voice_clients
        for voice in voices:
            if voice.is_connected():
                if not voice.is_playing() and not voice.is_paused():
                    voice.stop()
                    await voice.disconnect()


def setup(bot):
    bot.add_cog(Music(bot))
