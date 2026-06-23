# job_agg_dag.py
# Airflow DAG that orchestrates the Job Aggregation Pipeline:
# Ingest (RemoteOK, Remotive) -> Bronze -> Silver (PySpark) -> Gold (dbt run + test)
#
# This mirrors src/runner.py but lets Airflow handle scheduling,
# retries, and dependency visualization instead of a manual script.

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

# All project code (src/, dbt_project/) is mounted into the container at
# /opt/airflow/project via the docker-compose.yaml volume mapping.
PROJECT_DIR = "/opt/airflow/project"
SRC_DIR = f"{PROJECT_DIR}/src"
DBT_DIR = f"{PROJECT_DIR}/dbt_project"

default_args = {
    "owner": "memri",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="job_aggregation_pipeline",
    description="Ingest -> Bronze -> Silver (PySpark) -> Gold (dbt)",
    default_args=default_args,
    schedule="@daily",          # runs once a day; change to None for manual-only
    start_date=datetime(2026, 6, 1),
    catchup=False,
    tags=["job-pipeline", "spark", "dbt"],
) as dag:

    ingest_remoteok = BashOperator(
        task_id="ingest_remoteok",
        bash_command=f"cd {SRC_DIR} && python -c \"from ingest_remoteok import run; run()\"",
    )

    ingest_remotive = BashOperator(
        task_id="ingest_remotive",
        bash_command=f"cd {SRC_DIR} && python -c \"from ingest_remotive import run; run()\"",
    )

    bronze_to_silver = BashOperator(
        task_id="bronze_to_silver",
        bash_command=f"cd {SRC_DIR} && python -c \"from spark.bronze_to_silver_spark import run; run()\"",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run --target duck_local",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --target duck_local",
    )

    # Dependency graph: both ingests run in parallel, then silver, then dbt
    [ingest_remoteok, ingest_remotive] >> bronze_to_silver >> dbt_run >> dbt_test