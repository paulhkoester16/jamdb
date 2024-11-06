/***** Drop Tables *******************************/

DROP TABLE IF EXISTS [_schema_tables];

DROP TABLE IF EXISTS [_schema_columns];

DROP TABLE IF EXISTS [Charts];

DROP TABLE IF EXISTS [Composer];

DROP TABLE IF EXISTS [Contact];

DROP TABLE IF EXISTS [EventGen];

DROP TABLE IF EXISTS [EventOcc];

DROP TABLE IF EXISTS [Genre];

DROP TABLE IF EXISTS [Instrument];

DROP TABLE IF EXISTS [Key];

DROP TABLE IF EXISTS [Mode];

DROP TABLE IF EXISTS [Person];

DROP TABLE IF EXISTS [PersonInstrument];

DROP TABLE IF EXISTS [PerformanceVideo];

DROP TABLE IF EXISTS [RefRecs];

DROP TABLE IF EXISTS [Setlist];

DROP TABLE IF EXISTS [SetlistSongs];

DROP TABLE IF EXISTS [Song];

DROP TABLE IF EXISTS [SongLearn];

DROP TABLE IF EXISTS [SongPerform];

DROP TABLE IF EXISTS [SongPerformer];

DROP TABLE IF EXISTS [SubGenre];

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

CREATE TABLE Contact (
	id	TEXT	NOT NULL,
	person_id	TEXT	NOT NULL,
	contact_type	TEXT	NOT NULL,
	contact_info	TEXT	DEFAULT "",
	link	TEXT	DEFAULT "",
	PRIMARY KEY	(id),
	FOREIGN KEY (person_id) REFERENCES Person (id)
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
	FOREIGN KEY (song_id) REFERENCES Song (id),    
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
	PRIMARY KEY	(id),
	FOREIGN KEY (subgenre_id) REFERENCES SubGenre (id),
	FOREIGN KEY (key_id) REFERENCES Key (id),
	FOREIGN KEY (composer_id) REFERENCES Composer (id)
);

CREATE TABLE RefRecs (
	id	TEXT	NOT NULL,
	song_id	TEXT	NOT NULL,
	source	TEXT	NOT NULL,
	link	TEXT	NOT NULL	UNIQUE,
	PRIMARY KEY	(id),
	FOREIGN KEY (song_id) REFERENCES Song (id)
);

CREATE TABLE Charts (
	id	TEXT	NOT NULL,
	song_id	TEXT	NOT NULL,
	source	TEXT	NOT NULL,
	link	TEXT	NOT NULL	UNIQUE,
	PRIMARY KEY	(id),
	FOREIGN KEY (song_id) REFERENCES Song (id)
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
	source	TEXT	NOT NULL,
	link	TEXT	NOT NULL	UNIQUE,
    PRIMARY KEY (id),
	FOREIGN KEY (song_perform_id) REFERENCES SongPerform (id)
);

/***** Create Views ************************************************
As general philosopy, use TABLES for writing and storing data and
use VIEWS for reading data.

Some VIEWS appear pointless, just SELECT * from associated table.
But this gives flexibility -- we may later decide parent table
needs to be further factored into more normalized components.
As long as downstream code only consumes from VIEWS, then downstream
won't need to change.
********************************************************************/

CREATE VIEW RefRecsView AS
    SELECT rr.id as ref_ref_id, rr.song_id, rr.source, rr.link
    FROM RefRecs as rr;

CREATE VIEW ChartsView AS
    SELECT c.id as chart_id, c.song_id, c.source, c.link
    FROM Charts as c;

CREATE VIEW ContactView AS
    SELECT c.id as contact_id, c.person_id, c.contact_type, c.contact_info, c.link
    FROM Contact as c;

CREATE VIEW PersonView AS
    SELECT p.id as person_id, p.public_name, p.full_name
    FROM Person as p;

CREATE VIEW InstrumentView AS
    SELECT i.id as instrument_id, i.instrument
    FROM Instrument as i;
    
CREATE VIEW SubgenreView AS
    SELECT
        s.id as subgenre_id, s.genre_id, s.subgenre, g.genre
    FROM Subgenre as s
    INNER JOIN Genre as g
        ON s.genre_id = g.id;

