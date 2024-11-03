# This file is TEMP
#   For now, we are still using the ODS files "jamming_db/data/paul_k_db/"
#   as the system of record, but eventually, we'll want to use a persisitent
#   DB as the system of record.
#   Until then, we should only modify the ODS files, and periodically rebuild.
from pathlib import Path
import sys
import argparse
from pandas_ods_reader import read_ods

REPO_ROOT = Path("./").absolute()
sys.path.append(str(REPO_ROOT))
from jamdb.db import init_db, BackendSQLite


SQL_FILE = "jamdb/jamming.sql"
OLD_DATA_DIR = REPO_ROOT.parent / "jamming_db/data/paul_k_db/"

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
        print(f"Done!  {db_file=} already exists.")
    else:
        init_db(SQL_FILE, data_dir=data_dir, db_file=db_file)
        db_handler = BackendSQLite(data_dir=data_dir, db_file=db_file)

        ods_file = OLD_DATA_DIR / "public.ods"

        for table_name in db_handler._sorted_tables():
            table = read_ods(ods_file, table_name)

            for _, row in table.iterrows():
                try:
                    db_handler.insert_row(table_name=table_name, row=row)
                except Exception as exc:
                    msg = f"{table_name=}, {row=}"
                    raise Exception(msg) from exc
        print("Done!")

