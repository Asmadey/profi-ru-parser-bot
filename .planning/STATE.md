# Current State

**Last reviewed:** 2026-07-13
**Phase 1 (Stabilization): COMPLETE** — commit `a278c0c`
**Phase 2 (Configuration & Deployment): COMPLETE** — commit `043fbb1`
**Phase 3 (Robustness & Observability): COMPLETE** — commit `d54efb9`
**Phase 4 (Feature Enhancements): COMPLETE** — commit `4aaf626`

---

## Status: Production-Ready Feature Bot

The core pipeline (parse → filter → enrich → notify) is operational with multi-specialty support, interactive Telegram commands, and order detail enrichment.

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

4. **Order enrichment (`enricher.py`)** — ✅ NEW (Phase 4)
   - Opens order detail pages in same browser context
   - Extracts: full_description, client_rating, responses_count, attachments_count, category_path
   - Rate-limited (3s delay, max 5 per cycle)
   - Defensive: returns original order on any failure

5. **Interactive Telegram commands (`bot_commands.py`)** — ✅ NEW (Phase 4)
   - `/status` — parser heartbeat, uptime, last poll, pause status
   - `/stats` — metrics counters with emojis
   - `/pause` — create pause.flag, stop processing
   - `/resume` — remove pause.flag, resume processing
   - `/last` — last 5 matched orders
   - `/test` — test formatted message
   - `/help` — command list
   - Admin-only (ADMIN_CHAT_ID guard)
   - Commands registered with Telegram Bot API on startup

6. **Telegram notifier (`run_all.py::telegram_notifier`)** — Functional + pause-aware (Phase 4)
   - Cursor-based JSONL tail reading
   - HTML message formatting
   - SOCKS5 proxy support
   - Flood control handling
   - Pause-aware: skips sending when paused, cursor still advances

7. **Orchestrator (`run_all.py`)** — Functional + 3 tasks (Phase 4)
   - Concurrent: parser subprocess + telegram notifier + bot commands dispatcher
   - Subprocess supervision with auto-restart
   - Graceful shutdown

8. **Resilience (`main.py`)** — Functional + exponential backoff (Phase 3)
   - Network error handling with 3-strike restart
   - Browser crash detection and recovery
   - Session expiry detection → re-auth
   - Exponential backoff (5s × 2^n, cap 900s)

9. **Logging (`logger_setup.py`)** — Functional + JSON format (Phase 3)
   - Rotating file handlers
   - JSON format option via `LOG_FORMAT=json`

10. **Metrics (`metrics.py`)** — ✅ NEW (Phase 3)
    - Counters: parsed, matched, sent, errors, restarts, uptime
    - JSON persistence (`metrics.json`)

11. **Alerting (`alerting.py`)** — ✅ NEW (Phase 3)
    - Telegram alerts on critical errors

12. **Data retention (`cleanup.py`)** — ✅ NEW (Phase 3)
    - Old screenshot cleanup (7 days)
    - JSONL trimming (10k lines)

13. **Storage robustness (`storage.py`)** — ✅ Enhanced (Phase 3)
    - Graceful recovery on corrupted seen_ids.json

14. **Deployment** — ✅ Complete (Phase 2)
    - `Dockerfile` + `docker-compose.yml`
    - `pyproject.toml`
    - systemd unit file
    - `.env.example`
    - README fully rewritten

---

## What's Missing / Not Implemented 🚧

1. **No tests** — Zero test files in the repository.
2. **No CI/CD** — No GitHub Actions, no linting config.
3. **No web dashboard** — No web UI for monitoring.
4. **No database backend** — Still using JSON/JSONL files.
5. **No multi-account support** — Single Profi.ru account.
6. **No auto-response** — No automatic responses to orders.

---

## What's Next

### Phase 5: Testing & CI (M5)
1. Unit tests for `filters.py`, `parser.py`, `storage.py`, `tg_formatter.py`
2. Unit tests for `specialties.py`, `enricher.py`, `bot_commands.py`
3. Integration tests for `run_all.py`
4. GitHub Actions CI pipeline (lint + test)
5. Type checking (mypy)

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
| `pyproject.toml` | ✅ New | Python packaging (Phase 2) |
| `systemd/profi-parser-bot.service` | ✅ New | Systemd unit (Phase 2) |
| `requirements.txt` | ✅ Present | Pinned dependencies |
| `.gitignore` | ✅ Present | Covers runtime artifacts |