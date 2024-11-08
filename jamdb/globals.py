from pathlib import Path

ME_ID = "paul_k"
DATA_DIR = Path("data/paul_k")
DB_FILE = DATA_DIR / "jamming.db"


TEST_DATA_DIR = Path("data/testing")
TEST_DB_FILE = TEST_DATA_DIR / "jamming.db"

def _id_from_name(name):
    return name.lower().strip().replace(" ", "_")

def _format_id_as_str(x):
    # Some ids are strs that look like nums, and pandas will cast them to float.
    # This undoes that.
    try:
        x = float(x)
        x = f"{x:.0f}"
    except ValueError:
        pass
    return x
    