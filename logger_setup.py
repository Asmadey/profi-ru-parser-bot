import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """JSON log formatter for machine-parseable logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(
    name: str,
    log_dir: str = "logs",
    level: int = logging.INFO,
    max_bytes: int = 2_000_000,   # ~2MB
    backup_count: int = 5,
) -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # не плодим хэндлеры при повторном импорте
    if logger.handlers:
        return logger

    use_json = os.getenv("LOG_FORMAT", "").lower() == "json"
    fmt = JsonFormatter() if use_json else logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # console
    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # all logs
    fh = RotatingFileHandler(
        os.path.join(log_dir, f"{name}.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # error logs only
    eh = RotatingFileHandler(
        os.path.join(log_dir, f"{name}.error.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    eh.setLevel(logging.ERROR)
    eh.setFormatter(fmt)
    logger.addHandler(eh)

    return logger


def log_json(logger: logging.Logger, prefix: str, payload: Dict[str, Any], level: int = logging.INFO) -> None:
    try:
        logger.log(level, "%s | %s", prefix, json.dumps(payload, ensure_ascii=False))
    except Exception:
        logger.log(level, "%s | <json_dump_failed>", prefix)
