#orchestrator to run pipeline steps in sequence.

import traceback

from ingest_remoteok import run as run_remoteok
from ingest_remotive import run as run_remotive
from bronze_to_silver import normalize_and_write as bronze_to_silver
from silver_to_gold import run as silver_to_gold
from loader_to_snowflake import upload_gold_to_snowflake  # optional if configured


def main():
    print("🚀 Starting Job Aggregation Pipeline\n")

    try:
        print("📥 Step 1: Ingest RemoteOK")
        run_remoteok()

        print("📥 Step 2: Ingest Remotive")
        run_remotive()

        print("\n🔄 Step 3: Bronze → Silver (normalize)")
        bronze_to_silver()

        print("\n🏆 Step 4: Silver → Gold (dedupe & score)")
        silver_to_gold()

        print("\n❄️ Step 5: (optional) Push Gold to Snowflake")
        try:
            upload_gold_to_snowflake()
        except Exception as e:
            print("   Skipping Snowflake upload (not configured or failed):", e)

        print("\n✨ Pipeline finished successfully.")
    except Exception as exc:
        print("\n❌ Pipeline failed:")
        traceback.print_exc()


if __name__ == "__main__":
    main()
