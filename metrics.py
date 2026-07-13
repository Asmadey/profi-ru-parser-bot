"""Metrics collector for the Profi.ru Parser Bot.

Uses only the Python standard library (json, time, os).

Counters
--------
- orders_parsed   — total cards processed
- orders_matched  — cards that passed the filter
- orders_sent     — Telegram messages sent
- parse_errors    — card parsing failures
- restart_count   — parser subprocess restarts
- start_time      — unix timestamp when the bot started
- last_poll_time  — unix timestamp of the last poll cycle
"""

import json
import os
import time


COUNTERS = (
    "orders_parsed",
    "orders_matched",
    "orders_sent",
    "parse_errors",
    "restart_count",
    "start_time",
    "last_poll_time",
)


class Metrics:
    """Lightweight in-memory metrics collector with JSON persistence."""

    def __init__(self) -> None:
        self._data: dict[str, int | float] = {}
        now = time.time()
        for name in COUNTERS:
            if name in ("start_time",):
                self._data[name] = now
            else:
                self._data[name] = 0

    # ------------------------------------------------------------------ #
    # Mutators
    # ------------------------------------------------------------------ #
    def inc(self, name: str, value: int = 1) -> None:
        """Increment a counter by *value* (default 1)."""
        if name not in self._data:
            raise KeyError(f"Unknown metric: {name!r}")
        self._data[name] = self._data[name] + value

    def set(self, name: str, value: int | float) -> None:
        """Set a counter to an exact *value*."""
        if name not in self._data:
            raise KeyError(f"Unknown metric: {name!r}")
        self._data[name] = value

    # ------------------------------------------------------------------ #
    # Accessors
    # ------------------------------------------------------------------ #
    def get(self, name: str, default: int | float = 0) -> int | float:
        """Return the current value of a metric."""
        return self._data.get(name, default)

    def to_dict(self) -> dict[str, int | float]:
        """Return all metrics as a dict, including computed *uptime*."""
        now = time.time()
        result = dict(self._data)
        result["uptime"] = now - self._data.get("start_time", now)
        return result

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def save(self, path: str = "metrics.json") -> None:
        """Write current metrics (including uptime) to *path* as JSON."""
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)

    def load(self, path: str = "metrics.json") -> None:
        """Load metrics from *path*, preserving existing counters.

        If *start_time* is missing from the file the current in-memory
        value is kept untouched.
        """
        if not os.path.exists(path):
            return

        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return

        if not isinstance(loaded, dict):
            return

        for name in COUNTERS:
            if name in loaded:
                self._data[name] = loaded[name]
            # If start_time is absent from file, keep the value set in __init__.

    # ------------------------------------------------------------------ #
    # Convenience
    # ------------------------------------------------------------------ #
    def __getitem__(self, name: str) -> int | float:
        return self._data[name]

    def __setitem__(self, name: str, value: int | float) -> None:
        if name not in self._data:
            raise KeyError(f"Unknown metric: {name!r}")
        self._data[name] = value

    def __contains__(self, name: str) -> bool:
        return name in self._data

    def __repr__(self) -> str:
        return f"Metrics({self._data!r})"


if __name__ == "__main__":
    m = Metrics()
    m.inc("orders_parsed", 5)
    m.inc("orders_matched", 3)
    m.set("last_poll_time", time.time())
    m.save("/tmp/metrics_demo.json")
    print(m.to_dict())