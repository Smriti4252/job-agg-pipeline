import os
import sys
from pyspark.sql import SparkSession


def get_spark_session(app_name: str = "job_agg_spark") -> SparkSession:
    """Create or return a SparkSession configured for local development.

    Configuration is conservative for a developer laptop.
    """
    # Ensure Spark uses the current venv's python.exe instead of looking
    # for "python3", which doesn't exist on Windows by default.
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    builder = SparkSession.builder.master("local[*]").appName(app_name)
    builder = builder.config("spark.sql.shuffle.partitions", "4")
    builder = builder.config("spark.driver.bindAddress", "127.0.0.1")
    return builder.getOrCreate()