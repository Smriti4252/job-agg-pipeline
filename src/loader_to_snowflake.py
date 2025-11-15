# import os
# import pandas as pd
# from sqlalchemy import create_engine, text
# from urllib.parse import quote_plus
# from pathlib import Path

# GOLD_DIR = Path("data/gold")


# def get_snowflake_engine():
#     """
#     Create a Snowflake SQLAlchemy engine using environment variables.
#     """

#     user = os.getenv("SNOWFLAKE_USER")
#     password = os.getenv("SNOWFLAKE_PASSWORD")
#     account = os.getenv("SNOWFLAKE_ACCOUNT")
#     warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
#     database = os.getenv("SNOWFLAKE_DATABASE")
#     schema = os.getenv("SNOWFLAKE_SCHEMA")
#     role = os.getenv("SNOWFLAKE_ROLE", "")

#     # Validate that mandatory variables exist
#     if not all([user, password, account, warehouse, database, schema]):
#         raise Exception("Snowflake environment variables are missing.")

#     # Format: snowflake://user:pass@account/database/schema?warehouse=...&role=...
#     engine_url = (
#         f"snowflake://{quote_plus(user)}:{quote_plus(password)}@{account}/"
#         f"{database}/{schema}?warehouse={warehouse}&role={role}"
#     )

#     engine = create_engine(engine_url)
#     return engine


# def upload_gold_to_snowflake():
#     """
#     Upload the latest Gold CSV snapshot into Snowflake.
#     """

#     # Find latest gold CSV file
#     csv_files = sorted(GOLD_DIR.glob("gold_*.csv"))
#     if not csv_files:
#         print("❌ No Gold CSV files found.")
#         return 0

#     latest_csv = csv_files[-1]
#     print(f"📄 Latest Gold file: {latest_csv}")

#     # Load CSV into DataFrame
#     df = pd.read_csv(latest_csv)
#     if df.empty:
#         print("❌ Gold CSV is empty.")
#         return 0

#     # Rename columns to match Snowflake table schema
#     df = df.rename(
#         columns={
#             "external_id": "JOB_ID",
#             "title": "TITLE",
#             "company": "COMPANY",
#             "location": "LOCATION",
#             "remote": "REMOTE",
#             "url": "URL",
#             "description": "DESCRIPTION",
#             "post_date": "POST_DATE",
#             "fetched_at": "FETCHED_AT",
#             "salary": "SALARY",
#             "tags": "TAGS",
#             "score": "SCORE",
#             "outreach_message": "OUTREACH_MESSAGE",
#         }
#     )

#     # Connect to Snowflake
#     engine = get_snowflake_engine()
#     target_table = "GOLD.GOLD_JOBS"
#     temp_table = "GOLD.GOLD_JOBS_STAGE"

#     with engine.begin() as conn:

#         # -------------------------------
#         # ✅ FIX: Always select DB + schema
#         # -------------------------------
#         conn.execute(text(f"USE DATABASE {os.getenv('SNOWFLAKE_DATABASE')};"))
#         conn.execute(text(f"USE SCHEMA {os.getenv('SNOWFLAKE_SCHEMA')};"))

#         print("🧱 Creating temporary stage table...")
#         conn.execute(text(f"CREATE OR REPLACE TABLE {temp_table} LIKE {target_table};"))

#         print("⬆️ Uploading data into stage table...")
#         df.to_sql(
#             name=temp_table.split(".")[-1],
#             con=conn,
#             schema="GOLD",
#             index=False,
#             if_exists="append",
#         )

#         print("🔄 Merging into main table...")

#         merge_sql = f"""
#         MERGE INTO {target_table} T
#         USING {temp_table} S
#         ON T.URL = S.URL

#         WHEN MATCHED THEN UPDATE SET
#             T.TITLE = S.TITLE,
#             T.COMPANY = S.COMPANY,
#             T.LOCATION = S.LOCATION,
#             T.REMOTE = S.REMOTE,
#             T.DESCRIPTION = S.DESCRIPTION,
#             T.POST_DATE = S.POST_DATE,
#             T.FETCHED_AT = S.FETCHED_AT,
#             T.SALARY = S.SALARY,
#             T.TAGS = S.TAGS,
#             T.SCORE = S.SCORE,
#             T.OUTREACH_MESSAGE = S.OUTREACH_MESSAGE

