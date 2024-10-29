/***** Drop Tables *******************************/

DROP TABLE IF EXISTS [_schema_tables];

DROP TABLE IF EXISTS [_schema_columns];

DROP TABLE IF EXISTS [Composer];

DROP TABLE IF EXISTS [EventGen];

DROP TABLE IF EXISTS [EventOcc];

DROP TABLE IF EXISTS [Genre];

DROP TABLE IF EXISTS [Instrument];

DROP TABLE IF EXISTS [Key];

DROP TABLE IF EXISTS [Person];

DROP TABLE IF EXISTS [PersonInstrument];

DROP TABLE IF EXISTS [Setlist];

DROP TABLE IF EXISTS [SetlistSongs];

DROP TABLE IF EXISTS [Song];

DROP TABLE IF EXISTS [SongLearn];

DROP TABLE IF EXISTS [SongPerform];

DROP TABLE IF EXISTS [SubGenre];

DROP TABLE IF EXISTS [Venue];

DROP TABLE IF EXISTS [Mode];

/****  Create Tables ******************************/

CREATE TABLE _schema_tables (
	table_name	TEXT	NOT NULL,
	description	TEXT	NOT NULL,
	PRIMARY KEY	(table_name)
);

CREATE TABLE _schema_columns (
	table_name	TEXT	NOT NULL,
	column	TEXT	NOT NULL,
	description	TEXT	NOT NULL,
	PRIMARY KEY	(table_name, column),
	FOREIGN KEY (table_name) REFERENCES _schema_tables (table_name)
);

CREATE TABLE Composer (
	id	TEXT	NOT NULL,
	composer	TEXT	NOT NULL	UNIQUE,
	PRIMARY KEY	(id)
);

CREATE TABLE Venue (
	id	TEXT	NOT NULL,
	venue	TEXT	NOT NULL	UNIQUE,
	address	TEXT	NOT NULL,
	city	TEXT	NOT NULL,
	zip	TEXT	NOT NULL,
	state	TEXT	NOT NULL,
	web	TEXT	NOT NULL,
	PRIMARY KEY	(id)
);

CREATE TABLE Person (
	id	TEXT	NOT NULL,
	public_name	TEXT	NOT NULL	UNIQUE,
	full_name	TEXT	NOT NULL	UNIQUE,
    facebook	TEXT	DEFAULT "",
    instagram	TEXT	DEFAULT "",
    youtube	TEXT	DEFAULT "",
    other_contact	TEXT	DEFAULT "",
	PRIMARY KEY	(id)
);

CREATE TABLE Genre (
	id	TEXT	NOT NULL,
	genre	TEXT	NOT NULL	UNIQUE,
	PRIMARY KEY	(id)
);

CREATE TABLE Instrument (
	id	TEXT	NOT NULL,
	instrument	TEXT	NOT NULL	UNIQUE,
	PRIMARY KEY	(id)
);

CREATE TABLE Mode (
	id	TEXT	NOT NULL,
	mode_name	TEXT	NOT NULL	UNIQUE,
	PRIMARY KEY	(id)
);

CREATE TABLE EventGen (
	id	TEXT	NOT NULL,
	name	TEXT	NOT NULL	UNIQUE,
	event_genre_id	TEXT	NOT NULL,
	venue_id	TEXT	NOT NULL,
	date	TEXT	NOT NULL,
	time	TEXT	NOT NULL,
	host_id	TEXT	DEFAULT "unknown_host",
	PRIMARY KEY	(id),
	FOREIGN KEY (venue_id) REFERENCES Venue (id),
	FOREIGN KEY (host_id) REFERENCES Person (id),
	FOREIGN KEY (event_genre_id) REFERENCES Genre (id)
);

CREATE TABLE PersonInstrument (
	id	TEXT	NOT NULL,
	person_id	TEXT	NOT NULL,
	instrument_id	TEXT	NOT NULL,
	PRIMARY KEY	(id),
	FOREIGN KEY (person_id) REFERENCES Person (id),
	FOREIGN KEY (instrument_id) REFERENCES Instrument (id)
    UNIQUE(person_id, instrument_id)
);

CREATE TABLE Setlist (
	id	TEXT	NOT NULL,
	setlist	TEXT	NOT NULL	UNIQUE,
	description	TEXT	DEFAULT "",
	PRIMARY KEY	(id)
);

