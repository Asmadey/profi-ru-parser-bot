"""Data-retention cleanup utilities for the Profi.ru Parser Bot.

Provides:
  * cleanup_debug_screenshots — delete stale debug screenshots/HTML dumps.
  * trim_jsonl                — keep only the last N lines of a JSONL log.
  * run_cleanup               — run both and report a summary dict.

All functions use only the Python standard library and never raise:
on any error they log via ``logging`` and return a safe value (0 / {}).
"""

from __future__ import annotations

import logging
import os
import tempfile
import time

log = logging.getLogger(__name__)
if not log.handlers:
    logging.basicConfig(level=logging.INFO)


# --------------------------------------------------------------------------- #
# Debug screenshots
# --------------------------------------------------------------------------- #
def cleanup_debug_screenshots(debug_dir: str = "logs/debug", max_age_days: int = 7) -> int:
    """Delete files in *debug_dir* older than *max_age_days*.

    Returns the number of files actually deleted.  Never raises.
    """
    deleted = 0
    try:
        if not os.path.isdir(debug_dir):
            return 0

        cutoff = time.time() - max_age_days * 86400

        for entry in os.listdir(debug_dir):
            path = os.path.join(debug_dir, entry)
            try:
                if not os.path.isfile(path):
                    continue
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    deleted += 1
            except Exception as exc:  # noqa: BLE001
                log.warning("cleanup: cannot remove %s: %s", path, exc)
    except Exception as exc:  # noqa: BLE001
        log.warning("cleanup_debug_screenshots failed: %s", exc)
    return deleted


# --------------------------------------------------------------------------- #
# JSONL trimming
# --------------------------------------------------------------------------- #
def trim_jsonl(path: str = "new_orders.jsonl", max_lines: int = 10000) -> int:
    """Trim *path* to the last *max_lines* lines.

    Returns the number of lines removed (0 if the file was already small
    enough, missing, or unreadable).  The rewrite is atomic: a temp file is
    written in the same directory and then ``os.replace``-d over the original.
    Never raises.
    """
    try:
        if not os.path.isfile(path):
            return 0

        # Read all lines once.  jsonl files are typically small enough for this;
        # if they aren't, the trim itself is the remedy.
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total = len(lines)
        if total <= max_lines:
            return 0

        keep = lines[-max_lines:]
        removed = total - max_lines

        directory = os.path.dirname(os.path.abspath(path)) or "."
        fd, tmp_path = tempfile.mkstemp(
            prefix=".trim_", suffix=".tmp", dir=directory
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.writelines(keep)
            # Preserve original permissions where possible.
            try:
                st = os.stat(path)
                os.chmod(tmp_path, st.st_mode & 0o7777)
            except Exception:  # noqa: BLE001
                pass
            os.replace(tmp_path, path)
        except Exception:
            # Clean up the temp file if the replace failed.
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise

        log.info("trim_jsonl: removed %d lines from %s", removed, path)
        return removed
    except Exception as exc:  # noqa: BLE001
        log.warning("trim_jsonl failed for %s: %s", path, exc)
        return 0


# --------------------------------------------------------------------------- #
# Combined entry point
# --------------------------------------------------------------------------- #
def run_cleanup(
    debug_dir: str = "logs/debug",
    max_age_days: int = 7,
    jsonl_path: str = "new_orders.jsonl",
    max_lines: int = 10000,
) -> dict:
    """Run screenshot cleanup and JSONL trimming.

    Returns a dict::

        {"files_deleted": <int>, "lines_trimmed": <int>}

    Never raises.
    """
    files_deleted = cleanup_debug_screenshots(debug_dir, max_age_days)
    lines_trimmed = trim_jsonl(jsonl_path, max_lines)
    result = {"files_deleted": files_deleted, "lines_trimmed": lines_trimmed}
    log.info("run_cleanup: %s", result)
    return result


if __name__ == "__main__":
    print(run_cleanup())