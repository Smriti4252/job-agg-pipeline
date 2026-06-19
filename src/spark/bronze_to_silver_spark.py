import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

from pyspark.sql import functions as F
from pyspark.sql.types import StringType, IntegerType, ArrayType

# Ensure src is on sys.path so module imports work when running the script directly
ROOT_SRC = Path(__file__).resolve().parents[1]
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from spark.spark_utils import get_spark_session


logger = logging.getLogger("bronze_to_silver_spark")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BRONZE_DIR = Path("data/bronze")
SILVER_DIR = Path("data/silver")
SILVER_DIR.mkdir(parents=True, exist_ok=True)


def normalize(df):
    # Add source detection if not present
    df = df.withColumn("_source", F.coalesce(F.col("_source"), F.lit("unknown")))

    def safe_col(name):
        return F.col(name) if name in df.columns else F.lit(None)

    # remote normalization: accept several truthy forms
    def remote_expr(col):
        return F.when((safe_col(col) == True) | (F.lower(safe_col(col).cast(StringType())) == "true") | (safe_col(col) == 1) | (safe_col(col) == "1"), F.lit(1)).otherwise(F.lit(0))

    # Common columns
    df = df.withColumn("job_id", F.coalesce(safe_col("id").cast(StringType()), safe_col("slug").cast(StringType())))
    df = df.withColumn("title", F.coalesce(safe_col("position"), safe_col("title")))
    df = df.withColumn("company", F.coalesce(safe_col("company"), safe_col("company_name")))
    df = df.withColumn("location", F.coalesce(safe_col("location"), safe_col("candidate_required_location")))
    df = df.withColumn("url", F.coalesce(safe_col("url"), safe_col("apply_url")))
    df = df.withColumn("description", F.coalesce(safe_col("description"), F.lit("")))
    df = df.withColumn("post_date", F.coalesce(safe_col("date"), safe_col("publication_date"), safe_col("publication_date")))
    df = df.withColumn("salary", safe_col("salary"))

    # tags: lists -> comma string
    df = df.withColumn("tags", F.when(safe_col("tags").isNull(), F.lit("")).otherwise(F.expr("array_join(tags, ', ')") ))

    # source-specific adjustments
    df = df.withColumn("remote_flag", F.when(F.col("_source") == "remotive", F.lit(1)).otherwise(remote_expr("remote")))

    # fetched_at: set now if missing
    now = datetime.now(timezone.utc).isoformat()
    df = df.withColumn("fetched_at", F.coalesce(safe_col("fetched_at"), F.lit(now)))

    # select and cast
    out = df.select(
        F.coalesce(F.col("job_id").cast(StringType()), F.lit("")).alias("job_id"),
        F.col("title").cast(StringType()).alias("title"),
        F.col("company").cast(StringType()).alias("company"),
        F.coalesce(F.col("location").cast(StringType()), F.lit("")).alias("location"),
        F.col("remote_flag").cast(IntegerType()).alias("remote"),
        F.coalesce(F.col("url").cast(StringType()), F.lit("")).alias("url"),
        F.col("description").cast(StringType()).alias("description"),
        F.col("post_date").cast(StringType()).alias("post_date"),
        F.col("fetched_at").cast(StringType()).alias("fetched_at"),
        F.col("salary").cast(StringType()).alias("salary"),
        F.col("tags").cast(StringType()).alias("tags"),
        F.col("_source").cast(StringType()).alias("source"),
    )

    return out


def run():
    spark = get_spark_session("bronze_to_silver")

    try:
        files = sorted(BRONZE_DIR.glob("*.json"))
        if not files:
            logger.info("No bronze JSON files found.")
            return 0

        paths = [str(p) for p in files]
        logger.info("Reading %d bronze files", len(paths))

        # Read all JSONs; some files contain arrays
        raw = spark.read.option("multiline", True).json(paths)

        # If a top-level array was read as a single array column, explode it
        array_field = None
        for f in raw.schema.fields:
            if isinstance(f.dataType, ArrayType):
                array_field = f.name
                break
        if array_field:
            raw = raw.select(F.explode(F.col(array_field)).alias("v")).select("v.*")

        # If file names contain source, add it
        raw = raw.withColumn("_input_file", F.input_file_name())
        raw = raw.withColumn("_filename", F.regexp_extract(F.col("_input_file"), "([^/\\\\]+$)", 1))

        # Native Spark expression instead of a Python UDF — avoids spawning
        # a separate python worker process (which fails on Windows since
        # Spark looks for "python3" by default).
        raw = raw.withColumn(
            "_source",
            F.when(F.lower(F.col("_filename")).contains("remoteok"), F.lit("remoteok"))
             .when(F.lower(F.col("_filename")).contains("remotive"), F.lit("remotive"))
             .when(F.lower(F.col("_filename")).contains("arbeit"), F.lit("arbeitnow"))
             .otherwise(F.lit("unknown"))
        )

        norm = normalize(raw)

        out_path = str(SILVER_DIR / "silver.parquet")
        logger.info("Writing silver parquet to %s", out_path)
        norm.write.mode("overwrite").parquet(out_path)

        logger.info("Bronze → Silver complete (rows: approx) %d", norm.count())
        return norm.count()

    except Exception as e:
        logger.exception("bronze_to_silver Spark job failed: %s", e)
        return 0
    finally:
        spark.stop()


if __name__ == "__main__":
    rc = run()
    sys.exit(0 if rc and rc > 0 else 1)