#         WHEN NOT MATCHED THEN INSERT (
#             JOB_ID, TITLE, COMPANY, LOCATION, REMOTE, URL, DESCRIPTION,
#             POST_DATE, FETCHED_AT, SALARY, TAGS, SCORE, OUTREACH_MESSAGE
#         )
#         VALUES (
#             S.JOB_ID, S.TITLE, S.COMPANY, S.LOCATION, S.REMOTE, S.URL, S.DESCRIPTION,
#             S.POST_DATE, S.FETCHED_AT, S.SALARY, S.TAGS, S.SCORE, S.OUTREACH_MESSAGE
#         );
#         """

#         conn.execute(text(merge_sql))

#         print("🧹 Dropping stage table...")
#         conn.execute(text(f"DROP TABLE IF EXISTS {temp_table}"))

#     print("✅ Gold data successfully uploaded to Snowflake!")
#     return len(df)


# if __name__ == "__main__":
#     upload_gold_to_snowflake()




import os
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from pathlib import Path


GOLD_DIR = Path("data/gold")


def get_snowflake_engine():
    """
    Create a Snowflake SQLAlchemy engine using env variables
    """
    user = os.getenv("SNOWFLAKE_USER")
    password = os.getenv("SNOWFLAKE_PASSWORD")
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
    database = os.getenv("SNOWFLAKE_DATABASE")
    schema = os.getenv("SNOWFLAKE_SCHEMA")
    role = os.getenv("SNOWFLAKE_ROLE", "")

    if not all([user, password, account, warehouse, database, schema]):
        raise Exception("❌ Missing required Snowflake environment variables.")

    engine_url = (
        f"snowflake://{quote_plus(user)}:{quote_plus(password)}@{account}/"
        f"{database}/{schema}?warehouse={warehouse}&role={role}"
    )

    return create_engine(engine_url)


def upload_gold_to_snowflake():
    """
    Upload the latest Gold CSV → Snowflake (MERGE logic)
    """

    csv_files = sorted(GOLD_DIR.glob("gold_*.csv"))
    if not csv_files:
        print("❌ No Gold CSV found.")
        return 0

    latest_csv = csv_files[-1]
    print(f"📄 Loading Gold file: {latest_csv}")

    df = pd.read_csv(latest_csv)
    if df.empty:
        print("❌ Gold file is empty.")
        return 0

    # Snowflake table naming
    target_table = f"{os.getenv('SNOWFLAKE_SCHEMA')}.GOLD_JOBS"
    temp_table = f"{os.getenv('SNOWFLAKE_SCHEMA')}.GOLD_JOBS_STAGE"

    engine = get_snowflake_engine()

    with engine.begin() as conn:

        print("🧭 Selecting warehouse/database/schema...")
        conn.execute(text(f"USE WAREHOUSE {os.getenv('SNOWFLAKE_WAREHOUSE')};"))
        conn.execute(text(f"USE DATABASE {os.getenv('SNOWFLAKE_DATABASE')};"))
        conn.execute(text(f"USE SCHEMA {os.getenv('SNOWFLAKE_SCHEMA')};"))

        print("🧱 Creating temporary staging table...")
        conn.execute(text(f"CREATE OR REPLACE TABLE {temp_table} LIKE {target_table};"))

        print("⬆️ Uploading into stage table...")
        df.to_sql(
            name="GOLD_JOBS_STAGE",
            con=conn,
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            index=False,
            if_exists="append",
        )

        print("🔄 Merging stage → production...")
        merge_sql = f"""
        MERGE INTO {target_table} T
        USING {temp_table} S
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

        WHEN NOT MATCHED THEN INSERT VALUES (
            S.JOB_ID, S.TITLE, S.COMPANY, S.LOCATION, S.REMOTE,
            S.URL, S.DESCRIPTION, S.POST_DATE, S.FETCHED_AT,
            S.SALARY, S.TAGS, S.SCORE, S.OUTREACH_MESSAGE
        );
        """
        conn.execute(text(merge_sql))

        print("🧹 Dropping stage table...")
        conn.execute(text(f"DROP TABLE IF EXISTS {temp_table};"))

    print("✅ Gold successfully uploaded to Snowflake!")
    return len(df)


if __name__ == "__main__":
    upload_gold_to_snowflake()
