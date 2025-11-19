import json
from pathlib import Path
from datetime import datetime, timezone
import sqlite3
from typing import Any, Dict, Optional

BRONZE_DIR = Path("data/bronze")
BRONZE_DIR.mkdir(parents=True, exist_ok=True)

PIPELINE_DB = Path("data/pipeline.db")
PIPELINE_DB.parent.mkdir(parents=True, exist_ok=True)


def utcnow_ts() -> str:
    """Compact UTC timestamp for filenames."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_bronze_file(payload: Any, source: str) -> Path:
    """Write payload (list/dict) to data/bronze with timestamped filename."""
    ts = utcnow_ts()
    fname = f"{ts}_{source}.json"
    out = BRONZE_DIR / fname
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def get_db_conn(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Return sqlite3 connection to pipeline DB (creates file if missing)."""
    db_path = db_path or PIPELINE_DB
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def ensure_bronze_table(conn: Optional[sqlite3.Connection] = None) -> None:
    """Create bronze_raw table if missing."""
    close_after = False
    if conn is None:
        conn = get_db_conn()
        close_after = True

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS bronze_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    if close_after:
        conn.close()


def insert_bronze_row(source: str, payload: Any, conn: Optional[sqlite3.Connection] = None) -> int:
    """
    Insert a row into bronze_raw and return inserted id.
    If conn not provided, opens/closes a connection.
    """
    close_after = False
    if conn is None:
        conn = get_db_conn()
        close_after = True

    ensure_bronze_table(conn)
    fetched_at = datetime.now(timezone.utc).isoformat()
    j = json.dumps(payload, ensure_ascii=False)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO bronze_raw (source, raw_json, fetched_at) VALUES (?, ?, ?)",
        (source, j, fetched_at),
    )
    conn.commit()
    row_id = cur.lastrowid
    if close_after:
        conn.close()
    return row_id


def persist_raw(payload: Any, source: str, write_db: bool = True) -> Dict[str, Any]:
    """
    Save payload to bronze file and optionally insert a DB row.
    Returns {"path": ..., "db_id": ... (optional)}.
    """
    path = write_bronze_file(payload, source)
    out = {"path": str(path)}
    if write_db:
        out["db_id"] = insert_bronze_row(source, payload)
    return out


if __name__ == "__main__":
    # quick local test
    sample = [{"id": "t1", "title": "Local test job"}]
    r = persist_raw(sample, "localtest", write_db=True)
    print("Wrote:", r)
