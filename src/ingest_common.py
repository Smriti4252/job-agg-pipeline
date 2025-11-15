import os
import json
import sqlite3
import datetime
from pathlib import Path

# Base data directory (inside your project)
DATA_DIR = Path("data")
BRONZE_DIR = DATA_DIR / "bronze"

# Ensure folder exists
BRONZE_DIR.mkdir(parents=True, exist_ok=True)

# SQLite database file for Bronze layer
BRONZE_DB = BRONZE_DIR / "bronze.db"


def init_bronze_db():
    """
    Create or connect to bronze.db and ensure raw_jobs table exists.
    """
    conn = sqlite3.connect(str(BRONZE_DB))
    cur = conn.cursor()

    # Create raw_jobs table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        filename TEXT,
        raw_json TEXT NOT NULL
    );
    """)

    conn.commit()
    return conn


def save_raw(source_name, payload):
    """
    Saves the raw JSON into:
    1) A .json file in data/bronze
    2) Inserts the raw content into bronze.db
    """

    # Timestamp for filename
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = BRONZE_DIR / f"{ts}_{source_name}.json"

    # Save JSON file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # Insert into SQLite table
    conn = init_bronze_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO raw_jobs (source, fetched_at, filename, raw_json)
        VALUES (?, ?, ?, ?)
        """,
        (
            source_name,
            datetime.datetime.utcnow().isoformat(),
            str(filename),
            json.dumps(payload)
        )
    )
    conn.commit()
    conn.close()

    return str(filename)
