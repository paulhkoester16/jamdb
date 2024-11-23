/***** Drop Tables *******************************/

DROP TABLE IF EXISTS [_schema_tables];

DROP TABLE IF EXISTS [_schema_columns];

DROP TABLE IF EXISTS [Chart];

DROP TABLE IF EXISTS [Composer];

DROP TABLE IF EXISTS [ContactType];

DROP TABLE IF EXISTS [Contact];

DROP TABLE IF EXISTS [EventGen];

DROP TABLE IF EXISTS [EventOcc];

DROP TABLE IF EXISTS [Genre];

DROP TABLE IF EXISTS [Instrument];

DROP TABLE IF EXISTS [Key];

DROP TABLE IF EXISTS [LinkSource];

DROP TABLE IF EXISTS [Mode];

DROP TABLE IF EXISTS [Person];

DROP TABLE IF EXISTS [PersonPicture];

DROP TABLE IF EXISTS [PersonInstrument];

DROP TABLE IF EXISTS [PerformanceVideo];

DROP TABLE IF EXISTS [RefRec];

DROP TABLE IF EXISTS [Setlist];

DROP TABLE IF EXISTS [SetlistSong];

DROP TABLE IF EXISTS [Song];

DROP TABLE IF EXISTS [SongLearn];

DROP TABLE IF EXISTS [SongPerform];

DROP TABLE IF EXISTS [SongPerformer];

DROP TABLE IF EXISTS [Subgenre];

DROP TABLE IF EXISTS [Venue];

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

CREATE TABLE LinkSource (
    id	TEXT	NOT NULL,
	rank	INT	NOT NULL	UNIQUE,
	PRIMARY KEY	(id)
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
	PRIMARY KEY	(id)
);

CREATE TABLE PersonPicture (
	id	TEXT	NOT NULL,
	person_id	TEXT	NOT NULL,
	source_id	TEXT	NOT NULL,
	link	TEXT	NOT NULL	UNIQUE,
	PRIMARY KEY	(id),
	FOREIGN KEY (person_id) REFERENCES Person (id),
	FOREIGN KEY (source_id) REFERENCES LinkSource (id)
);

CREATE TABLE ContactType (
	id	TEXT	NOT NULL,
	display_name	TEXT	NOT NULL	UNIQUE,
	rank	INTEGER	NOT NULL	UNIQUE,
    private	BOOLEAN	NOT NULL,
	PRIMARY KEY	(id)
);

CREATE TABLE Contact (
	id	TEXT	NOT NULL,
	person_id	TEXT	NOT NULL,
	contact_type_id	TEXT	NOT NULL,
	contact_info	TEXT	DEFAULT "",
	link	TEXT	DEFAULT "",
    private	BOOLEAN,
	PRIMARY KEY	(id),
	FOREIGN KEY (person_id) REFERENCES Person (id)
	FOREIGN KEY (contact_type_id) REFERENCES ContactType (id)    
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
	mode	TEXT	NOT NULL	UNIQUE,
	PRIMARY KEY	(id)
);

