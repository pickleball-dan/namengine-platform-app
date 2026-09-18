import sys, os
sys.path.insert(0, ".")
from namengine.core.storage import get_database_path, initialize_database
from sqlite3 import connect
import contextlib

db = get_database_path()
print("DB path:", db)
initialize_database(db)

with contextlib.closing(connect(str(db))) as c:
    rows = c.execute(
        "SELECT id, vertical FROM sessions WHERE vertical='business' ORDER BY rowid DESC LIMIT 5"
    ).fetchall()
    print("Business sessions:", rows)

    all_rows = c.execute(
        "SELECT id, vertical FROM sessions ORDER BY rowid DESC LIMIT 10"
    ).fetchall()
    print("All recent sessions:", all_rows)
