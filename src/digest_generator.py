import os
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path("data/pipeline.db")
DIGEST_DIR = Path("data/digest")
DIGEST_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Load Gold Table from SQLite
# -----------------------------------------------------------------------------
def load_gold():
    if not DB_PATH.exists():
        raise FileNotFoundError("❌ pipeline.db not found!")

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM gold_jobs", conn)
    conn.close()

    if df.empty:
        raise ValueError("❌ Gold table contains zero rows!")

    # Normalize timestamps
    df["post_date"] = pd.to_datetime(df["post_date"], errors="coerce")
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], errors="coerce")

    # Convert any tz-aware → UTC tz-naive
    try:
        df["post_date"] = df["post_date"].dt.tz_convert("UTC").dt.tz_localize(None)
    except:
        pass

    return df


# -----------------------------------------------------------------------------
# Build Digest Sections
# -----------------------------------------------------------------------------
def create_digest_sections(df):
    now = datetime.utcnow()

    # 1) Top 20 highest scoring jobs
    top20 = df.sort_values("score", ascending=False).head(20)

    # 2) All remote jobs
    remote = df[df["remote"] == 1]

    # 3) Fresh jobs (posted in last 3 days)
    df_filtered = df.dropna(subset=["post_date"])
    threshold = now - timedelta(days=3)
    fresh = df_filtered[df_filtered["post_date"] >= threshold]

    return top20, remote, fresh


# -----------------------------------------------------------------------------
# Format Job Entry for Digest
# -----------------------------------------------------------------------------
def fmt(job):
    return (
        f"- **{job['title']}** at *{job['company']}*\n"
        f"  Location: {job['location']} | Score: {job['score']}\n"
        f"  URL: {job['url']}\n"
    )


# -----------------------------------------------------------------------------
# Generate Text Digest
# -----------------------------------------------------------------------------
def generate_text_digest(top20, remote, fresh, snapshot):
    text = []
    text.append(f"📊 JOB DIGEST — {snapshot}\n")
    text.append("=====================================\n\n")

    text.append("🔥 TOP 20 JOBS BY SCORE\n")
    text.append("-------------------------------------\n")
    for _, r in top20.iterrows():
        text.append(fmt(r))
    text.append("\n\n")

    text.append("🌎 REMOTE JOBS\n")
    text.append("-------------------------------------\n")
    for _, r in remote.iterrows():
        text.append(fmt(r))
    text.append("\n\n")

    text.append("🆕 FRESH JOBS (Last 3 days)\n")
    text.append("-------------------------------------\n")
    for _, r in fresh.iterrows():
        text.append(fmt(r))
    text.append("\n\n")

    return "".join(text)


# -----------------------------------------------------------------------------
# Generate HTML Digest
# -----------------------------------------------------------------------------
def generate_html_digest(top20, remote, fresh, snapshot):
    def block(title, df):
        items = "".join(
            f"""
            <li><b>{row['title']}</b> at {row['company']}<br>
            Location: {row['location']} | Score: {row['score']}<br>
            <a href="{row['url']}">Apply Link</a></li><br>
            """
            for _, row in df.iterrows()
        )
        return f"<h2>{title}</h2><ul>{items}</ul>"

    html = f"""
    <html>
    <body>
    <h1>📊 Job Digest — {snapshot}</h1>
    {block("🔥 Top 20 Jobs", top20)}
    {block("🌎 Remote Jobs", remote)}
    {block("🆕 Fresh Jobs (Last 3 Days)", fresh)}
    </body>
    </html>
    """
    return html


# -----------------------------------------------------------------------------
# Main Function
# -----------------------------------------------------------------------------
def generate_digest():
    print("📥 Loading Gold table...")
    df = load_gold()

    print("⚙️ Preparing digest sections...")
    top20, remote, fresh = create_digest_sections(df)

    snapshot = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    filename_ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # Generate text digest
    text_output = generate_text_digest(top20, remote, fresh, snapshot)
    text_path = DIGEST_DIR / f"digest_{filename_ts}.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text_output)

    # Generate HTML digest
    html_output = generate_html_digest(top20, remote, fresh, snapshot)
    html_path = DIGEST_DIR / f"digest_{filename_ts}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_output)

    print(f"📄 Digest TXT saved at: {text_path}")
    print(f"🌐 Digest HTML saved at: {html_path}")
    print("✅ Digest generation complete!")


# -----------------------------------------------------------------------------
# Run Script
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    generate_digest()
