import sqlalchemy
from jamdb.globals import TEST_DATA_DIR, TEST_DB_FILE
from jamdb.db import DBHandler

db_handler = DBHandler.from_db_file(db_file=TEST_DB_FILE)

def test_simple():
    with db_handler.Session.begin() as session:
        actual = session.execute(sqlalchemy.text("SELECT * FROM Key WHERE id == 'D_minor'")).fetchone()

    expected = ('D_minor', 'D', 'minor')
    assert actual == expected
