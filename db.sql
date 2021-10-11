DROP TABLE IF EXISTS guilds;
CREATE TABLE guilds (
	guild_id VARCHAR(200) NOT NULL PRIMARY KEY,
	guild_name VARCHAR(200),
	member_count INT,
	owner_id VARCHAR(200)
);

DROP TABLE IF EXISTS members;
CREATE TABLE members (
	member_id VARCHAR(200) NOT NULL PRIMARY KEY,
	member_guild_id VARCHAR(200) NOT NULL REFERENCES guilds(guild_id),
	member_name VARCHAR(200) NOT NULL,
	member_nick VARCHAR(200),
	warning_count INT NOT NULL DEFAULT 0
);

DROP TABLE IF EXISTS offenders;
CREATE TABLE offenders (
	offend_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	offender_id VARCHAR(200) NOT NULL REFERENCES members(member_id),
	offender_guild_id VARCHAR(200) NOT NULL REFERENCES guilds(guild_id),
	offender_chat_id VARCHAR(200) NOT NULL,
	offender_message TEXT
);

DROP TABLE IF EXISTS playlists;
CREATE TABLE playlists (
	playlist_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	playlist_guild_id VARCHAR(200) NOT NULL REFERENCES guilds(guild_id),
	playlist_name VARCHAR(200) NOT NULL,
	duration INT NOT NULL,
	tracks_count INT NOT NULL
);

DROP TABLE IF EXISTS tracks;
CREATE TABLE tracks (
	track_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	title VARCHAR(200) NOT NULL,
	track_url TEXT NOT NULL,
	duration INT NOT NULL
);

DROP TABLE IF EXISTS plyalists_tracks;
CREATE TABLE playlists_tracks (
	playlist_id INT REFERENCES playlists(playlist_id) ON UPDATE CASCADE ON DELETE CASCADE,
	track_id INT REFERENCES tracks(track_id) ON UPDATE CASCADE,
	CONSTRAINT plyalist_track_pkey PRIMARY KEY (playlist_id, track_id)
);
