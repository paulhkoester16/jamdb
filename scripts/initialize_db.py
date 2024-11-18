# This file is TEMP
#   For now, we are still using the ODS files "data/source_data/public.ods"
#   as the system of record, but eventually, we'll want to use a persisitent
#   DB as the system of record.
#   Until then, we should only modify the ODS files, and periodically rebuild.
from pathlib import Path
import sys
import argparse
from pandas_ods_reader import read_ods
import sqlalchemy
import eralchemy

REPO_ROOT = Path("./").absolute()
sys.path.append(str(REPO_ROOT))
from jamdb.db import DBHandler
from jamdb.transformations import format_id_as_str
from jamdb.globals import ME_ID

SQL_FILE = Path("jamdb/jamming.sql")
SRC_DATA_DIR = REPO_ROOT / "data" / "source_data" 
ODS_FILE = SRC_DATA_DIR / "public.ods"


def _parse_sql_file(sql_file):
    def drop_comment(row):
        if row.startswith("/"):
            return row.split("/", 2)[-1]
        return row.strip()

    sql_file = Path(sql_file)
    commands = [drop_comment(x.strip()) for x in sql_file.read_text().split(";")]
    commands = [x + ";" for x in commands if x != ""]
    commands = [command.strip() for command in commands]
    return commands

def _sorted_table_names():
    # When inserting, need to insert in correct order, regarding FKs
    # Here I assume the order of tabels in the sql file addresses the order    
    sql_commands = _parse_sql_file(SQL_FILE)
    table_names = [x.split(" ", 3)[2] for x in sql_commands if x.startswith("CREATE TABLE")]
    table_names = [x for x in table_names if not x.startswith("_")]
    return table_names

def create_tables(db_handler):
    with db_handler.Session.begin() as session:
        for command in _parse_sql_file(SQL_FILE):
            session.execute(sqlalchemy.text(command))

def insert_for_song_performance(db_handler, song_perform, me_id=ME_ID):
    song_performers = []
    videos = []
    
    for _, song in song_perform.iterrows():
        sp_id = song["id"]
        if song["instrument_id"] is not None:
            song_performers.append(
                {
                    "id": len(song_performers),
                    "song_perform_id": sp_id, 
                    "person_instrument_id": f"{me_id}:{song['instrument_id']}"
                }
            )
        for key, val in song.items():
            if key.startswith("other_player_") and val is not None:
                song_performers.append(
                    {
                        "id": len(song_performers),                        
                        "song_perform_id": sp_id, 
                        "person_instrument_id": val
                    }
                )
            if key == "video" and val is not None:
                videos.append(
                    {
                        "id": len(videos),                        
                        "song_perform_id": sp_id,
                        "source": "YouTube",
                        "link": val
                    }
                )

    song_perform = song_perform[["id", "event_occ_id", "song_id", "key_id"]]
    db_handler.insert("SongPerform", song_perform.to_dict(orient="records"))
    db_handler.insert("SongPerformer", song_performers)
    db_handler.insert("PerformanceVideo", videos)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog='initialize_jam_db')

    parser.add_argument('data_dir')
    parser.add_argument('--db_file')
    parser.add_argument('--force_rebuild', action="store_true")

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    db_file = args.db_file
    if db_file is None:
        db_file = data_dir / "jamming.db"
    db_file = Path(db_file)
    force_rebuild = args.force_rebuild

    if force_rebuild:
        db_file.unlink(missing_ok=True)

    if db_file.exists():
        
        print(f"{db_file=} already exists.")
    else:
        db_handler = DBHandler.from_db_file(db_file)
        create_tables(db_handler)

        for table_name in _sorted_table_names():
            if table_name in ["PerformanceVideo", "SongPerformer"]:
                continue
            df = read_ods(ODS_FILE, table_name)
            if table_name == "Venue":
                df["zip"] = df["zip"].apply(format_id_as_str)
            if isinstance(df["id"].iloc[0], (float, int)):
                df["id"] = df["id"].apply(format_id_as_str)
        
            if table_name == "SongPerform":
                insert_for_song_performance(db_handler, df)
            else:
                db_handler.insert(table_name, df.to_dict(orient="records"))
            
        print("DB created!")

    eralchemy.render_er(f"sqlite:///{db_file}", str(data_dir / "erd.png"))
