from psycopg2 import connect, sql
import os

# * Constants for DB connection
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_PASS = os.environ.get('DB_PASS')
DB_USER = os.environ.get('DB_USER')
DB_PORT = os.environ.get('DB_PORT')


def db_executor(executable):
    """Simple tamplete for executing simple commands with DB.

    Args:
        executable (str): SQL query to execute.
    """

    try:
        connection = connect(user=DB_USER,
                             password=DB_PASS,
                             host=DB_HOST,
                             port=DB_PORT,
                             database=DB_NAME)
        cursor = connection.cursor()
        connection.autocommit = True

        cursor.execute(executable)
    finally:
        if connection:
            cursor.close()
            connection.close()


def db_executor_return(executable):
    """Simple tamplete for executing simple commands with DB, with return of smth.

    Args:
        executable (str): SQL query to execute.

    Returns:
        {different}: Returning of query.
    """

    try:
        connection = connect(user=DB_USER,
                             password=DB_PASS,
                             host=DB_HOST,
                             port=DB_PORT,
                             database=DB_NAME)
        cursor = connection.cursor()
        connection.autocommit = True

        cursor.execute(executable)

        output = cursor.fetchone()
        if output != None:
            output = output[0]
    finally:
        if connection:
            cursor.close()
            connection.close()

    return output


def db_executor_return_all(executable):
    """Simple tamplete for executing simple commands with DB, with return of all data.

    Args:
        executable (str): SQL query to execute.

    Returns:
        {different}: Returning of query.
    """

    try:
        connection = connect(user=DB_USER,
                             password=DB_PASS,
                             host=DB_HOST,
                             port=DB_PORT,
                             database=DB_NAME)
        cursor = connection.cursor()
        connection.autocommit = True

        cursor.execute(executable)

        output = cursor.fetchall()
    finally:
        if connection:
            cursor.close()
            connection.close()

    return output


def get_guild_data(guild_id):
    select = sql.SQL(
        f"SELECT guild_name, member_count, owner_id FROM guilds WHERE guild_id = '{guild_id}';"
    )

    return db_executor_return_all(select)


def add_guild_data(guild):
    if get_guild_data(guild.id) == []:
        insert = f"INSERT INTO guilds(guild_id, guild_name, member_count, owner_id) VALUES('{guild.id}', '{guild.name}', {guild.member_count}, '{guild.owner_id}');"

        db_executor(insert)


def get_all_guilds():
    select = sql.SQL(f"SELECT guild_name, member_count, owner_id, guild_id FROM guilds;")

    return db_executor_return_all(select)


def get_member_data(member_id):
    select = sql.SQL(
        f"SELECT member_id, member_guild_id, member_name, member_nick, warning_count FROM members WHERE member_id = '{member_id}';"
    )

    return db_executor_return_all(select)


def get_member_warnings_count(member_id):
    select = sql.SQL(
        f"SELECT warning_count FROM members WHERE member_id='{member_id}';")

    return db_executor_return(select)


def add_member_data(member):
    if get_member_data(member.id) == []:
        name = member.name.replace("'", "''")
        nick = member.nick
        if nick != None:
            nick = nick.replace("'", "''")

        insert = sql.SQL(
            f"INSERT INTO members(member_id, member_guild_id,  member_name, member_nick) VALUES('{member.id}', '{member.guild.id}', E'{name}', E'{nick}');")

        db_executor(insert)


def update_member_data(member, warning_count):
    # warning_count = get_members_warnings_count(member.id)+1
    name = member.name.replace("'", "''")
    nick = member.nick
    if nick != None:
        nick = nick.replace("'", "''")

    update = sql.SQL(
        f"UPDATE members SET member_guild_id='{member.guild.id}', member_name=E'{name}', member_nick=E'{nick}', warning_count={warning_count} WHERE member_id='{member.id}';")

    db_executor(update)


def add_offend(member, chat_id, msg):
    insert = sql.SQL(
        f"INSERT INTO offenders(offender_id, offender_guild_id, offender_chat_id, offender_message) VALUES('{member.id}', '{member.guild.id}', '{chat_id}', '{msg}');"
    )

    db_executor(insert)

    warnings_count = get_member_warnings_count(member.id) + 1

    update_member_data(member, warnings_count)


