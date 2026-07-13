# Phase 3: Robustness & Observability (M3)

**Goal:** Improve reliability for unattended 24/7 operation.

## Tasks

### Wave 1 (parallel — no file conflicts)

| Task | File(s) | Action |
|---|---|---|
| T1 (M3.2) | `metrics.py` (new) | Metrics collector: orders_parsed, orders_matched, orders_sent, parse_errors, restart_count, uptime. Write to `metrics.json` periodically. |
| T2 (M3.3) | `alerting.py` (new) | Send Telegram alert on critical errors (auth failure, too many restarts, Chrome unavailable). Uses BOT_TOKEN + ADMIN_CHAT_ID. |
| T3 (M3.5) | `cleanup.py` (new) | Data retention: delete debug screenshots older than 7 days, trim new_orders.jsonl to last N entries. |
| T4 (M3.6) | `storage.py` | Graceful handling of seen_ids.json corruption (backup + reset on unparseable JSON). |

### Wave 2 (depends on wave 1)

| Task | File(s) | Action |
|---|---|---|
| T5 (M3.1) | `logger_setup.py` | Add optional JSON formatter (env var LOG_FORMAT=json). |
| T6 (M3.7) | `main.py` | Exponential backoff for repeated parse failures (double delay up to backoff_max_sec). |
| T7 (M3.4) | `main.py` | Proactive session refresh: re-auth if storage_state.json older than 24h. |

## Acceptance Criteria

- [ ] metrics.py writes metrics.json with counters
- [ ] alerting.py sends Telegram message on critical errors
- [ ] cleanup.py deletes old debug files and trims JSONL
- [ ] storage.py handles corrupted seen_ids.json gracefully
- [ ] logger_setup.py supports JSON format via env var
- [ ] main.py uses exponential backoff on repeated failures
- [ ] main.py proactively refreshes auth if state file is old
- [ ] No existing functionality broken
- [ ] Git commit + push