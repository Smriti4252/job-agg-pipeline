import sqlite3

conn = sqlite3.connect("data/pipeline.db")
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("Tables found in SQLite:", tables)
