from jamdb.db import BackendSQLite

DB_FILE = "data/jamming.db"
conn = BackendSQLite(DB_FILE)

def test_simple():
    actual = conn.get_row(table_name="Key", primary_key="D_minor")
    expected = {'id': 'D_minor', 'root': 'D', 'mode_id': 'minor'}
    assert actual == expected