CREATE VIEW KeyView AS
    SELECT
        k.id as key_id, k.mode_id, k.root, m.mode, k.root || ' ' || m.mode as key
    FROM Key as k
    INNER JOIN Mode as m
        ON k.mode_id = m.id;

CREATE VIEW EventGenView AS
    SELECT 
        e.id as event_gen_id,
        e.genre_id as event_genre_id,
        e.venue_id,
        e.host_id,
        e.date as event_gen_date,
        e.time as event_gen_time,
        e.name as event_gen,
        v.venue as venue_name,
        v.address as venue_address,
        v.city as venue_city,
        v.zip as venue_zip,
        v.state as venue_state,
        v.web as venue_web,
        g.genre as event_genre,
        p.public_name as host_public_name,
        p.full_name as host_full_name
    FROM EventGen as e
    INNER JOIN Venue as v
        ON e.venue_id = v.id
    INNER JOIN Genre as g
        ON e.genre_id = g.id
    LEFT JOIN Person as p
        ON e.host_id = p.id;

CREATE VIEW EventOccView AS
    SELECT
        o.id as event_occ_id,
        o.name as event_occ,
        o.date as event_occ_date,
        g.*
    FROM EventOcc as o
    INNER JOIN EventGenView as g
        ON o.event_gen_id = g.event_gen_id;

CREATE VIEW PersonInstrumentView AS
    SELECT
        a.id as person_instrument_id,
        a.instrument_id,
        a.person_id,
        i.instrument,
        p.full_name,
        p.public_name
    FROM PersonInstrument as a
    INNER JOIN Person as p
        ON a.person_id = p.id
    INNER JOIN Instrument as i
        ON a.instrument_id = i.id;

CREATE VIEW SongView AS
    SELECT
        s.id as song_id,
        s.song,
        s.composer_id,
        s.instrumental,
        k.*,
        sg.*
    FROM Song as s
    LEFT JOIN KeyView as k
        ON s.key_id = k.key_id
    LEFT JOIN SubgenreView as sg
        ON s.subgenre_id = sg.subgenre_id;

CREATE VIEW SongPerformerView AS
    SELECT
        sp.id as song_performer_id,
        sp.song_perform_id,    
        pi.id as person_instrument_id,
        pi.person_id,
        pi.instrument_id,
        s.song_id,
        s.event_occ_id
    FROM SongPerformer as sp
    INNER JOIN PersonInstrument as pi
        ON pi.id = sp.person_instrument_id
    INNER JOIN SongPerform as s
        ON s.id = sp.song_perform_id;

CREATE VIEW SongPerformView AS
    SELECT 
        sp.id as song_perform_id,
        b.i_played,
        b.num_players,
        v.num_videos IS NOT NULL as has_video,
        e.*,
        s.*,
        k.key_id as performed_key_id,
        k.mode_id as performed_mode_id,
        k.root as performed_root,
        k.mode as performed_mode,
        k.key as performed_key
    FROM SongPerform as sp
    LEFT JOIN (
        SELECT
            p.song_perform_id, SUM(a.me) > 0 as i_played, COUNT(p.id) as num_players
        FROM SongPerformer as p
        INNER JOIN (
            SELECT
                id, person_id = "paul_k" as me
            FROM PersonInstrument
            ) as a
            ON p.person_instrument_id = a.id 
        GROUP BY p.song_perform_id
    ) as b
        ON b.song_perform_id = sp.id
    LEFT JOIN (
        SELECT
            song_perform_id, count(id) as num_videos
        FROM PerformanceVideo
        GROUP BY song_perform_id
    ) as v
        ON v.song_perform_id = sp.id
    INNER JOIN EventOccView as e
        ON e.event_occ_id = sp.event_occ_id
    INNER JOIN SongView as s
        ON s.song_id = sp.song_id
    LEFT JOIN KeyView as k
        ON k.key_id = sp.key_id;


/*** Populate Schema Tables *******************/