CREATE TABLE EventGen (
	id	TEXT	NOT NULL,
	name	TEXT	NOT NULL	UNIQUE,
	genre_id	TEXT	NOT NULL,
	venue_id	TEXT	NOT NULL,
	date	TEXT	NOT NULL,
	time	TEXT	NOT NULL,
	host_id	TEXT	DEFAULT "unknown_host",
	PRIMARY KEY	(id),
	FOREIGN KEY (venue_id) REFERENCES Venue (id),
	FOREIGN KEY (host_id) REFERENCES Person (id),
	FOREIGN KEY (genre_id) REFERENCES Genre (id)
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

CREATE TABLE Subgenre (
	id	TEXT	NOT NULL,
	subgenre	TEXT	NOT NULL	UNIQUE,
	genre_id	TEXT	NOT NULL,
	PRIMARY KEY	(id),
	FOREIGN KEY (genre_id) REFERENCES Genre (id)
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
	PRIMARY KEY	(id),
	FOREIGN KEY (subgenre_id) REFERENCES Subgenre (id),
	FOREIGN KEY (key_id) REFERENCES Key (id),
	FOREIGN KEY (composer_id) REFERENCES Composer (id)
);

CREATE TABLE SongLearn (
	id	TEXT	NOT NULL,
	song_id	TEXT	NOT NULL,
	instrument_id	TEXT	NOT NULL,
	date	TEXT	NOT NULL,
	key_id	TEXT,
	PRIMARY KEY	(id),
	FOREIGN KEY (song_id) REFERENCES Song (id),    
	FOREIGN KEY (key_id) REFERENCES Key (id)
);

CREATE TABLE RefRec (
	id	TEXT	NOT NULL,
	song_id	TEXT	NOT NULL,
	source_id	TEXT	NOT NULL,
	link	TEXT	NOT NULL	UNIQUE,
	display_name	TEXT	DEFAULT "",
	PRIMARY KEY	(id),
	FOREIGN KEY (song_id) REFERENCES Song (id),
	FOREIGN KEY (source_id) REFERENCES LinkSource (id)
);

CREATE TABLE Chart (
	id	TEXT	NOT NULL,
	song_id	TEXT	NOT NULL,
	source_id	TEXT	NOT NULL,
	link	TEXT	NOT NULL	UNIQUE,
	display_name	TEXT	DEFAULT "",    
	PRIMARY KEY	(id),
	FOREIGN KEY (song_id) REFERENCES Song (id),
	FOREIGN KEY (source_id) REFERENCES LinkSource (id)
);

CREATE TABLE SetlistSong (
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
	key_id	TEXT,
	PRIMARY KEY	(id),
	FOREIGN KEY (event_occ_id) REFERENCES EventOcc (id),
	FOREIGN KEY (song_id) REFERENCES Song (id),
	FOREIGN KEY (key_id) REFERENCES Key (id)
);

CREATE TABLE SongPerformer (
	id	TEXT	NOT NULL,
	song_perform_id	TEXT	NOT NULL,
	person_instrument_id	TEXT	NOT NULL,
    PRIMARY KEY (id),
	FOREIGN KEY (song_perform_id) REFERENCES SongPerform (id),
	FOREIGN KEY (person_instrument_id) REFERENCES PersonInstrument (id),
    UNIQUE(song_perform_id, person_instrument_id)
);

CREATE TABLE PerformanceVideo (
	id	TEXT	NOT NULL,
	song_perform_id	TEXT	NOT NULL,
	source_id	TEXT	NOT NULL,
	link	TEXT	NOT NULL	UNIQUE,
	display_name	TEXT	DEFAULT "",
    PRIMARY KEY (id),
	FOREIGN KEY (song_perform_id) REFERENCES SongPerform (id),
	FOREIGN KEY (source_id) REFERENCES LinkSource (id)
);


/*** Populate Schema Tables *******************/

INSERT INTO _schema_tables (table_name, description) VALUES
	("Chart", "Links to charts for songs."),    
	("Composer", "Composer information"),
	("Contact", "Contact information for a person, e.g., social media links."),
	("ContactType", "Contact information type, e.g., facebook vs linktree etc."),
	("EventGen", "Recurring events, including event's venue and the recurrence pattern.  Due to the data design, even one-off gigs are defined in EventGen."),
	("EventOcc", "Specific events, including the event's specific date and EventGen that it derives from."),
	("Genre", "Coarse genre information. Genres are at the level of 'Jazz' vs 'Blues', etc.  See also `SubGrenre`."),
	("Instrument", "Instrument information."),
	("Key", "Key signature / mode information."),
    ("LinkSource", "Information about the type of link"),
	("Mode", "Information about mode."),
	("PerformanceVideo", "Video link for a performed song."),
	("Person", "Public Information about a person."),
	("PersonPicture", "Links to person pictures."),
	("PersonInstrument", "Which instruments are played by a given person."),
	("RefRec", "Links to reference recordings of songs."),
	("Setlist", "Setlist information."),
	("SetlistSong", "Information about songs on a Setlist, including song name, key, and which instrument I will play."),
	("Song", "Information about a song, including song name, key, etc."),
	("SongLearn", "Information about songs that I've learned, including instrument, key, and when I learned it."),
	("SongPerform", "Information about a particular performance of a song."),
	("SongPerformer", "Information about performers on a given performed song."),
	("Subgenre", "Granular genre information. Subgenres can be at the level of 'Bop' vs 'Swing', etc.  See also `Grenre`."),
	("Venue", "Information about a physical venue, including venue name, address, etc.");


INSERT INTO _schema_columns (table_name, column, description) VALUES
	("Chart", "id", "Unique ID of the Chart."),
	("Chart", "song_id", "ID of the Chart's song"),
	("Chart", "source_id", "Unique ID of the chart's source, e.g., web link or ireal, etc."),
	("Chart", "link", "Link, etc., url or uri"),
	("Chart", "display_name", "Human readable name of link"),
	("Composer", "id", "Unique ID for Composer."),
	("Composer", "composer", "Composer name."),
	("Contact", "id", "Unique ID for Contact info."),
	("Contact", "person_id", "ID for the Contact's person."),
	("Contact", "contact_type_id", "Unique id for the kind of contact, e.g., facebook vs youtube etc."),
	("Contact", "contact_info", "Free form text contact info, like phone numbers, etc."),
	("Contact", "link", "Hyperlink, e.g., for Facebook etc."),
	("Contact", "private", "Whether the contact info should remain private"),
    ("ContactType", "id", "ID for the contact type"),
    ("ContactType", "display_name", "Human readable name of the contact type"),
    ("ContactType", "rank", "For ordering links by source. e.g., linktree before facebook, etc."),
	("ContactType", "private", "Whether the contact info should remain private"),    
	("EventGen", "id", "Unique ID for EventGen."),
	("EventGen", "name", "Name of EventGen, e.g., 'Jazz Madcats'"),
	("EventGen", "genre_id", "ID of the genre, to distinguish between 'Blues' jam vs 'Open Mic', etc."),
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
    ("LinkSource", "id", "Unique ID of the link type"),
    ("LinkSource", "rank", "For ordering links by source. e.g., web links before images, etc."),
	("Mode", "id", "Unique ID of the mode."),
	("Mode", "mode", "Descriptive name of the mode."),
	("PerformanceVideo", "id", "Unique ID of the PerformanceVideo"),
	("PerformanceVideo", "song_perform_id", "ID of the SongPerform"),
	("PerformanceVideo", "source_id", "Unique ID of the recording's source, e.g., youtube or spotify, etc."),
	("PerformanceVideo", "link", "Link, etc., url or uri"),
	("PerformanceVideo", "display_name", "Human readable name of link"),    
	("Person", "id", "Unique ID for Person."),
	("Person", "public_name", "Person's publicly used name, typically their first name and last initial."),
	("Person", "full_name", "Person's full name."),
	("PersonInstrument", "id", "Unique ID for PersonInstrument."),
	("PersonInstrument", "person_id", "ID of the Person."),
	("PersonInstrument", "instrument_id", "ID of the Instrument."),
	("PersonPicture", "id", "Unique ID for PersonPicture."),
	("PersonPicture", "person_id", "ID for picture's person."),
	("PersonPicture", "source_id", "Unique ID of photo's source, e.g, jpg vs png etc."),
	("PersonPicture", "link", "Link to picture."),
	("RefRec", "id", "Unique ID of the RefRec."),
	("RefRec", "song_id", "ID of the RefRec's song"),
	("RefRec", "source_id", "Unique ID of the recording's source type, e.g., YouTube or Spotify, etc."),
	("RefRec", "link", "Link, etc., url or uri"),
	("RefRec", "display_name", "Human readable name of link"),
	("Setlist", "id", "Unique ID for SetList."),
	("Setlist", "setlist", "Name of the SetList."),
	("Setlist", "description", "Description of the SetList."),
	("SetlistSong", "id", "Unique ID for the SetlistSong."),
	("SetlistSong", "setlist_id", "ID of the SetList that this SetlistSong belongs to."),
	("SetlistSong", "song_id", "ID of the Song."),
	("SetlistSong", "instrument_id", "ID of the instrument I will play for this SetlistSong."),
	("SetlistSong", "key_id", "ID of the SetlistSong's key.  This is provided to override if a particular SetlistSong requires playing in a key other than the Song’s default key."),
	("Song", "id", "Unique ID of the Song."),
	("Song", "song", "Name of the Song."),
	("Song", "subgenre_id", "ID of the Song's Subgenre."),
	("Song", "instrumental", "Boolean as to if the song is an instrumental or not."),
	("Song", "key_id", "ID of the Song's Key."),
	("Song", "composer_id", "ID of the Song's Composer."),
	("SongLearn", "id", "Unique ID of the SongLearn."),
	("SongLearn", "song_id", "ID of the Song."),
	("SongLearn", "instrument_id", "ID of the Instrument I learned the Song on."),
	("SongLearn", "date", "Date when I learned the Song."),
	("SongLearn", "key_id", "ID of the SetlistSong's key.  This is provided to override if a particular SongLearn's key is different than the Song's default key."),
	("SongPerform", "id", "Unique ID of a SongPerform."),
	("SongPerform", "event_occ_id", "ID of the performed song's EventOcc."),
	("SongPerform", "song_id", "ID of the performed song's Song."),
	("SongPerform", "key_id", "ID of the performed song's key.  This is provided to override if a particular performance is in different than the Song's default key."),
	("SongPerformer", "id", "Unique ID of the SongPerformer."),
	("SongPerformer", "song_perform_id", "ID of the SongPerformed by the SongPerformer."),
	("SongPerformer", "person_instrument_id", "ID of the PersonInstrument of the SongPerformer."),
	("Subgenre", "id", "Unique ID of the Subgenre."),
	("Subgenre", "subgenre", "Name of the Subgenre.  Subgenre provides more granularity than Genre.  E.g., 'Jazz' as a Genre, 'Bop', 'Swing' etc as SubGenres of 'Jazz'."),
	("Subgenre", "genre_id", "ID of the Genre."),
	("Venue", "id", "Unique ID of the Venue."),
	("Venue", "venue", "Name of the Venue, e.g, “Madcats”."),
	("Venue", "address", "Street address of the Venue."),
	("Venue", "city", "City of the Venue."),
	("Venue", "zip", "Zipcode of the Venue."),
	("Venue", "state", "State of the Venue."),
	("Venue", "web", "Link(s) to Venue's website.");
