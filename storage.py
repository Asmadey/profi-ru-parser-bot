import json
import logging
import os
import time
from typing import Iterable

logger = logging.getLogger("parser.storage")


def load_seen_ids(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning("seen_ids.json corrupted: %s. Backing up and resetting.", e)
        backup = f"{path}.corrupted.{int(time.time())}"
        try:
            os.rename(path, backup)
            logger.warning("Corrupted file backed up to %s", backup)
        except OSError:
            logger.error("Failed to backup corrupted seen_ids.json")
        return set()

    if isinstance(data, dict):
        data = data.get("ids", [])
    if not isinstance(data, (list, tuple, set)):
        logger.warning("seen_ids.json has unexpected type: %s. Resetting.", type(data).__name__)
        return set()

    return set(str(x) for x in data if x)


def save_seen_ids(path: str, ids: set[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f, ensure_ascii=False, indent=2)


def append_jsonl(path: str, obj: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
