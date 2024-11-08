from jamdb.globals import TEST_DATA_DIR, TEST_DB_FILE
from jamdb.db import db_factory

db_handler = db_factory(data_dir=TEST_DATA_DIR, db_file=TEST_DB_FILE)

def test_simple():
    actual = db_handler.get_row(table_name="Key", primary_key="D_minor")
    expected = {'id': 'D_minor', 'root': 'D', 'mode_id': 'minor'}
    assert actual == expected