INSERT INTO _schema_tables (table_name, description) VALUES
	("Charts", "Links to charts for songs."),    
	("Composer", "Composer information"),
	("Contact", "Contact information for a person, e.g., social media links."),
	("EventGen", "Recurring events, including event's venue and the recurrence pattern.  Due to the data design, even one-off gigs are defined in EventGen."),
	("EventOcc", "Specific events, including the event's specific date and EventGen that it derives from."),
	("Genre", "Coarse genre information. Genres are at the level of 'Jazz' vs 'Blues', etc.  See also `SubGrenre`."),
	("Instrument", "Instrument information."),
	("Key", "Key signature / mode information."),
	("Mode", "Information about mode."),
	("PerformanceVideo", "Video link for a performed song."),
	("Person", "Public Information about a person."),
	("PersonInstrument", "Which instruments are played by a given person."),
	("RefRecs", "Links to reference recordings of songs."),
	("Setlist", "Setlist information."),
	("SetlistSongs", "Information about songs on a Setlist, including song name, key, and which instrument I will play."),
	("Song", "Information about a song, including song name, key, etc."),
	("SongLearn", "Information about songs that I've learned, including instrument, key, and when I learned it."),
	("SongPerform", "Information about a particular performance of a song."),
	("SongPerformer", "Information about performers on a given performed song."),
	("SubGenre", "Granular genre information. SubGenres can be at the level of 'Bop' vs 'Swing', etc.  See also `Grenre`."),
	("Venue", "Information about a physical venue, including venue name, address, etc.");



INSERT INTO _schema_columns (table_name, column, description) VALUES
	("Charts", "id", "Unique ID of the Chart."),
	("Charts", "song_id", "ID of the Chart's song"),
	("Charts", "source", "Source of the chart, e.g., web link or iReal, etc."),
	("Charts", "link", "Link, etc., url or uri"),    
	("Composer", "id", "Unique ID for Composer."),
	("Composer", "composer", "Composer name."),
	("Contact", "id", "Unique ID for Contact info."),
	("Contact", "person_id", "ID for the Contact's person."),
	("Contact", "contact_type", "The kind of contact, e.g., Facebook vs YouTube etc."),
	("Contact", "contact_info", "Free form text contact info, like phone numbers, etc."),
	("Contact", "link", "Hyperlink, e.g., for Facebook etc."),
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
	("Mode", "id", "Unique ID of the mode."),
	("Mode", "mode", "Descriptive name of the mode."),
	("PerformanceVideo", "id", "Unique ID of the PerformanceVideo"),
	("PerformanceVideo", "song_perform_id", "ID of the SongPerform"),
	("PerformanceVideo", "source", "Source of the recording, e.g., YouTube or Spotify, etc."),
	("PerformanceVideo", "link", "Link, etc., url or uri"),    
	("Person", "id", "Unique ID for Person."),
	("Person", "public_name", "Person's publicly used name, typically their first name and last initial."),
	("Person", "full_name", "Person's full name."),
	("PersonInstrument", "id", "Unique ID for PersonInstrument."),
	("PersonInstrument", "person_id", "ID of the Person."),
	("PersonInstrument", "instrument_id", "ID of the Instrument."),
	("RefRecs", "id", "Unique ID of the RefRec."),
	("RefRecs", "song_id", "ID of the RefRec's song"),
	("RefRecs", "source", "Source of the recording, e.g., YouTube or Spotify, etc."),
	("RefRecs", "link", "Link, etc., url or uri"),
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
	("SubGenre", "id", "Unique ID of the SubGenre."),
	("SubGenre", "subgenre", "Name of the SubGenre.  Subgenre provides more granularity than Genre.  E.g., 'Jazz' as a Genre, 'Bop', 'Swing' etc as SubGenres of 'Jazz'."),
	("SubGenre", "genre_id", "ID of the Genre."),
	("Venue", "id", "Unique ID of the Venue."),
	("Venue", "venue", "Name of the Venue, e.g, “Madcats”."),
	("Venue", "address", "Street address of the Venue."),
	("Venue", "city", "City of the Venue."),
	("Venue", "zip", "Zipcode of the Venue."),
	("Venue", "state", "State of the Venue."),
	("Venue", "web", "Link(s) to Venue's website.");