CREATE TABLE Key (
	id	TEXT	NOT NULL,
	root	TEXT	NOT NULL,
	mode_id	TEXT	NOT NULL,
	PRIMARY KEY	(id),
	FOREIGN KEY (mode_id) REFERENCES Mode (id)
    UNIQUE(root, mode_id)
);

CREATE TABLE SubGenre (
	id	TEXT	NOT NULL,
	subgenre	TEXT	NOT NULL	UNIQUE,
	genre_id	TEXT	NOT NULL,
	PRIMARY KEY	(id),
	FOREIGN KEY (genre_id) REFERENCES Genre (id)
);

CREATE TABLE SongLearn (
	id	TEXT	NOT NULL,
	song_id	TEXT	NOT NULL,
	instrument_id	TEXT	NOT NULL,
	date	TEXT	NOT NULL,
	key_id	TEXT,
	PRIMARY KEY	(id),
	FOREIGN KEY (key_id) REFERENCES Key (id)
);

CREATE TABLE EventOcc (
	id	TEXT	NOT NULL,
	name	TEXT	NOT NULL	UNIQUE,
	event_gen_id	TEXT	NOT NULL,
	date	TEXT	NOT NULL,
	PRIMARY KEY	(id),
	FOREIGN KEY (event_gen_id) REFERENCES EventGen (id)
);

CREATE TABLE Song (
	id	TEXT	NOT NULL,
	song	TEXT	NOT NULL	UNIQUE,
	subgenre_id	TEXT,
	instrumental	TEXT,
	key_id	TEXT,
	composer_id	TEXT,
	reference_recordings	TEXT	DEFAULT "",
	charts	TEXT	DEFAULT "",
	PRIMARY KEY	(id),
	FOREIGN KEY (subgenre_id) REFERENCES SubGenre (id),
	FOREIGN KEY (key_id) REFERENCES Key (id),
	FOREIGN KEY (composer_id) REFERENCES Composer (id)
);

CREATE TABLE SetlistSongs (
	id	TEXT	NOT NULL,
	setlist_id	TEXT	NOT NULL,
	song_id	TEXT	NOT NULL,
	instrument_id	TEXT	NOT NULL,
	key_id	TEXT,
	PRIMARY KEY	(id),
	FOREIGN KEY (setlist_id) REFERENCES Setlist (id),
	FOREIGN KEY (instrument_id) REFERENCES Instrument (id),
	FOREIGN KEY (song_id) REFERENCES Song (id),
	FOREIGN KEY (key_id) REFERENCES Key (id)
);

CREATE TABLE SongPerform (
	id	TEXT	NOT NULL,
	event_occ_id	TEXT	NOT NULL,
	song_id	TEXT	NOT NULL,
	instrument_id	TEXT,
	key_id	TEXT,
	video	TEXT	DEFAULT "",
	other_player_01	TEXT,
	other_player_02	TEXT,
	other_player_03	TEXT,
	other_player_04	TEXT,
	other_player_05	TEXT,
	other_player_06	TEXT,
	other_player_07	TEXT,
	other_player_08	TEXT,
	other_player_09	TEXT,
	other_player_10	TEXT,
	other_player_11	TEXT,
	other_player_12	TEXT,
	other_player_13	TEXT,
	other_player_14	TEXT,
	other_player_15	TEXT,
	other_player_16	TEXT,
	PRIMARY KEY	(id),
	FOREIGN KEY (event_occ_id) REFERENCES EventOcc (id),
	FOREIGN KEY (other_player_01) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_02) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_03) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_04) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_05) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_06) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_07) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_08) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_09) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_10) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_11) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_12) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_13) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_14) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_15) REFERENCES PersonInstrument (id),
	FOREIGN KEY (other_player_16) REFERENCES PersonInstrument (id),
	FOREIGN KEY (instrument_id) REFERENCES Instrument (id),
	FOREIGN KEY (song_id) REFERENCES Song (id),
	FOREIGN KEY (key_id) REFERENCES Key (id)
);


/***** Create Foreign Keys Constraints **************************/

CREATE INDEX IFK__schema_columnstable_name ON _schema_tables (table_name);

CREATE INDEX IFK_EventGenvenue_id ON Venue (id);

