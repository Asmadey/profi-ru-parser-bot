# Current State

**Last reviewed:** 2026-07-13

---

## Status: MVP — Functional with Known Bugs

The core pipeline (parse → filter → notify) is operational via `run_all.py`. The project can run end-to-end given proper setup (external Chrome CDP + `.env` credentials). However, there are bugs in alternative entry points and missing operational infrastructure.

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

---

## What's Broken / Buggy ❌

1. **`tg_bot.py`** — Multiple bugs, likely dead code:
   - `text = order_matches_filter(order)` — assigns `bool` to `text`, then passes to `bot.send_message()` as message body. Should use `format_order(order)` instead.
   - `orders, _ = orders, _ = read_new_orders()` — nonsensical double assignment (no-op, but confusing).
   - `from asyncio.log import logger` — imports stdlib's logger, not the configured `setup_logger`. The `log` variable from `setup_logger("bot")` is used for some calls, but `logger` (stdlib) is used for others — inconsistent.
   - This file appears to be an older alternative to `run_all.py`'s notifier and is NOT the primary entry point.

2. **`tg_formatter.py`** — Minor issue:
   - `from html import escape as h` on line 3 is immediately shadowed by `def h(x):` on line 5. The import is unused/dead code.

3. **README vs Reality mismatch:**
   - README says configure `KEYWORDS = []` in `config.py`, but actual filtering is hardcoded in `filters.py` with regex patterns. The `config.py` `Settings` dataclass has no `KEYWORDS` field.
   - README doesn't mention the external Chrome CDP requirement (port 9225) — a critical setup step.
   - README says `python run_all.py` but doesn't document the prerequisites (Chrome with `--remote-debugging-port=9225`, `.env` file).

---

## What's Missing / Not Implemented 🚧

1. **No `.env.example`** — Users must guess env var names (`BOT_TOKEN`, `ADMIN_CHAT_ID`, `TELEGRAM_PROXY`).
2. **No tests** — Zero test files in the repository.
3. **No CI/CD** — No GitHub Actions, no linting config.
4. **No Docker** — No Dockerfile or docker-compose.
5. **No `pyproject.toml`** — Only `requirements.txt` with pinned versions.
6. **No `.env` file present** — (gitignored, expected).
7. **No health monitoring** — No way to check if bot is alive externally.
8. **No alerting** — Critical failures (auth, Chrome down, too many restarts) are logged but not sent to admin via Telegram.
9. **No data retention** — `logs/debug/` and `new_orders.jsonl` grow indefinitely.
10. **No interactive bot commands** — No `/status`, `/pause`, `/stats` commands.
11. **No multi-chat/multi-specialty** — Single filter set, single target chat.

---

## What's Next  *(Priority Order)*

1. **Fix or remove `tg_bot.py`** — Dead code with bugs creates confusion
2. **Fix `tg_formatter.py` import** — Trivial cleanup
3. **Add `.env.example`** — Critical for onboarding
4. **Update README** — Document Chrome CDP requirement and actual config structure
5. **Add startup validation** — Fail fast if Chrome CDP unreachable
6. **Add Docker setup** — For reproducible deployment
7. **Add tests for `filters.py`** — Most complex logic, highest risk of regression

---

## File Inventory

| File | Status | Notes |
|---|---|---|
| `run_all.py` | ✅ Working | Primary entry point |
| `main.py` | ✅ Working | Parser loop |
| `client.py` | ✅ Working | Playwright CDP client |
| `auth.py` | ✅ Working | First-run auth |
| `parser.py` | ✅ Working | DOM extraction |
| `filters.py` | ✅ Working | Multi-stage filtering |
| `storage.py` | ✅ Working | Seen IDs + JSONL |
| `tg_formatter.py` | ⚠️ Minor bug | Unused import shadowing |
| `logger_setup.py` | ✅ Working | Rotating logger |
| `tg_bot.py` | ❌ Broken | Multiple bugs, likely dead code |
| `tg_watcher.py` | ⚠️ Unused | Only used by broken `tg_bot.py` |
| `config.py` | ✅ Working | Settings dataclass |
| `requirements.txt` | ✅ Present | Pinned dependencies |
| `.gitignore` | ✅ Present | Covers runtime artifacts |
| `README.md` | ⚠️ Outdated | Mismatches actual implementation |