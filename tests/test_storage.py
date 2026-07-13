"""Unit tests for storage.py."""

import json
import os
import sys
import time

import pytest

# Make the project root importable when tests are run from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage import load_seen_ids, save_seen_ids, append_jsonl  # noqa: E402


# ---------------------------------------------------------------------------
# load_seen_ids
# ---------------------------------------------------------------------------
def test_load_seen_ids_nonexistent_path(tmp_path):
    """A missing file should yield an empty set."""
    path = tmp_path / "seen_ids.json"
    assert load_seen_ids(str(path)) == set()


def test_load_seen_ids_valid_list(tmp_path):
    """A JSON list should be returned as a set of strings."""
    path = tmp_path / "seen_ids.json"
    path.write_text('["a", "b", "c"]', encoding="utf-8")
    assert load_seen_ids(str(path)) == {"a", "b", "c"}


def test_load_seen_ids_dict_with_ids(tmp_path):
    """A dict with an 'ids' key should extract the list under 'ids'."""
    path = tmp_path / "seen_ids.json"
    path.write_text('{"ids": ["x", "y"]}', encoding="utf-8")
    assert load_seen_ids(str(path)) == {"x", "y"}


def test_load_seen_ids_corrupted_json(tmp_path):
    """Corrupted JSON should return an empty set and create a backup file."""
    path = tmp_path / "seen_ids.json"
    path.write_text("{not valid json", encoding="utf-8")
    result = load_seen_ids(str(path))
    assert result == set()
    # A backup file starting with the original name should now exist.
    backups = [f for f in os.listdir(str(tmp_path)) if f.startswith("seen_ids.json.corrupted.")]
    assert len(backups) == 1


def test_load_seen_ids_empty_file(tmp_path):
    """An empty file is not valid JSON and should yield an empty set."""
    path = tmp_path / "seen_ids.json"
    path.write_text("", encoding="utf-8")
    assert load_seen_ids(str(path)) == set()


# ---------------------------------------------------------------------------
# save_seen_ids
# ---------------------------------------------------------------------------
def test_save_seen_ids_sorted(tmp_path):
    """save_seen_ids should write a sorted JSON array."""
    path = tmp_path / "seen_ids.json"
    ids = {"c", "a", "b"}
    save_seen_ids(str(path), ids)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# append_jsonl
# ---------------------------------------------------------------------------
def test_append_jsonl(tmp_path):
    """Append three objects, verify three lines, each valid JSON, trailing newline."""
    path = tmp_path / "orders.jsonl"
    objs = [{"id": 1, "name": "alpha"},
            {"id": 2, "name": "beta"},
            {"id": 3, "name": "gamma"}]
    for obj in objs:
        append_jsonl(str(path), obj)

    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")
    # Trailing newline → last element is an empty string.
    assert lines[-1] == ""
    json_lines = lines[:-1]
    assert len(json_lines) == 3
    for line, original in zip(json_lines, objs):
        assert json.loads(line) == original


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------
def test_save_load_round_trip(tmp_path):
    """save → load should preserve the set."""
    path = tmp_path / "seen_ids.json"
    ids = {"order_1", "order_2", "order_3"}
    save_seen_ids(str(path), ids)
    loaded = load_seen_ids(str(path))
    assert loaded == ids