# Profi.ru Parser Bot

## Summary

A Telegram bot that automatically monitors Profi.ru (a Russian freelance/services marketplace) for new order postings, filters them against AI/ML/chatbot development keywords, and sends relevant notifications to a Telegram chat. The parser uses Playwright with a real browser (via Chrome DevTools Protocol) to mimic human behavior and avoid account bans.

## Problem Solved

- Profi.ru has no public API for order monitoring
- Manual page refreshing is tedious and slow
- The full order stream is noisy; only AI/development-related orders are relevant
- Aggressive scraping risks account suspension

## Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Primary language |
| **Playwright 1.57** | Browser automation via CDP (Chrome DevTools Protocol) |
| **aiogram 3.24** | Telegram Bot API client (async) |
| **aiohttp** | Async HTTP for Telegram session (with SOCKS5 proxy support) |
| **asyncio** | Concurrent parser + notifier orchestration |
| **python-dotenv** | Environment variable loading (`.env`) |
| **beautifulsoup4 / lxml** | HTML parsing (available as dependency, not directly used in source) |
| **JSON / JSONL** | Local state persistence (seen IDs, order log, read cursor) |

## Architecture

```
                     run_all.py  (entry point — orchestrator)
                    ┌──────┴──────────────────────┐
                    │                             │
          supervise_parser()              telegram_notifier()
          (asyncio task)                  (asyncio task)
                    │                             │
                    ▼                             ▼
         ┌─────────────────┐          ┌──────────────────────┐
         │  main.py        │          │  run_all.py           │
         │  (subprocess)   │          │  (notifier loop)      │
         │                 │          │                      │
         │  Playwright     │          │  Reads new_orders     │
         │  ┌── CDP ──►    │          │  .jsonl via cursor    │
         │  │  Chrome:9225 │          │  (bot_cursor.json)    │
         │  │              │          │                      │
         │  │ auth.py      │          │  format_order()       │
         │  │ (first-run   │          │  → tg_formatter.py    │
         │  │  manual login│          │                      │
         │  │  → state)    │          │  bot.send_message()   │
         │  │              │          │  via SOCKS5 proxy     │
         │  │ client.py    │          │                      │
         │  │ (ProfiClient)│          │  Flood control        │
         │  │              │          │  (TelegramRetryAfter) │
         │  │ parser.py    │          └──────────────────────┘
         │  │ (DOM parse)  │
         │  │              │
         │  │ filters.py   │
         │  │ (keyword     │
         │  │  matching)   │
         │  │              │
         │  │ storage.py   │
         │  │ (seen_ids)   │
         │  └─────────────│
         │                 │
         │  new_orders.jsonl ────► (shared file between processes)
         └─────────────────┘
```

### Data Flow

1. **run_all.py** launches two concurrent asyncio tasks
2. **Parser subprocess** (`main.py`):
   - Connects to external Chrome browser via CDP (port 9225)
   - Loads `storage_state.json` for authenticated session
   - Polls `https://profi.ru/backoffice/` with human-like delays (45±25s)
   - Extracts order cards from DOM (`parser.py`)
   - Filters orders against AI/ML keyword patterns (`filters.py`)
   - Deduplicates via `seen_ids.json`
   - Appends matching orders to `new_orders.jsonl`
3. **Telegram notifier** (in `run_all.py`):
   - Polls `new_orders.jsonl` every 3s using a byte-offset cursor (`bot_cursor.json`)
   - Formats each order as HTML (`tg_formatter.py`)
   - Sends to `ADMIN_CHAT_ID` via Telegram Bot API through SOCKS5 proxy
   - Handles flood control (`TelegramRetryAfter`)

### Alternative Entry Points

- **`tg_bot.py`** — Older standalone bot variant (has bugs, see STATE.md). Reads JSONL via `tg_watcher.py` and sends to Telegram. Not the primary entry point.
- **`main.py`** — Can run standalone as parser-only (writes JSONL without Telegram).

## Key Components

| File | Role |
|---|---|
| `run_all.py` | **Entry point.** Orchestrates parser subprocess + Telegram notifier |
| `main.py` | Parser monitoring loop (Playwright, refresh, extract, filter, save) |
| `client.py` | `ProfiClient` — CDP browser connection, page management, debug dumps |
| `auth.py` | First-run interactive login (manual browser login → save `storage_state.json`) |
| `parser.py` | DOM extraction of order card fields (title, price, description, location, etc.) |
| `filters.py` | Multi-stage order filtering: target keywords, dev intent, disallowed topics/platforms, budget threshold (≥10,000₽) |
| `storage.py` | `seen_ids.json` load/save + JSONL append |
| `tg_formatter.py` | HTML message formatting for Telegram notifications |
| `tg_watcher.py` | JSONL tail-reader with offset state (used by `tg_bot.py`) |
| `tg_bot.py` | Alternative standalone bot (broken — see STATE.md) |
| `logger_setup.py` | Rotating file logger (2MB, 5 backups, separate error log) |
| `config.py` | `Settings` dataclass — all configurable parameters |

## Configuration

- **`config.py`** — `Settings` dataclass with defaults (URLs, selectors, poll intervals, timeouts, backoff)
- **`.env`** (gitignored) — `BOT_TOKEN`, `ADMIN_CHAT_ID`, `TELEGRAM_PROXY`
- **External Chrome** — Must be running with `--remote-debugging-port=9225` for CDP connection

## Runtime Artifacts (gitignored)

- `storage_state.json` — Playwright auth state (cookies, localStorage)
- `seen_ids.json` — Set of processed order IDs (dedup)
- `new_orders.jsonl` — Append-only log of matching orders
- `bot_cursor.json` — Byte offset for JSONL tail-reading
- `tg_state.json` — Offset state for `tg_bot.py` variant
- `logs/` — Rotating logs + debug screenshots/HTML dumps