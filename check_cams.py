import sqlite3
conn = sqlite3.connect("ibvap.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, name, source_type, source_config FROM cameras").fetchall()
for r in rows:
    print(dict(r))
conn.close()
