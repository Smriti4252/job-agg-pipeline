import os
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/pipeline.db")
GOLD_DIR = Path("data/gold")


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


# ---------------------------------------------------------------
# SCORING LOGIC
# ---------------------------------------------------------------
def calculate_score(row):
    score = 0

    title = (row["title"] or "").lower()
    description = (row["description"] or "").lower()

    entry_keywords = ["junior", "entry", "fresher", "graduate", "trainee"]
    tech_keywords = ["python", "sql", "etl", "pipeline", "data engineer"]

    if any(k in title for k in entry_keywords):
        score += 2
    if any(k in description for k in entry_keywords):
        score += 1

    if row["remote"] == 1:
        score += 1

    if any(k in title for k in tech_keywords):
        score += 1

    return score


# ---------------------------------------------------------------
# Outreach message generator
# ---------------------------------------------------------------
def generate_outreach_message(title, company):
    if not company:
        company = "your team"

    return (
        f"Hi, I came across your '{title}' position at {company}. "
        f"I’m really interested because it aligns well with my hands-on work in ETL pipelines, "
        f"SQL, Python, and modern data engineering tools. "
        f"I would love to connect and discuss the opportunity further!"
    )


# ---------------------------------------------------------------
# MAIN GOLD PIPELINE
# ---------------------------------------------------------------
def silver_to_gold():
    print("🔄 Starting Silver → Gold processing...")

    if not DB_PATH.exists():
        print("❌ SQLite warehouse database missing!")
        print(f"Expected at: {DB_PATH}")
        return 0

    conn = get_db()

    # load Silver
    df = pd.read_sql("SELECT * FROM silver_jobs", conn)

    if df.empty:
        print("❌ No rows found in Silver table.")
        return 0

    # ---------------------------------------------------------------
    # CLEAN
    # ---------------------------------------------------------------
    print("✨ Cleaning data...")
    df = df.dropna(subset=["url"])
    df["title"] = df["title"].fillna("Untitled")
    df["company"] = df["company"].fillna("Unknown")
    df["location"] = df["location"].fillna("Unknown")

    # ---------------------------------------------------------------
    # DEDUPE by URL
    # ---------------------------------------------------------------
    print("✨ Removing duplicate jobs...")
    df = df.sort_values("fetched_at", ascending=False)
    df = df.drop_duplicates(subset=["url"], keep="first")

    # ---------------------------------------------------------------
    # SCORING
    # ---------------------------------------------------------------
    print("✨ Scoring jobs...")
    df["score"] = df.apply(calculate_score, axis=1)

    # ---------------------------------------------------------------
    # OUTREACH TEXT
    # ---------------------------------------------------------------
    print("✨ Adding outreach messages...")
    df["outreach_message"] = df.apply(
        lambda row: generate_outreach_message(row["title"], row["company"]),
        axis=1
    )

    # ---------------------------------------------------------------
    # EXPORT SNAPSHOTS
    # ---------------------------------------------------------------
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    csv_path = GOLD_DIR / f"gold_{snapshot}.csv"
    parquet_path = GOLD_DIR / f"gold_{snapshot}.parquet"

    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)

    print(f"📁 Gold CSV saved at: {csv_path}")
    print(f"📁 Gold Parquet saved at: {parquet_path}")

    # ---------------------------------------------------------------
    # SAVE INTO SQLITE GOLD TABLE (New!)
    # ---------------------------------------------------------------
    print("🗄️ Writing Gold table into SQLite...")

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS gold_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            title TEXT,
            company TEXT,
            location TEXT,
            remote INTEGER,
            url TEXT UNIQUE,
            description TEXT,
            post_date TEXT,
            fetched_at TEXT,
            salary TEXT,
            tags TEXT,
            score REAL,
            outreach_message TEXT
        )
    """)

    for _, r in df.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO gold_jobs (
                job_id, title, company, location, remote,
                url, description, post_date, fetched_at,
                salary, tags, score, outreach_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["job_id"], r["title"], r["company"], r["location"],
            int(r["remote"]), r["url"], r["description"], r["post_date"],
            r["fetched_at"], r["salary"], r["tags"],
            float(r["score"]), r["outreach_message"]
        ))

    conn.commit()
    conn.close()

    print("✅ Gold table successfully saved to SQLite!")
    return len(df)


# ---------------------------------------------------------------
# RUN
# ---------------------------------------------------------------
if __name__ == "__main__":
    silver_to_gold()
