"""Unit tests for metrics.py."""

import json
import os
import sys
import time

import pytest

# Make the project root importable when tests are run from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from metrics import Metrics, COUNTERS  # noqa: E402


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------
def test_metrics_init():
    m = Metrics()
    for name in COUNTERS:
        if name == "start_time":
            assert abs(m.get(name) - time.time()) < 5
        else:
            assert m.get(name) == 0


# ---------------------------------------------------------------------------
# inc
# ---------------------------------------------------------------------------
def test_metrics_inc_default():
    m = Metrics()
    m.inc("orders_parsed")
    assert m.get("orders_parsed") == 1


def test_metrics_inc_by_value():
    m = Metrics()
    m.inc("orders_sent", 5)
    assert m.get("orders_sent") == 5
    m.inc("orders_sent", 3)
    assert m.get("orders_sent") == 8


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------
def test_metrics_set():
    m = Metrics()
    m.set("orders_matched", 42)
    assert m.get("orders_matched") == 42


# ---------------------------------------------------------------------------
# get with default
# ---------------------------------------------------------------------------
def test_metrics_get_default():
    m = Metrics()
    assert m.get("nonexistent", default=99) == 99


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------
def test_metrics_to_dict_uptime():
    m = Metrics()
    time.sleep(0.05)
    d = m.to_dict()
    assert "uptime" in d
    assert d["uptime"] > 0


# ---------------------------------------------------------------------------
# save + load round-trip
# ---------------------------------------------------------------------------
def test_metrics_save_load_round_trip(tmp_path):
    m = Metrics()
    m.inc("orders_parsed", 10)
    m.set("orders_matched", 5)
    m.set("last_poll_time", 1234567890)

    path = tmp_path / "metrics.json"
    m.save(str(path))

    m2 = Metrics()
    m2.load(str(path))
    assert m2.get("orders_parsed") == 10
    assert m2.get("orders_matched") == 5
    assert m2.get("last_poll_time") == 1234567890


# ---------------------------------------------------------------------------
# KeyError on unknown metric
# ---------------------------------------------------------------------------
def test_metrics_inc_unknown_raises():
    m = Metrics()
    with pytest.raises(KeyError):
        m.inc("bogus")


def test_metrics_set_unknown_raises():
    m = Metrics()
    with pytest.raises(KeyError):
        m.set("bogus", 1)


def test_metrics_setitem_unknown_raises():
    m = Metrics()
    with pytest.raises(KeyError):
        m["bogus"] = 1


# ---------------------------------------------------------------------------
# __getitem__ / __contains__
# ---------------------------------------------------------------------------
def test_metrics_getitem():
    m = Metrics()
    m.set("orders_parsed", 7)
    assert m["orders_parsed"] == 7


def test_metrics_contains():
    m = Metrics()
    assert "orders_parsed" in m
    assert "bogus" not in m


# ---------------------------------------------------------------------------
# load edge cases
# ---------------------------------------------------------------------------
def test_metrics_load_missing_file(tmp_path):
    """Loading a missing file should leave metrics unchanged."""
    m = Metrics()
    before = dict(m._data)
    m.load(str(tmp_path / "nope.json"))
    assert m._data == before


def test_metrics_load_corrupted_file(tmp_path):
    """Loading a corrupted file should leave metrics unchanged."""
    m = Metrics()
    before = dict(m._data)
    path = tmp_path / "metrics.json"
    path.write_text("{not json", encoding="utf-8")
    m.load(str(path))
    assert m._data == before