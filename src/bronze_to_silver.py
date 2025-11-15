import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------
BRONZE_DIR = Path("data/bronze")
DB_PATH = Path("data/pipeline.db")


# ---------------------------------------------------------------------
# DB CONNECTION
# ---------------------------------------------------------------------
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


# ---------------------------------------------------------------------
# NORMALIZE RAW API PAYLOAD → SILVER FORMAT
# ---------------------------------------------------------------------
def normalize_payload_to_silver(payload, source):
    """
    Convert raw API-specific JSON into a unified Silver structure.
    Handles differences in API shapes.
    """

    rows = []
    fetched_at = datetime.now().isoformat()

    # ----------------------------------------------------------
    # FIX: Extract correct list of job items for each API
    # ----------------------------------------------------------
    if source == "remoteok":
        # RemoteOK returns a LIST
        data = [i for i in payload if isinstance(i, dict)]

    elif source == "remotive":
        # Remotive returns an OBJECT → extract the "jobs" list
        data = payload.get("jobs", [])

    elif source == "arbeitnow":
        # ArbeitNow is inconsistent: list OR inside "data"
        if isinstance(payload, list):
            data = payload
        else:
            data = payload.get("data", [])

    else:
        print(f"⚠ Unknown API source: {source}, skipping.")
        return rows

    # ----------------------------------------------------------
    # Normalize each job record
    # ----------------------------------------------------------
    for item in data:

        if source == "remoteok":
            job_id = str(item.get("id"))
            title = item.get("position") or item.get("title")
            company = item.get("company")
            location = item.get("location")
            remote = 1 if "remote" in str(location).lower() else 0
            url = item.get("url")
            description = item.get("description")
            post_date = item.get("date")
            salary = item.get("salary")
            tags = ", ".join(item.get("tags") or [])

        elif source == "remotive":
            job_id = str(item.get("id"))
            title = item.get("title")
            company = item.get("company_name")
            location = item.get("candidate_required_location")
            remote = 1
            url = item.get("url")
            description = item.get("description")
            post_date = item.get("publication_date")
            salary = item.get("salary")
            tags = ", ".join(item.get("tags") or [])

        elif source == "arbeitnow":
            job_id = str(item.get("slug"))
            title = item.get("title")
            company = item.get("company_name")
            location = item.get("location")
            remote = 1 if item.get("remote") else 0
            url = item.get("url")
            description = item.get("description")
            post_date = item.get("date_posted")
            salary = item.get("salary")
            tags = ", ".join(item.get("tags") or [])

        # --------------------------
        # Scoring + outreach
        # --------------------------
        score = 1.0
        if "junior" in (title or "").lower():
            score += 1
        if remote:
            score += 0.5

        outreach_message = f"Hi, I came across your '{title}' role at {company}."

        rows.append((
            job_id, title, company, location, remote, url,
            description, post_date, fetched_at, salary,
            tags, score, outreach_message
        ))

    return rows



# ---------------------------------------------------------------------
# MAIN PIPELINE: Bronze JSON → Silver SQLite
# ---------------------------------------------------------------------
def bronze_to_silver():
    print("🔄 Starting Bronze → Silver pipeline...")

    conn = get_db()
    cur = conn.cursor()

    # ----------------------------------------------------------
    # Create Bronze table
    # ----------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bronze_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            raw_json TEXT,
            fetched_at TEXT
        )
    """)

    # ----------------------------------------------------------
    # Create Silver table
    # ----------------------------------------------------------
    cur.execute("""
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
            tags TEXT,
            score REAL,
            outreach_message TEXT
        )
    """)

    now_str = datetime.now(timezone.utc).isoformat()

    # ----------------------------------------------------------
    # Load all Bronze JSON files
    # ----------------------------------------------------------
    json_files = list(BRONZE_DIR.glob("*.json"))

    if not json_files:
        print("❌ No Bronze JSON files found.")
        return

    for file in json_files:

        # Extract API source correctly (last part of filename)
        # Example: 20251115T141225Z_remoteok.json → remoteok
        source = file.stem.split("_")[-1].lower().strip()

        print(f"📥 Loading Bronze file: {file}  (source={source})")

        # -------------------------------
        # Load JSON file
        # -------------------------------
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Insert raw JSON into Bronze table
        cur.execute(
            "INSERT INTO bronze_raw (source, raw_json, fetched_at) VALUES (?, ?, ?)",
            (source, json.dumps(data), now_str)
        )

        # -------------------------------
        # Normalize → Silver rows
        # -------------------------------
        rows = normalize_payload_to_silver(data, source)

        for row in rows:
            cur.execute("""
                INSERT OR REPLACE INTO silver_jobs (
                    job_id, title, company, location, remote, url,
                    description, post_date, fetched_at, salary,
                    tags, score, outreach_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, row)

    # -------------------------------
    # Save & Close
    # -------------------------------
    conn.commit()
    conn.close()

    print("✅ Bronze → Silver processing complete!")


# ---------------------------------------------------------------------
# RUN SCRIPT
# ---------------------------------------------------------------------
if __name__ == "__main__":
    bronze_to_silver()
