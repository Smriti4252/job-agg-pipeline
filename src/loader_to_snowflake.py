# This script picks up the latest Gold snapshot and pushes it into Snowflake.
# The logic is intentionally simple: load → stage → merge → clean up.

import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text


GOLD_DIR = Path("data/gold")


def _snowflake_engine():
    """Build a Snowflake engine based on environment variables."""

    user = os.getenv("SNOWFLAKE_USER")
    password = os.getenv("SNOWFLAKE_PASSWORD")
    account = os.getenv("SNOWFLAKE_ACCOUNT")

    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
    database = os.getenv("SNOWFLAKE_DATABASE")
    schema = os.getenv("SNOWFLAKE_SCHEMA")
    role = os.getenv("SNOWFLAKE_ROLE", "")

    required = [user, password, account, warehouse, database, schema]
    if not all(required):
        raise RuntimeError("Missing one or more Snowflake environment variables.")

    conn_str = (
        f"snowflake://{quote_plus(user)}:{quote_plus(password)}@{account}/"
        f"{database}/{schema}?warehouse={warehouse}&role={role}"
    )

    return create_engine(conn_str)


def upload_gold_to_snowflake():
    """Take the newest Gold CSV and merge it into the warehouse table."""

    csvs = sorted(GOLD_DIR.glob("gold_*.csv"))
    if not csvs:
        print("No Gold CSVs found in data/gold/.")
        return 0

    latest = csvs[-1]
    print(f"→ Using latest Gold snapshot: {latest}")

    df = pd.read_csv(latest)
    if df.empty:
        print("Gold CSV was empty — skipping upload.")
        return 0

    # Snowflake tables
    schema = os.getenv("SNOWFLAKE_SCHEMA")
    main_table = f"{schema}.GOLD_JOBS"
    stage_table = f"{schema}.GOLD_JOBS_STAGE"

    engine = _snowflake_engine()

    with engine.begin() as conn:
        # Pick environment context
        conn.execute(text(f"USE WAREHOUSE {os.getenv('SNOWFLAKE_WAREHOUSE')}"))
        conn.execute(text(f"USE DATABASE {os.getenv('SNOWFLAKE_DATABASE')}"))
        conn.execute(text(f"USE SCHEMA {schema}"))

        print("→ Creating staging table...")
        conn.execute(text(f"CREATE OR REPLACE TABLE {stage_table} LIKE {main_table}"))

        print("→ Loading rows into staging...")
        df.to_sql(
            name="GOLD_JOBS_STAGE",
            con=conn,
            schema=schema,
            index=False,
            if_exists="append",
        )

        print("→ Merging staging → main table...")
        merge_sql = f"""
        MERGE INTO {main_table} T
        USING {stage_table} S
            ON T.URL = S.URL

        WHEN MATCHED THEN UPDATE SET
            TITLE = S.TITLE,
            COMPANY = S.COMPANY,
            LOCATION = S.LOCATION,
            REMOTE = S.REMOTE,
            DESCRIPTION = S.DESCRIPTION,
            POST_DATE = S.POST_DATE,
            FETCHED_AT = S.FETCHED_AT,
            SALARY = S.SALARY,
            TAGS = S.TAGS,
            SCORE = S.SCORE,
            OUTREACH_MESSAGE = S.OUTREACH_MESSAGE

        WHEN NOT MATCHED THEN INSERT (
            JOB_ID, TITLE, COMPANY, LOCATION, REMOTE,
            URL, DESCRIPTION, POST_DATE, FETCHED_AT,
            SALARY, TAGS, SCORE, OUTREACH_MESSAGE
        ) VALUES (
            S.JOB_ID, S.TITLE, S.COMPANY, S.LOCATION, S.REMOTE,
            S.URL, S.DESCRIPTION, S.POST_DATE, S.FETCHED_AT,
            S.SALARY, S.TAGS, S.SCORE, S.OUTREACH_MESSAGE
        );
        """

        conn.execute(text(merge_sql))

        print("→ Cleaning up staging table...")
        conn.execute(text(f"DROP TABLE IF EXISTS {stage_table}"))

    print("✔ Gold layer successfully loaded into Snowflake.")
    return len(df)


if __name__ == "__main__":
    upload_gold_to_snowflake()