CREATE INDEX IFK_EventGenhost_id ON Person (id);

CREATE INDEX IFK_EventGenevent_genre_id ON Genre (id);

CREATE INDEX IFK_EventOccevent_gen_id ON EventGen (id);

CREATE INDEX IFK_Keymode_id ON Mode (id);

CREATE INDEX IFK_PersonInstrumentperson_id ON Person (id);

CREATE INDEX IFK_PersonInstrumentinstrument_id ON Instrument (id);

CREATE INDEX IFK_SetlistSongssetlist_id ON Setlist (id);

CREATE INDEX IFK_SetlistSongsinstrument_id ON Instrument (id);

CREATE INDEX IFK_SetlistSongssong_id ON Song (id);

CREATE INDEX IFK_SetlistSongskey_id ON Key (id);

CREATE INDEX IFK_Songsubgenre_id ON SubGenre (id);

CREATE INDEX IFK_Songkey_id ON Key (id);

CREATE INDEX IFK_Songcomposer_id ON Composer (id);

CREATE INDEX IFK_SongLearnkey_id ON Key (id);

CREATE INDEX IFK_SongPerformevent_occ_id ON EventOcc (id);

CREATE INDEX IFK_SongPerformother_player_01 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_02 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_03 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_04 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_05 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_06 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_07 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_08 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_09 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_10 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_11 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_12 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_13 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_14 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_15 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerformother_player_16 ON PersonInstrument (id);

CREATE INDEX IFK_SongPerforminstrument_id ON Instrument (id);

CREATE INDEX IFK_SongPerformsong_id ON Song (id);

CREATE INDEX IFK_SongPerformkey_id ON Key (id);

CREATE INDEX IFK_SubGenregenre_id ON Genre (id);

/*** Populate Schema Tables *******************/

INSERT INTO _schema_tables (table_name, description) VALUES
	("Composer", "Composer information"),
	("EventGen", "Recurring events, including event's venue and the recurrence pattern.  Due to the data design, even one-off gigs are defined in EventGen."),
	("EventOcc", "Specific events, including the event's specific date and EventGen that it derives from."),
	("Genre", "Coarse genre information. Genres are at the level of 'Jazz' vs 'Blues', etc.  See also `SubGrenre`."),
	("Instrument", "Instrument information."),
	("Key", "Key signature / mode information."),
	("Person", "Public Information about a person."),
	("PersonInstrument", "Which instruments are played by a given person."),
	("Setlist", "Setlist information."),
	("SetlistSongs", "Information about songs on a Setlist, including song name, key, and which instrument I will play."),
	("Song", "Information about a song, including song name, key, etc."),
	("SongLearn", "Information about songs that I've learned, including instrument, key, and when I learned it."),
	("SongPerform", "Information about a particular performance of a song, including which instrument I played, which event I played at, and who else played."),
	("SubGenre", "Granular genre information. SubGenres can be at the level of 'Bop' vs 'Swing', etc.  See also `Grenre`."),
	("Venue", "Information about a physical venue, including venue name, address, etc."),
	("Mode", "Information about mode.");

