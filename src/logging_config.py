# logging_config.py
# Centralized logging setup used across the pipeline.
# Logs go to both console and a timestamped file under logs/.

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging(name: str = "job_agg_pipeline", level=logging.INFO) -> logging.Logger:
    """Configure a logger that writes to console and a per-run log file.

    Safe to call multiple times (e.g. once per module) — it will not
    duplicate handlers on the root logger.
    """
    log_filename = f"{name}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    log_path = LOGS_DIR / log_filename

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    # Avoid attaching duplicate handlers if setup_logging() is called again
    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(fmt)
        root_logger.addHandler(console_handler)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(fmt)
        root_logger.addHandler(file_handler)

    logger = logging.getLogger(name)
    logger.info("Logging initialized. Log file: %s", log_path)
    return logger