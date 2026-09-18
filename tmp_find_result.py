import sqlite3, os
db = 'namengine.db'
if not os.path.exists(db):
    print('no db')
    exit()
con = sqlite3.connect(db)
rows = con.execute(
    "SELECT s.id, r.id, r.name FROM results r "
    "JOIN sessions s ON r.session_id = s.id "
    "WHERE s.vertical_slug = 'baby' AND r.name IS NOT NULL "
    "ORDER BY r.id DESC LIMIT 5"
).fetchall()
for row in rows:
    print(row)
con.close()
