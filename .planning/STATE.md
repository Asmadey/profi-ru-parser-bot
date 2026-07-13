# Current State

**Last reviewed:** 2026-07-13
**Phase 1 (Stabilization): COMPLETE** — commit `a278c0c`
**Phase 2 (Configuration & Deployment): COMPLETE** — commit `043fbb1`
**Phase 3 (Robustness & Observability): COMPLETE** — commit `d54efb9`
**Phase 4 (Feature Enhancements): COMPLETE** — commit `4aaf626`
**Phase 5 (Testing & CI): COMPLETE** — commit `857d1f8`

---

## Status: Production-Ready with Full Test Coverage

All 5 phases complete. The bot has multi-specialty filtering, interactive commands, order enrichment, 205 passing tests, and CI pipeline.

---

## What Works ✅

1. **Parser core (`main.py` + `client.py`)** — Fully functional
   - Connects to Chrome via CDP on port 9225
   - Opens Profi.ru backoffice, refreshes page, waits for order cards
   - Extracts order data from DOM (`parser.py`)
   - Deduplicates via `seen_ids.json` (`storage.py`)
   - Appends to `new_orders.jsonl`
   - Human-like polling delays (45±25s)
   - Multi-specialty filtering via `match_specialties()` (Phase 4)
   - Order detail enrichment via `enricher.py` (Phase 4)
   - Pause flag check (Phase 4)

2. **Authentication (`auth.py`)** — Functional
   - First-run interactive login (non-headless browser)
   - Saves `storage_state.json` for session persistence
   - Proactive re-auth if state > 24h old (Phase 3)

3. **Order filtering (`filters.py` + `specialties.py`)** — Multi-specialty (Phase 4)
   - `Specialty` dataclass with configurable keyword sets
   - `load_specialties()` from YAML file
   - `match_specialties()` — order can match multiple specialties
   - `DEFAULT_SPECIALTY` backwards-compatible with original patterns
   - `specialties.yaml.example`: AI/ML, Web Dev, Data Science presets
   - Budget threshold per specialty

4. **Order enrichment (`enricher.py`)** — Phase 4
   - Opens order detail pages in same browser context
   - Extracts: full_description, client_rating, responses_count, attachments_count, category_path
   - Rate-limited (3s delay, max 5 per cycle)
   - Defensive: returns original order on any failure

5. **Interactive Telegram commands (`bot_commands.py`)** — Phase 4
   - `/status` `/stats` `/pause` `/resume` `/last` `/test` `/help`
   - Admin-only (ADMIN_CHAT_ID guard)
   - Commands registered with Telegram Bot API on startup

6. **Telegram notifier (`run_all.py::telegram_notifier`)** — Functional + pause-aware
   - Cursor-based JSONL tail reading
   - HTML message formatting, SOCKS5 proxy, flood control
   - Pause-aware: skips sending when paused, cursor still advances

7. **Orchestrator (`run_all.py`)** — 3 concurrent async tasks
   - parser subprocess + telegram notifier + bot commands dispatcher
   - Subprocess supervision with auto-restart, graceful shutdown

8. **Resilience (`main.py`)** — Exponential backoff (Phase 3)
   - Network error handling, browser crash recovery, session re-auth
   - Exponential backoff (5s × 2^n, cap 900s)

9. **Observability** — Phase 3
   - `logger_setup.py` — rotating logs + JSON format
   - `metrics.py` — counters with JSON persistence
   - `alerting.py` — Telegram alerts on critical errors
   - `cleanup.py` — data retention (screenshots 7d, JSONL 10k lines)

10. **Deployment** — Phase 2
    - Dockerfile, docker-compose.yml, pyproject.toml, systemd unit, .env.example, README

11. **Testing & CI** — ✅ NEW (Phase 5)
    - 205 unit + integration tests across 9 test files
    - GitHub Actions CI: ruff lint + pytest (matrix 3.10/3.11/3.12)
    - mypy type checking configured
    - pytest-asyncio for async tests
    - All tests pass: `pytest tests/ -v`

---

## Test Coverage (Phase 5)

| Test File | Tests | Module |
|---|---|---|
| `test_filters.py` | 55 | filters.py — keyword matching, budget, disallowed topics/platforms |
| `test_specialties.py` | 20 | specialties.py — DEFAULT_SPECIALTY, YAML loading |
| `test_bot_commands.py` | 40 | bot_commands.py — all 7 command handlers, helpers |
| `test_tg_formatter.py` | 21 | tg_formatter.py — HTML escaping, URL, truncation |
| `test_enricher.py` | 18 | enricher.py — _build_url, enrich_order (mock), batch |
| `test_run_all.py` | 22 | run_all.py — CDP, cursor, notifier, subprocess, async_main |
| `test_metrics.py` | 14 | metrics.py — counters, save/load, KeyError |
| `test_storage.py` | 8 | storage.py — seen_ids, JSONL, corruption recovery |
| `test_cleanup.py` | 7 | cleanup.py — screenshot cleanup, JSONL trim |
| **Total** | **205** | |

---

## What's Missing / Not Implemented 🚧

1. **No web dashboard** — No web UI for monitoring.
2. **No database backend** — Still using JSON/JSONL files.
3. **No multi-account support** — Single Profi.ru account.
4. **No auto-response** — No automatic responses to orders.

---

## File Inventory

| File | Status | Notes |
|---|---|---|
| `run_all.py` | ✅ Working | 3 async tasks: parser + notifier + commands |
| `main.py` | ✅ Working | Multi-specialty + enrichment + pause |
| `client.py` | ✅ Working | Playwright CDP client |
| `auth.py` | ✅ Working | First-run auth + proactive refresh |
| `parser.py` | ✅ Working | DOM extraction |
| `filters.py` | ✅ Enhanced | Multi-specialty filtering (Phase 4) |
| `specialties.py` | ✅ New | Specialty dataclass + YAML loader (Phase 4) |
| `specialties.yaml.example` | ✅ New | 3 example specialties (Phase 4) |
| `enricher.py` | ✅ New | Order detail enrichment (Phase 4) |
| `bot_commands.py` | ✅ New | Interactive Telegram commands (Phase 4) |
| `storage.py` | ✅ Enhanced | Corruption recovery (Phase 3) |
| `tg_formatter.py` | ✅ Working | HTML formatting |
| `logger_setup.py` | ✅ Working | Rotating logger + JSON option |
| `metrics.py` | ✅ New | In-memory metrics (Phase 3) |
| `alerting.py` | ✅ New | Telegram alerts (Phase 3) |
| `cleanup.py` | ✅ New | Data retention (Phase 3) |
| `config.py` | ✅ Enhanced | Settings with specialties_path |
| `.env.example` | ✅ Present | Environment docs |
| `README.md` | ✅ Rewritten | Full docs (Phase 2) |
| `Dockerfile` | ✅ New | Container deployment (Phase 2) |
| `docker-compose.yml` | ✅ New | Container orchestration (Phase 2) |
| `pyproject.toml` | ✅ Enhanced | Packaging + pytest + mypy config (Phase 5) |
| `systemd/profi-parser-bot.service` | ✅ New | Systemd unit (Phase 2) |
| `requirements.txt` | ✅ Present | Pinned dependencies + PyYAML |
| `requirements-dev.txt` | ✅ New | Dev dependencies (Phase 5) |
| `.github/workflows/ci.yml` | ✅ New | CI pipeline (Phase 5) |
| `.gitignore` | ✅ Present | Covers runtime artifacts |
| `tests/` | ✅ New | 9 test files, 205 tests (Phase 5) |