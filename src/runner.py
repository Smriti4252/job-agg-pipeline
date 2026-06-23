# runner.py
# Orchestrator: runs the full pipeline in sequence
# Ingest -> Bronze -> Silver (PySpark) -> Gold (dbt run + test)

import subprocess
import sys
from pathlib import Path

from logging_config import setup_logging
from ingest_remoteok import run as run_remoteok
from ingest_remotive import run as run_remotive
from spark.bronze_to_silver_spark import run as run_bronze_to_silver

logger = setup_logging("runner")

ROOT_DIR = Path(__file__).resolve().parents[1]   # job-agg-pipeline root
DBT_PROJECT_DIR = ROOT_DIR / "dbt_project"
DBT_EXE = str(Path(sys.executable).parent / "dbt.exe")


def run_dbt(target: str = "duck_local"):
    """Run dbt build + tests as a subprocess inside the dbt project directory."""
    run_cmd = [DBT_EXE, "run", "--target", target]
    logger.info("Running: %s (cwd=%s)", " ".join(run_cmd), DBT_PROJECT_DIR)
    result = subprocess.run(run_cmd, cwd=str(DBT_PROJECT_DIR), capture_output=True, text=True)
    logger.info(result.stdout)
    if result.returncode != 0:
        logger.error(result.stderr)
        raise RuntimeError("dbt run failed")

    test_cmd = [DBT_EXE, "test", "--target", target]
    logger.info("Running: %s", " ".join(test_cmd))
    test_result = subprocess.run(test_cmd, cwd=str(DBT_PROJECT_DIR), capture_output=True, text=True)
    logger.info(test_result.stdout)
    if test_result.returncode != 0:
        logger.error(test_result.stderr)
        raise RuntimeError("dbt test failed")


def main():
    logger.info("Starting Job Aggregation Pipeline")
    try:
        logger.info("Step 1: Ingest RemoteOK")
        run_remoteok()

        logger.info("Step 2: Ingest Remotive")
        run_remotive()

        logger.info("Step 3: Bronze -> Silver (PySpark normalize)")
        rows = run_bronze_to_silver()
        logger.info("Silver layer written: %s rows", rows)

        if not rows or rows == 0:
            raise RuntimeError("Silver layer wrote 0 rows — aborting before gold layer.")

        logger.info("Step 4: Silver -> Gold (dbt run + test)")
        run_dbt(target="duck_local")

        logger.info("Pipeline finished successfully.")

    except Exception:
        logger.exception("Pipeline failed")
        raise


if __name__ == "__main__":
    main()