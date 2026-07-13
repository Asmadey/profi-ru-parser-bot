# Phase 5 — Testing & CI (M5)

## Goal
Add unit tests for all modules, set up CI pipeline with GitHub Actions, enable type checking.

## Tasks

### M5.1–M5.4 — Unit Tests
**Files:** `tests/test_filters.py`, `tests/test_specialties.py`, `tests/test_storage.py`, `tests/test_tg_formatter.py`, `tests/test_cleanup.py`, `tests/test_metrics.py`, `tests/test_enricher.py`, `tests/test_bot_commands.py`

Test modules (each independently runnable via pytest):
- **test_filters.py** — keyword matching (positive/negative), budget extraction (various formats), disallowed topics exclusion, disallowed platforms exclusion, dev intent detection, text normalization (ё→е, Unicode spaces, case), order_matches_filter backwards compat, order_matches_specialty, match_specialties (multi-match)
- **test_specialties.py** — DEFAULT_SPECIALTY structure, load_specialties (missing file → default, empty file → default, valid YAML → list, invalid YAML → error), specialties.yaml.example loads correctly with 3 entries
- **test_storage.py** — load_seen_ids (empty, valid, corrupted → backup + reset, dict format, unexpected type), save_seen_ids (round-trip), append_jsonl
- **test_tg_formatter.py** — HTML escaping, URL handling (relative → absolute), truncation (3000 chars), empty fields, all fields populated, add_space_after_do
- **test_cleanup.py** — cleanup_debug_screenshots (creates files with different ages, verifies deletion), trim_jsonl (creates file with N lines, trims to max), run_cleanup combined
- **test_metrics.py** — Metrics init, inc/set/get, to_dict with uptime, save/load round-trip, unknown metric raises KeyError
- **test_enricher.py** — _build_url (relative, absolute, empty), enrich_order with mock context (success + failure), enrich_orders_batch (max_enrich limit, delay, passthrough)
- **test_bot_commands.py** — is_paused (flag exists/not), get_admin_id (valid/missing), _fmt_uptime, _read_json (valid/missing/corrupted), command handlers with mock Bot/Message

### M5.5 — Integration Test
**Files:** `tests/test_run_all.py`
- Mock subprocess for parser, mock Telegram Bot
- Test: check_cdp_available (mock socket), load_cursor/save_cursor round-trip, telegram_notifier with paused state

### M5.6 — GitHub Actions CI
**Files:** `.github/workflows/ci.yml`
- Trigger: push + pull_request
- Steps: checkout, setup Python 3.11, install deps (pip install -r requirements.txt + pytest + ruff + mypy), ruff check, mypy, pytest
- Upload coverage report artifact

### M5.7 — Type Checking + Dev Deps
**Files:** `pyproject.toml` (modify), `requirements-dev.txt` (new)
- Add `[tool.mypy]` section to pyproject.toml
- Add `[tool.pytest.ini_options]` with testpaths, asyncio_mode
- Create requirements-dev.txt: pytest, pytest-asyncio, ruff, mypy, pyyaml
- Add PyYAML to requirements.txt (needed by specialties.py)

## Wave Plan

### Wave 1 (parallel, independent test files)
- Task A: test_filters.py + test_specialties.py
- Task B: test_storage.py + test_cleanup.py + test_metrics.py
- Task C: test_tg_formatter.py + test_enricher.py + test_bot_commands.py

### Wave 2 (parallel, config + CI)
- Task D: .github/workflows/ci.yml + requirements-dev.txt
- Task E: pyproject.toml update (mypy, pytest config) + requirements.txt (add pyyaml) + test_run_all.py

## Acceptance Criteria
1. All unit tests pass with `pytest tests/ -v`
2. Coverage > 70% for filters, specialties, storage, tg_formatter, cleanup, metrics
3. ruff check passes with no errors
4. mypy runs without fatal errors on tested modules
5. GitHub Actions CI workflow triggers on push and PR
6. No regressions in existing code