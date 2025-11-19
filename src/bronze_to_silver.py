# Turn Bronze JSON files + bronze_raw DB rows into a normalized silver_jobs table.

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ingest_common import get_db_conn, PIPELINE_DB

BRONZE_DIR = Path("data/bronze")


def _parse_remoteok(item: Dict[str, Any]) -> Dict:
    return {
        "job_id": item.get("id") or item.get("slug") or "",
        "title": item.get("position") or item.get("title"),
        "company": item.get("company") or item.get("company_name"),
        "location": item.get("location") or item.get("candidate_required_location") or "",
        "remote": 1 if item.get("remote") in (True, "true", 1, "1") else 0,
        "url": item.get("url") or item.get("apply_url") or "",
        "description": item.get("description") or "",
        "post_date": item.get("date") or item.get("publication_date") or None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "salary": item.get("salary"),
        "tags": ", ".join(item.get("tags") or [])
    }


def _parse_remotive(item: Dict[str, Any]) -> Dict:
    return {
        "job_id": item.get("id") or "",
        "title": item.get("title"),
        "company": item.get("company_name"),
        "location": item.get("candidate_required_location") or "",
        "remote": 1,
        "url": item.get("url") or "",
        "description": item.get("description") or "",
        "post_date": item.get("publication_date") or None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "salary": item.get("salary"),
        "tags": ", ".join(item.get("tags") or [])
    }


def _guess_source_from_filename(name: str) -> Optional[str]:
    if "remoteok" in name:
        return "remoteok"
    if "remotive" in name:
        return "remotive"
    if "arbeit" in name:
        return "arbeitnow"
    return None


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS silver_jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            remote INTEGER,
            url TEXT,
            description TEXT,
            post_date TEXT,
            fetched_at TEXT,
            salary TEXT,
            tags TEXT
        );

        -- keep bronze_raw in DB via ingest_common; no change here
        """
    )
    conn.commit()


def _load_json_files() -> List[Dict]:
    files = sorted(BRONZE_DIR.glob("*.json"))
    out = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            # our ingesters write lists
            if isinstance(data, list):
                source = _guess_source_from_filename(f.name) or "unknown"
                for item in data:
                    out.append({"_source": source, **item})
        except Exception as e:
            print(f"Could not read {f.name}: {e}")
    return out


def normalize_and_write():
    """Main entry: read bronze JSONs, normalize, write into silver_jobs table."""
    rows = _load_json_files()
    if not rows:
        print(" No bronze JSON files found.")
        return 0

    conn = get_db_conn(PIPELINE_DB)
    _ensure_tables(conn)
    cur = conn.cursor()

    inserted = 0
    for r in rows:
        src = r.pop("_source", "")
        parsed = _parse_remoteok(r) if src == "remoteok" else (_parse_remotive(r) if src == "remotive" else {
            "job_id": r.get("id") or r.get("slug") or "",
            "title": r.get("title") or r.get("position"),
            "company": r.get("company") or r.get("company_name"),
            "location": r.get("location") or r.get("candidate_required_location") or "",
            "remote": 1 if r.get("remote") else 0,
            "url": r.get("url") or r.get("apply_url") or "",
            "description": r.get("description") or "",
            "post_date": r.get("date") or r.get("publication_date") or None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "salary": r.get("salary"),
            "tags": ", ".join(r.get("tags") or [])
        })

        try:
            cur.execute(
                """
                INSERT OR REPLACE INTO silver_jobs
                (job_id, title, company, location, remote, url, description, post_date, fetched_at, salary, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(parsed.get("job_id") or ""),
                    parsed.get("title"),
                    parsed.get("company"),
                    parsed.get("location"),
                    int(parsed.get("remote") or 0),
                    parsed.get("url"),
                    parsed.get("description"),
                    parsed.get("post_date"),
                    parsed.get("fetched_at"),
                    parsed.get("salary"),
                    parsed.get("tags"),
                ),
            )
            inserted += 1
        except Exception as e:
            print("Failed to insert row:", e)

    conn.commit()
    conn.close()
    print(f" Bronze → Silver done. Inserted/updated {inserted} rows.")
    return inserted


if __name__ == "__main__":
    normalize_and_write()
