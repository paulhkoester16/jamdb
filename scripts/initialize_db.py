# This file is TEMP
#   For now, we are still using the ODS files "data/source_data/public.ods"
#   as the system of record, but eventually, we'll want to use a persisitent
#   DB as the system of record.
#   Until then, we should only modify the ODS files, and periodically rebuild.

import sys
import os
import argparse
import hashlib

from pathlib import Path
from shutil import copytree, rmtree
import sqlalchemy
import eralchemy
import pandas as pd

from pandas_ods_reader import read_ods

REPO_ROOT = Path("./").absolute()
sys.path.append(str(REPO_ROOT))

from jamdb.db import DBHandler
from jamdb.transformations import format_id_as_str
from jamdb.globals import ME_ID

SQL_FILE = Path("jamdb/jamming.sql")
DOCS_DIR = Path("docs")
SRC_DATA_DIR = REPO_ROOT / "data" / "source_data"
ODS_FILE = SRC_DATA_DIR / "public.ods"
DATA_SUB_DIRS = ["people"]


def row_to_hash(row):
    return hashlib.md5(str(row.to_dict().values()).encode()).hexdigest()


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
                        "source_id": "youtube",
                        "link": val
                    }
                )

    song_perform = song_perform[["id", "event_occ_id", "song_id", "key_id"]]
    db_handler.insert("SongPerform", song_perform.to_dict(orient="records"))
    db_handler.insert("SongPerformer", song_performers)
    db_handler.insert("PerformanceVideo", videos)


def process_person_picture(data_dir):
    person_pictures = []
    for person_dir in (data_dir / "people").glob("*"):
        person_id = person_dir.stem
        for person_file in person_dir.glob("*"):
            link = str(person_file.relative_to(data_dir))
            source_id = person_file.suffix
            if source_id.startswith("."):
                source_id = source_id[1:]
            person_pictures.append({"person_id": person_id, "link": link, "source_id": source_id})

    person_pictures = pd.DataFrame(person_pictures)
    person_pictures["id"] = person_pictures.apply(row_to_hash, axis=1)
    return person_pictures


def write_data_model_md(db_handler, erd_file):
    erd_file = str(erd_file.relative_to(DOCS_DIR))
    tables = db_handler.read_table('_schema_tables').to_dict(orient="records")
    columns = db_handler.read_table('_schema_columns')
    columns = dict(list(columns.groupby("table_name")))

    md = [
        '# Data Model',
        '<p align="center">',
        f'<img src="{erd_file}" width="800" title="ERD">',
        '</p>',
        '<br/>'        
    ]
    for table in tables:
        table_name = table["table_name"]
        cols = ["  <dl>"]
        for _, col in columns[table_name].iterrows():
            cols.append(f"    <dt><b>{col['column']}</b></dt><dd><i>{col['description']}</i></dd></dt>")
        cols.append("  </dl>")
        cols = "\n".join(cols)    
    
        md.append(f"<div>\n  <h2>{table_name}</h2>\n  {table['description']}<br/>\n{cols}\n</div>")
        
    with open(DOCS_DIR / "data_model.md", "w") as fh:
        fh.write("\n".join(md))


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
        if db_file.exists():
            os.remove(db_file)
        for sub_dir in DATA_SUB_DIRS:
            dir_ = data_dir / sub_dir
            print(dir_)
            if dir_.exists():
                print(f"Removing {dir_}")
                rmtree(dir_)

    if db_file.exists():
        print(f"{db_file=} already exists.")
    else:
        db_handler = DBHandler.from_db_file(db_file)

        for sub_dir in DATA_SUB_DIRS:
            src_dir = SRC_DATA_DIR / sub_dir
            dest_dir = data_dir / sub_dir
            print(f"Copy {src_dir} over to {dest_dir}")
            copytree(src_dir, dest_dir)

        print("Creating tables")
        create_tables(db_handler)

        for table_name in _sorted_table_names():
            print(f"Inserting into {table_name}")
            if table_name in ["PerformanceVideo", "SongPerformer"]:
                continue

            if table_name == "PersonPicture":
                df = process_person_picture(data_dir)
            else:
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

    exclude_tables=["_schema_tables", "_schema_columns"]
    eralchemy.render_er(f"sqlite:///{db_file}", str(data_dir / "erd.png"), exclude_tables=exclude_tables)
    erd_file = DOCS_DIR / "images/erd.png"
    eralchemy.render_er(f"sqlite:///{db_file}", str(erd_file), exclude_tables=exclude_tables)

    write_data_model_md(db_handler, erd_file)
