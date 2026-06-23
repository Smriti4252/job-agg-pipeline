# Job Aggregation Pipeline

A production-style data engineering pipeline that ingests remote job postings from multiple APIs, transforms them through a Bronze → Silver → Gold architecture using PySpark and dbt, and orchestrates daily runs via Apache Airflow.

---

## Architecture

```mermaid
flowchart LR
    A([RemoteOK API]) --> C[Bronze Layer\nRaw JSON]
    B([Remotive API]) --> C
    C --> D[PySpark ETL\nbronze_to_silver_spark.py]
    D --> E[Silver Layer\nParquet - 1500+ rows]
    E --> F[dbt Models\nDuckDB]
    F --> G[Gold Layer\ngold_jobs + job_metrics]
    G --> H([Analytics-Ready\nDeduped + Scored])

    subgraph Orchestration
        I[Apache Airflow\nDocker + LocalExecutor]
    end

    I -.->|@daily schedule| C
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Ingestion | Python, Requests |
| Bronze | JSON files + SQLite |
| Transformation | PySpark 4.1.2 |
| Storage | Parquet (Silver), DuckDB (Gold) |
| Modeling | dbt-duckdb 1.10.1 |
| Orchestration | Apache Airflow 2.10.4 (Docker) |
| CI/CD | GitHub Actions |
| Containerization | Docker Compose |

---

## Pipeline Steps

```
1. Ingest        → Fetch jobs from RemoteOK + Remotive APIs in parallel
2. Bronze        → Save raw JSON to data/bronze/
3. Silver        → PySpark normalizes, deduplicates, writes Parquet
4. Gold (dbt)    → SQL models: stg_jobs → gold_jobs → job_metrics
5. dbt test      → Data quality checks (not_null, unique)
```

---

## Project Structure

```
job-agg-pipeline/
├── src/
│   ├── ingest_remoteok.py        # RemoteOK API ingestion
│   ├── ingest_remotive.py        # Remotive API ingestion
│   ├── runner.py                 # Pipeline orchestrator (manual)
│   ├── logging_config.py         # Centralized logging
│   └── spark/
│       ├── bronze_to_silver_spark.py  # PySpark ETL
│       └── spark_utils.py             # SparkSession config
├── dbt_project/
│   ├── models/
│   │   ├── staging/
│   │   │   └── stg_jobs.sql      # Normalize silver parquet
│   │   └── gold/
│   │       ├── gold_jobs.sql     # Dedup + scoring logic
│   │       └── job_metrics.sql   # Aggregated analytics
│   ├── dbt_project.yml
│   └── profiles.yml
├── airflow/
│   ├── dags/
│   │   └── job_agg_dag.py        # Airflow DAG (5 tasks)
│   ├── Dockerfile                # Custom image: Airflow + Java + PySpark + dbt
│   └── docker-compose.yaml       # LocalExecutor setup
├── data/
│   ├── bronze/                   # Raw JSON files
│   ├── silver/                   # Parquet output
│   └── duckdb_local.db           # DuckDB warehouse
├── logs/                         # Pipeline run logs
└── .github/workflows/            # CI/CD
```

---

## Setup

### Prerequisites
- Python 3.11+
- Java 17 (for PySpark)
- Docker Desktop
- Git

### Local Setup

```bash
git clone https://github.com/yourusername/job-agg-pipeline.git
cd job-agg-pipeline
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Run Pipeline Manually

```bash
cd src
python runner.py
```

### Run via Airflow (Docker)

```bash
cd airflow
docker compose up airflow-init
docker compose up -d
```

Then open `http://localhost:8080` (login: `airflow` / `airflow`) and trigger `job_aggregation_pipeline`.

---

## dbt Models

| Model | Type | Description |
|---|---|---|
| `stg_jobs` | View | Reads silver parquet, normalizes columns |
| `gold_jobs` | Table | Deduplicates by URL, scores jobs by skill match |
| `job_metrics` | Table | Aggregated stats: total jobs, companies, remote % |

### Scoring Logic

Jobs are scored based on:
- **+2.0** — Junior / entry-level / fresher / intern titles
- **+1.0** — Remote position
- **+0.5 each** — Skill keywords matched: `etl`, `sql`, `python`, `dbt`, `snowflake`, `spark`

---

## Airflow DAG

```
ingest_remoteok ─┐
                  ├──→ bronze_to_silver ──→ dbt_run ──→ dbt_test
ingest_remotive ─┘
```

- **Schedule:** `@daily`
- **Executor:** LocalExecutor (Docker)
- **Retries:** 1 per task, 2 min delay
- Both ingestion tasks run in **parallel**

---

## Key Engineering Decisions

**Why PySpark for Bronze→Silver?**
Handles schema evolution across multiple JSON sources with different field names (RemoteOK vs Remotive). Native Spark expressions used instead of Python UDFs to avoid Windows `python3` path issues in executor processes.

**Why dbt + DuckDB locally?**
Zero-setup analytical warehouse — DuckDB reads Parquet directly. Same dbt models are portable to Snowflake by switching `--target dev` (Snowflake profile already configured in `profiles.yml`).

**Why Airflow over cron?**
Visual DAG graph, per-task retry logic, execution history, and easy migration path to managed Airflow (MWAA/Cloud Composer) for production.

---

## Data Quality

dbt tests run automatically after every gold layer build:

| Test | Column | Model |
|---|---|---|
| `not_null` | `job_id` | `gold_jobs` |
| `not_null` | `title` | `gold_jobs` |
| `unique` | `url` | `gold_jobs` |

---

## Author

**Smriti Sharma** — Data Engineer
[LinkedIn](#) · [GitHub](#)