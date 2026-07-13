# Current State

**Last reviewed:** 2026-07-13
**Phase 1 (Stabilization): COMPLETE** — commit `a278c0c`

---

## Status: MVP — Stabilized

The core pipeline (parse → filter → notify) is operational via `run_all.py`. Phase 1 stabilization complete: dead code removed, bugs fixed, startup validation added.

---

## What Works ✅

1. **Parser core (`main.py` + `client.py`)** — Fully functional
   - Connects to Chrome via CDP on port 9225
   - Opens Profi.ru backoffice, refreshes page, waits for order cards
   - Extracts order data from DOM (`parser.py`)
   - Deduplicates via `seen_ids.json` (`storage.py`)
   - Appends to `new_orders.jsonl`
   - Human-like polling delays (45±25s)

2. **Authentication (`auth.py`)** — Functional
   - First-run interactive login (non-headless browser)
   - Saves `storage_state.json` for session persistence
   - Skips re-auth if state file exists

3. **Order filtering (`filters.py`)** — Comprehensive and functional
   - 35+ regex patterns for AI/ML/chatbot keywords (Russian + English)
   - Development intent keywords
   - Disallowed topics (marketing/ads) exclusion
   - Disallowed platforms (Instagram, WhatsApp, etc.) exclusion
   - Budget extraction with ≥10,000₽ threshold
   - Text normalization (case-insensitive, ё→е, Unicode space handling)

4. **Telegram notifier (`run_all.py::telegram_notifier`)** — Functional
   - Cursor-based JSONL tail reading (`bot_cursor.json`)
   - HTML message formatting (`tg_formatter.py`)
   - SOCKS5 proxy support
   - Flood control handling (`TelegramRetryAfter`)
   - First-start cursor initialization to end-of-file

5. **Orchestrator (`run_all.py`)** — Functional
   - Concurrent parser subprocess + Telegram notifier
   - Subprocess supervision with auto-restart (up to 50 times)
   - stdout/stderr piping to logger
   - Graceful shutdown (SIGINT → cancel tasks → terminate subprocess → kill if needed)

6. **Resilience (`main.py`)** — Functional
   - Network error handling (DNS, disconnect) with 3-strike restart
   - Browser crash detection and recovery
   - Session expiry detection (title-based "вход"/"login" check) → re-auth
   - Debug diagnostics (screenshots + HTML dumps on card-not-found)

7. **Logging (`logger_setup.py`)** — Functional
   - Rotating file handlers (2MB, 5 backups)
   - Separate error log file
   - JSON payload logging helper
   - Console + file output

8. **Startup validation (`run_all.py`)** — ✅ NEW (Phase 1)
   - Chrome CDP reachability check before starting
   - Clear error message if Chrome is not running on port 9225
   - Exits with code 1 if CDP unavailable

9. **Environment documentation (`.env.example`)** — ✅ NEW (Phase 1)
   - Documents BOT_TOKEN, ADMIN_CHAT_ID, TELEGRAM_PROXY

---

## Phase 1 Fixes ✅

- ~~`tg_bot.py` — Multiple bugs, dead code~~ → **DELETED**
- ~~`tg_watcher.py` — Only used by broken tg_bot.py~~ → **DELETED**
- ~~`tg_formatter.py` — Unused import shadowing~~ → **FIXED** (removed `from html import escape as h`)
- ~~No `.env.example`~~ → **CREATED**
- ~~No startup validation for Chrome CDP~~ → **ADDED** in `run_all.py`

---

## What's Missing / Not Implemented 🚧

1. **No tests** — Zero test files in the repository.
2. **No CI/CD** — No GitHub Actions, no linting config.
3. **No Docker** — No Dockerfile or docker-compose.
4. **No `pyproject.toml`** — Only `requirements.txt` with pinned versions.
5. **No health monitoring** — No way to check if bot is alive externally.
6. **No alerting** — Critical failures logged but not sent to admin via Telegram.
7. **No data retention** — `logs/debug/` and `new_orders.jsonl` grow indefinitely.
8. **No interactive bot commands** — No `/status`, `/pause`, `/stats` commands.
9. **No multi-chat/multi-specialty** — Single filter set, single target chat.
10. **README outdated** — Doesn't document Chrome CDP requirement.

---

## What's Next *(Priority Order)*

### Phase 2: Configuration & Deployment (M2)
1. Update README — document Chrome CDP requirement and actual config structure
2. Move hardcoded settings in `filters.py` to `config.py`
3. Add `Dockerfile` + `docker-compose.yml`
4. Add `pyproject.toml`
5. Add health check endpoint
6. Add systemd unit file

### Phase 3: Robustness & Observability (M3)
1. Structured JSON logging
2. Metrics collection
3. Alerting via Telegram
4. Proactive session refresh
5. Data retention cleanup

---

## File Inventory

| File | Status | Notes |
|---|---|---|
| `run_all.py` | ✅ Working | Primary entry point. CDP validation added (Phase 1) |
| `main.py` | ✅ Working | Parser loop |
| `client.py` | ✅ Working | Playwright CDP client |
| `auth.py` | ✅ Working | First-run auth |
| `parser.py` | ✅ Working | DOM extraction |
| `filters.py` | ✅ Working | Multi-stage filtering |
| `storage.py` | ✅ Working | Seen IDs + JSONL |
| `tg_formatter.py` | ✅ Fixed | Unused import removed (Phase 1) |
| `logger_setup.py` | ✅ Working | Rotating logger |
| `config.py` | ✅ Working | Settings dataclass |
| `.env.example` | ✅ New | Created in Phase 1 |
| `tg_bot.py` | ❌ Deleted | Removed in Phase 1 |
| `tg_watcher.py` | ❌ Deleted | Removed in Phase 1 |
| `README.md` | ⚠️ Outdated | Mismatches actual implementation |
| `requirements.txt` | ✅ Present | Pinned dependencies |
| `.gitignore` | ✅ Present | Covers runtime artifacts |