INSERT INTO _schema_columns (table_name, column, description) VALUES
	("Composer", "id", "Unique ID for Composer."),
	("Composer", "composer", "Composer name."),
	("EventGen", "id", "Unique ID for EventGen."),
	("EventGen", "name", "Name of EventGen, e.g., 'Jazz Madcats'"),
	("EventGen", "event_genre_id", "ID of the genre, to distinguish between 'Blues' jam vs 'Open Mic', etc."),
	("EventGen", "venue_id", "ID of the event's venue."),
	("EventGen", "date", "Recurrence patter, eg. '3rd Thursday'"),
	("EventGen", "time", "Time of the event, eg., '4:00 pm - 7:00 pm'"),
	("EventGen", "host_id", "Person ID of the event's host."),
	("EventOcc", "id", "Unique ID for the EventOcc."),
	("EventOcc", "name", "Name of EventOcc, e.g., 'Jazz Madcat September 2024'"),
	("EventOcc", "event_gen_id", "ID of the recurring EventGen"),
	("EventOcc", "date", "Specific date of the EventOcc."),
	("Genre", "id", "Unique ID for Genre."),
	("Genre", "genre", "Name of Genre."),
	("Instrument", "id", "Unique ID for Instrument."),
	("Instrument", "instrument", "Name of Instrument."),
	("Key", "id", "Unique ID for key."),
	("Key", "root", "Root note of key, e.g, “Bb” or F#”, etc."),
	("Key", "mode_id", "ID of the mode."),
	("Person", "id", "Unique ID for Person."),
	("Person", "public_name", "Person's publicly used name, typically their first name and last initial."),
	("Person", "full_name", "Person's full name."),
	("Person", "facebook", "Person's Facebook link(s)."),
	("Person", "instagram", "Person's Instagram link(s)."),
	("Person", "youtube", "Person's Youtube link(s)."),
	("Person", "other_contact", "Other contact information for Person."),
	("PersonInstrument", "id", "Unique ID for PersonInstrument."),
	("PersonInstrument", "person_id", "ID of the Person."),
	("PersonInstrument", "instrument_id", "ID of the Instrument."),
	("Setlist", "id", "Unique ID for SetList."),
	("Setlist", "setlist", "Name of the SetList."),
	("Setlist", "description", "Description of the SetList."),
	("SetlistSongs", "id", "Unique ID for the SetlistSong."),
	("SetlistSongs", "setlist_id", "ID of the SetList that this SetlistSong belongs to."),
	("SetlistSongs", "song_id", "ID of the Song."),
	("SetlistSongs", "instrument_id", "ID of the instrument I will play for this SetlistSong."),
	("SetlistSongs", "key_id", "ID of the SetlistSong's key.  This is provided to override if a particular SetlistSong requires playing in a key other than the Song’s default key."),
	("Song", "id", "Unique ID of the Song."),
	("Song", "song", "Name of the Song."),
	("Song", "subgenre_id", "ID of the Song's Subgenre."),
	("Song", "instrumental", "Boolean as to if the song is an instrumental or not."),
	("Song", "key_id", "ID of the Song's Key."),
	("Song", "composer_id", "ID of the Song's Composer."),
	("Song", "reference_recordings", "Link(s) to reference recordings, e.g., YouTube links or Spotify URLs"),
	("Song", "charts", "Link(s) to reference charts."),
	("SongLearn", "id", "Unique ID of the SongLearn."),
	("SongLearn", "song_id", "ID of the Song."),
	("SongLearn", "instrument_id", "ID of the Instrument I learned the Song on."),
	("SongLearn", "date", "Date when I learned the Song."),
	("SongLearn", "key_id", "ID of the SetlistSong's key.  This is provided to override if a particular SongLearn's key is different than the Song's default key."),
	("SongPerform", "id", "Unique ID of a SongPerform."),
	("SongPerform", "event_occ_id", "ID of the performed song's EventOcc."),
	("SongPerform", "song_id", "ID of the performed song's Song."),
	("SongPerform", "instrument_id", "ID of which Instrument I played.  If NULL, then I did not play on this performance."),
	("SongPerform", "key_id", "ID of the performed song's key.  This is provided to override if a particular performance is in different than the Song's default key."),
	("SongPerform", "video", "Link(s) to recordings of the performance."),
	("SongPerform", "other_player_01", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_02", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_03", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_04", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_05", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_06", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_07", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_08", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_09", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_10", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_11", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_12", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_13", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_14", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_15", "ID of PersonInstrument for another player who played this song."),
	("SongPerform", "other_player_16", "ID of PersonInstrument for another player who played this song."),
	("SubGenre", "id", "Unique ID of the SubGenre."),
	("SubGenre", "subgenre", "Name of the SubGenre.  Subgenre provides more granularity than Genre.  E.g., 'Jazz' as a Genre, 'Bop', 'Swing' etc as SubGenres of 'Jazz'."),
	("SubGenre", "genre_id", "ID of the Genre."),
	("Venue", "id", "Unique ID of the Venue."),
	("Venue", "venue", "Name of the Venue, e.g, “Madcats”."),
	("Venue", "address", "Street address of the Venue."),
	("Venue", "city", "City of the Venue."),
	("Venue", "zip", "Zipcode of the Venue."),
	("Venue", "state", "State of the Venue."),
	("Venue", "web", "Link(s) to Venue's website."),
	("Mode", "id", "Unique ID of the mode."),
	("Mode", "mode_name", "Descriptive name of the mode.");
