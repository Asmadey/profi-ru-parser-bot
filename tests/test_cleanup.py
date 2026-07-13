"""Unit tests for cleanup.py."""

import os
import sys
import time

import pytest

# Make the project root importable when tests are run from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cleanup import cleanup_debug_screenshots, trim_jsonl, run_cleanup  # noqa: E402

OLD_AGE_DAYS = 30


def _make_old_file(path, age_days=OLD_AGE_DAYS):
    """Create a file and set its mtime to *age_days* in the past."""
    path.write_text("old", encoding="utf-8")
    old_ts = time.time() - age_days * 86400
    os.utime(str(path), (old_ts, old_ts))


# ---------------------------------------------------------------------------
# cleanup_debug_screenshots
# ---------------------------------------------------------------------------
def test_cleanup_debug_screenshots_deletes_old(tmp_path):
    debug_dir = tmp_path / "debug"
    debug_dir.mkdir()
    old_file = debug_dir / "old.png"
    new_file = debug_dir / "new.png"
    sub_dir = debug_dir / "subdir"
    sub_dir.mkdir()

    _make_old_file(old_file)
    new_file.write_text("new", encoding="utf-8")

    deleted = cleanup_debug_screenshots(str(debug_dir), max_age_days=7)
    assert deleted == 1
    assert not old_file.exists()
    assert new_file.exists()
    # Directories should be left untouched.
    assert sub_dir.exists()


def test_cleanup_debug_screenshots_nonexistent_dir(tmp_path):
    missing = tmp_path / "does_not_exist"
    assert cleanup_debug_screenshots(str(missing), max_age_days=7) == 0


def test_cleanup_debug_screenshots_empty_dir(tmp_path):
    debug_dir = tmp_path / "debug"
    debug_dir.mkdir()
    assert cleanup_debug_screenshots(str(debug_dir), max_age_days=7) == 0


# ---------------------------------------------------------------------------
# trim_jsonl
# ---------------------------------------------------------------------------
def test_trim_jsonl_removes_excess(tmp_path):
    path = tmp_path / "orders.jsonl"
    lines = [f'{{"i": {i}}}\n' for i in range(15)]
    path.write_text("".join(lines), encoding="utf-8")

    removed = trim_jsonl(str(path), max_lines=10)
    assert removed == 5

    remaining = path.read_text(encoding="utf-8").splitlines()
    assert len(remaining) == 10
    # The last 10 lines should be indices 5..14
    import json as _json
    expected = [_json.loads(l) for l in lines[-10:]]
    actual = [_json.loads(l) for l in remaining]
    assert actual == expected


def test_trim_jsonl_under_limit(tmp_path):
    path = tmp_path / "orders.jsonl"
    path.write_text('{"a": 1}\n' * 5, encoding="utf-8")
    assert trim_jsonl(str(path), max_lines=10) == 0
    assert len(path.read_text(encoding="utf-8").splitlines()) == 5


def test_trim_jsonl_nonexistent_file(tmp_path):
    path = tmp_path / "nope.jsonl"
    assert trim_jsonl(str(path), max_lines=10) == 0


# ---------------------------------------------------------------------------
# run_cleanup
# ---------------------------------------------------------------------------
def test_run_cleanup(tmp_path):
    debug_dir = tmp_path / "debug"
    debug_dir.mkdir()
    old_file = debug_dir / "old.png"
    _make_old_file(old_file)

    jsonl_path = tmp_path / "orders.jsonl"
    jsonl_path.write_text('{"i": 1}\n' * 15, encoding="utf-8")

    result = run_cleanup(
        debug_dir=str(debug_dir),
        max_age_days=7,
        jsonl_path=str(jsonl_path),
        max_lines=10,
    )
    assert result == {"files_deleted": 1, "lines_trimmed": 5}
    assert not old_file.exists()
    assert len(jsonl_path.read_text(encoding="utf-8").splitlines()) == 10