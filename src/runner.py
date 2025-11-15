import traceback

from ingest_remoteok import fetch_remoteok
from ingest_remotive import fetch_remotive
from bronze_to_silver import normalize_all
from silver_to_gold import dedupe_and_score
from loader_to_snowflake import upload_gold_to_snowflake


def main():
    print("🚀 Starting Job Aggregation Pipeline...\n")

    try:
        # ---- BRONZE LAYER: RAW INGESTION ----
        print("📥 Fetching RemoteOK jobs...")
        fetch_remoteok()

        print("📥 Fetching Remotive jobs...")
        fetch_remotive()

        # ---- SILVER LAYER ----
        print("\n🔄 Converting Bronze → Silver...")
        normalize_all()

        # ---- GOLD LAYER ----
        print("\n🏆 Converting Silver → Gold...")
        dedupe_and_score()

        # ---- LOAD TO SNOWFLAKE ----
        print("\n❄️ Uploading Gold → Snowflake...")
        upload_gold_to_snowflake()

        print("\n✨ Pipeline completed successfully!")

    except Exception as e:
        print("\n❌ Pipeline failed!")
        print("Error:", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
