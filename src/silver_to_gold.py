# Read silver_jobs table, dedupe, score, add outreach message, save gold snapshot
# and write/replace gold_jobs table in pipeline DB.

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import List
import pandas as pd
from ingest_common import get_db_conn, PIPELINE_DB

OUTPUT_DIR = Path("data/gold")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_silver(conn: sqlite3.Connection) -> pd.DataFrame:
    try:
        df = pd.read_sql("SELECT * FROM silver_jobs", conn)
    except Exception:
        return pd.DataFrame()
    return df


def _canonical_url(u: str) -> str:
    if not isinstance(u, str) or u.strip() == "":
        return ""
    return u.split("?")[0].rstrip("/")


def _score_row(row) -> float:
    score = 0.0
    title = str(row.get("title") or "").lower()
    desc = str(row.get("description") or "").lower()
    if any(k in title for k in ("junior", "entry", "fresher", "intern", "graduate")):
        score += 2.0
    if row.get("remote") == 1:
        score += 1.0
    # small heuristics: keywords that matter
    for kw in ("etl", "sql", "python", "dbt", "snowflake", "spark"):
        if kw in title or kw in desc:
            score += 0.5
    return round(score, 2)


def _outreach_text(title: str, company: str) -> str:
    company = company or "your team"
    return (
        f"Hi — I found your {title} role at {company}. "
        "I’m building data pipelines and have hands-on SQL & Python experience. "
        "Would love to connect — thanks!"
    )


def run():
    print(" Starting Silver → Gold...")

    conn = get_db_conn(PIPELINE_DB)
    df = _load_silver(conn)
    if df.empty:
        print(" No rows in silver_jobs.")
        conn.close()
        return 0

    # ensure columns we use exist
    df["url"] = df.get("url", "").astype(str)
    df["title"] = df.get("title", "").astype(str)
    df["company"] = df.get("company", "").astype(str)
    df["description"] = df.get("description", "").astype(str)
    df["post_date"] = pd.to_datetime(df.get("post_date"), errors="coerce")
    df["fetched_at"] = pd.to_datetime(df.get("fetched_at"), errors="coerce")
    df["remote"] = df.get("remote", 0).fillna(0).astype(int)

    # drop rows without URL (can't dedupe) and title
    df = df.dropna(subset=["url", "title"]).copy()
    df["canon_url"] = df["url"].apply(_canonical_url)

    # dedupe: keep newest fetched_at for same canonical URL
    df = df.sort_values(by=["canon_url", "fetched_at"], ascending=[True, False])
    df = df.drop_duplicates(subset=["canon_url"], keep="first").reset_index(drop=True)

    # scoring
    df["score"] = df.apply(_score_row, axis=1)

    # outreach
    df["outreach_message"] = df.apply(lambda r: _outreach_text(r["title"], r["company"]), axis=1)

    # save snapshot
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    csv_path = OUTPUT_DIR / f"gold_{ts}.csv"
    parquet_path = OUTPUT_DIR / f"gold_{ts}.parquet"

    df_out = df[[
        "job_id", "title", "company", "location", "remote", "url",
        "description", "post_date", "fetched_at", "salary", "tags",
        "score", "outreach_message"
    ]].copy()

    df_out.to_csv(csv_path, index=False)
    try:
        df_out.to_parquet(parquet_path, index=False)
    except Exception:
        # If pyarrow isn't available, ignore parquet (CSV is enough)
        pass

    # write gold_jobs table (replace)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS gold_jobs (
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
        );
        """
    )
    conn.commit()

    # replace content
    cur.execute("DELETE FROM gold_jobs;")
    conn.commit()

    insert_sql = """
        INSERT INTO gold_jobs
        (job_id, title, company, location, remote, url, description, post_date, fetched_at, salary, tags, score, outreach_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    inserted = 0
    for _, row in df_out.iterrows():
        cur.execute(insert_sql, (
            str(row.get("job_id") or ""),
            row.get("title"),
            row.get("company"),
            row.get("location"),
            int(row.get("remote") or 0),
            row.get("url"),
            row.get("description"),
            (row.get("post_date").isoformat() if pd.notna(row.get("post_date")) else None),
            (row.get("fetched_at").isoformat() if pd.notna(row.get("fetched_at")) else None),
            row.get("salary"),
            row.get("tags"),
            float(row.get("score") or 0.0),
            row.get("outreach_message"),
        ))
        inserted += 1

    conn.commit()
    conn.close()

    print(f" Gold snapshot written: {csv_path}  (rows: {inserted})")
    return inserted


if __name__ == "__main__":
    run()