def remove_offends(member_id, channel_id, guild_id):
    delete = sql.SQL(
        f"DELETE FROM offenders WHERE offender_chat_id='{channel_id}' AND offender_id='{member_id}' AND offender_guild_id='{guild_id}';"
    )

    db_executor(delete)

    update = sql.SQL(
        f"UPDATE members SET warning_count=0 WHERE member_id='{member_id}' AND member_guild_id='{guild_id}';")

    db_executor(update)


def remove_all_offends(member_id, guild_id):
    delete = sql.SQL(
        f"DELETE FROM offenders WHERE offender_id='{member_id}' AND offender_guild_id='{guild_id}';"
    )

    db_executor(delete)

    update = sql.SQL(
        f"UPDATE members SET warning_count=0 WHERE member_id='{member_id}' AND member_guild_id='{guild_id}';")

    db_executor(update)



def get_track_data(title):
    select = sql.SQL(
        f"SELECT track_id, title, track_url, duration FROM tracks WHERE title=E'{title}';"
    )

    return db_executor_return_all(select)


def get_track_data_by_url(url):
    select = sql.SQL(
        f"SELECT title, duration FROM tracks WHERE track_url=E'{url}';"
    )

    return db_executor_return_all(select)


def check_if_track_exists_by_url(url):
    select = sql.SQL(
        f"SELECT EXISTS(SELECT 1 FROM tracks WHERE track_url='{url}');"
    )

    return db_executor_return(select)


def add_track(title, track_url, duration):
    if len(title) >= 200:
        title = title[:190] + '...'
    title = title.replace("'", "''")

    if get_track_data(title) == []:
        insert = sql.SQL(
            f"INSERT INTO tracks(title, track_url, duration) VALUES(E'{title}', E'{track_url}', {duration});"
        )

        db_executor(insert)


def get_playlist_data(name, guild_id):
    select = sql.SQL(
        f"SELECT playlist_id, duration, tracks_count FROM playlists WHERE playlist_name=E'{name}' AND playlist_guild_id='{guild_id}';"
    )

    return db_executor_return_all(select)


def get_all_playlists(guild_id):
    select = sql.SQL(
        f"SELECT playlist_name, duration, tracks_count FROM playlists WHERE playlist_guild_id='{guild_id}';"
    )

    return db_executor_return_all(select)


def check_if_playlist_name_taken(name, guild_id):
    select = sql.SQL(
        f"SELECT EXISTS(SELECT 1 FROM playlists WHERE playlist_name='{name}' AND playlist_guild_id='{guild_id}');"
    )

    return db_executor_return(select)
    


def add_playlist(guild_id, name, duration, num):
    insert = sql.SQL(
        f"INSERT INTO playlists (playlist_guild_id, playlist_name, duration, tracks_count) VALUES('{guild_id}', E'{name}', {duration}, {num});"
    )

    db_executor(insert)


def remove_playlist(name, guild_id):
    delete = sql.SQL(
        f"DELETE FROM playlists WHERE playlist_name='{name}' AND playlist_guild_id='{guild_id}';"
    )

    db_executor(delete)


def add_playlists_tracks(name, guild_id, track_id):
    playlist_id = get_playlist_data(name, guild_id)[0][0]
    insert = sql.SQL(
        f"INSERT INTO playlists_tracks(playlist_id, track_id) VALUES({playlist_id}, {track_id}) ON CONFLICT DO NOTHING;")

    db_executor(insert)


def get_tracks_in_playlist(id):
    select = sql.SQL(
        f"SELECT track_url, duration FROM tracks JOIN playlists_tracks ON tracks.track_id=playlists_tracks.track_id WHERE playlist_id='{id}';"
    )

    return db_executor_return_all(select)


def get_tracks_data_in_playlist(id):
    select = sql.SQL(
        f"SELECT title, duration FROM tracks JOIN playlists_tracks ON tracks.track_id=playlists_tracks.track_id WHERE playlist_id='{id}';"
    )

    return db_executor_return_all(select)
