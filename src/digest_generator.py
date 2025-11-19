# Build a simple daily HTML digest out of Gold jobs.

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd


DB_FILE = Path("data/pipeline.db")
DIGEST_FOLDER = Path("data/digest")
DIGEST_FOLDER.mkdir(parents=True, exist_ok=True)


def load_gold_table():
    """Pull all Gold jobs from SQLite."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM gold_jobs", conn)
    conn.close()

    if df.empty:
        return df

    # Make sure timestamps are in good shape
    df["post_date"] = pd.to_datetime(df["post_date"], errors="coerce", utc=True)
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], errors="coerce", utc=True)

    return df


def render_job_block(row):
    """
    Small HTML snippet for one job.
    Keep it readable—digest emails are meant to be skimmed.
    """
    desc = (row["description"] or "").strip()
    short = desc[:200] + ("..." if len(desc) > 200 else "")

    return f"""
        <div style="margin-bottom: 18px;">
            <div><b>{row['title']}</b> — {row['company']}</div>
            <div style="font-size: 14px; color:#444;">{row['location']}</div>
            <a href="{row['url']}" target="_blank">Apply Link</a>
            <div style="margin-top: 6px; font-size: 13px; color:#666;">
                {short}
            </div>
        </div>
    """


def render_section(df, heading):
    """Convert a dataframe slice into a titled HTML section."""
    if df.empty:
        return f"<h2>{heading}</h2><p>No jobs found.</p>"

    blocks = [render_job_block(r) for _, r in df.iterrows()]
    return f"<h2>{heading}</h2>\n" + "\n".join(blocks)


def build_html_digest(top20, remote_only, fresh_jobs):
    """Combine all sections into the final HTML email."""
    now = datetime.now(timezone.utc)

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">

        <h1>Your Daily Job Digest</h1>

        {render_section(top20, "Top 20 Jobs (By Score)")}

        {render_section(remote_only, "Remote-Friendly Roles")}

        {render_section(fresh_jobs, "Fresh Listings (Last 3 Days)")}

        <hr>
        <div style="font-size: 12px; color:#777;">
            Generated at {now.strftime("%Y-%m-%d %H:%M:%S %Z")}
        </div>

    </body>
    </html>
    """


def generate_digest():
    print("→ Loading Gold data...")
    df = load_gold_table()

    if df.empty:
        print("   Gold table is empty.")
        return

    # Top 20 by score
    top20 = df.sort_values("score", ascending=False).head(20)

    # Remote-only
    remote_only = df[df["remote"] == 1].sort_values("score", ascending=False).head(20)

    # Last 3 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    fresh = df[df["post_date"] >= cutoff].sort_values("post_date", ascending=False).head(20)

    # Build & write HTML digest
    html = build_html_digest(top20, remote_only, fresh)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_file = DIGEST_FOLDER / f"digest_{ts}.html"
    out_file.write_text(html, encoding="utf-8")

    print(f"✔ Digest generated → {out_file}")


if __name__ == "__main__":
    generate_digest()
