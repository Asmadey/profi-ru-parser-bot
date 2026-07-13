# Roadmap

## Current State: MVP Functional (with known bugs)

The core parser→filter→notify pipeline is operational via `run_all.py`. See STATE.md for details.

---

## M1 — Stabilization & Bug Fixes  *(Phase 1 — Immediate)*

**Goal:** Fix known bugs, remove dead code, ensure reliable long-running operation.

- [ ] **M1.1** Fix `tg_bot.py` — `order_matches_filter()` returns `bool`, but `tg_bot.py` assigns it to `text` and sends it as message body. Either fix to use `format_order()` or remove the file if `run_all.py` is the sole entry point.
- [ ] **M1.2** Fix `tg_formatter.py` — unused import `from html import escape as h` is shadowed by function `h()`. Remove the unused import.
- [ ] **M1.3** Fix `tg_bot.py` — double assignment bug: `orders, _ = orders, _ = read_new_orders()`.
- [ ] **M1.4** Fix `tg_bot.py` — `from asyncio.log import logger` imports a stdlib logger, not the configured one. Use `setup_logger` like `run_all.py` does.
- [ ] **M1.5** Decide: remove `tg_bot.py` + `tg_watcher.py` (dead code) or consolidate them into `run_all.py`.
- [ ] **M1.6** Add `.env.example` with documented variables (`BOT_TOKEN`, `ADMIN_CHAT_ID`, `TELEGRAM_PROXY`).
- [ ] **M1.7** Add startup validation: fail fast with clear error if Chrome CDP is not reachable on port 9225.

## M2 — Configuration & Deployment  *(Phase 2 — Short-term)*

**Goal:** Make the project easy to deploy and configure.

- [ ] **M2.1** Move hardcoded settings in `filters.py` (keyword patterns, budget threshold) to `config.py` or external config file for easier tuning.
- [ ] **M2.2** Update README to document the external Chrome CDP requirement (currently undocumented).
- [ ] **M2.3** Add `Dockerfile` + `docker-compose.yml` for containerized deployment (including Chrome with `--remote-debugging-port`).
- [ ] **M2.4** Add `pyproject.toml` for modern Python packaging (replace or supplement `requirements.txt`).
- [ ] **M2.5** Add health check endpoint or heartbeat file for monitoring that the bot is alive.
- [ ] **M2.6** Add systemd unit file or supervisor config for production deployment.

## M3 — Robustness & Observability  *(Phase 3 — Medium-term)*

**Goal:** Improve reliability for unattended 24/7 operation.

- [ ] **M3.1** Add structured logging with JSON format for machine-parseable logs.
- [ ] **M3.2** Add metrics: orders parsed, orders matched, orders sent, parse errors, restart count, uptime.
- [ ] **M3.3** Add alerting: send a Telegram message to admin on critical errors (e.g., auth failure, too many restarts, Chrome unavailable).
- [ ] **M3.4** Add automatic `storage_state.json` refresh before expiry (proactive re-auth, not just reactive).
- [ ] **M3.5** Add data retention: auto-cleanup of old `logs/debug/` screenshots and old `new_orders.jsonl` entries.
- [ ] **M3.6** Add graceful handling of `seen_ids.json` corruption (currently `load_seen_ids` catches generic exceptions but could be more robust).
- [ ] **M3.7** Add exponential backoff for repeated parse failures instead of fixed delays.

## M4 — Feature Enhancements  *(Phase 4 — Long-term)*

**Goal:** Expand functionality based on usage patterns.

- [ ] **M4.1** Multi-specialty support — allow configuring multiple keyword sets for different professional domains (not just AI/ML).
- [ ] **M4.2** Multi-chat support — send different filtered orders to different Telegram chats.
- [ ] **M4.3** Interactive Telegram commands — `/status`, `/stats`, `/pause`, `/resume`, `/test` commands for the bot.
- [ ] **M4.4** Order detail enrichment — follow order links to fetch full description from order detail pages.
- [ ] **M4.5** Web dashboard — simple web UI showing recent orders, filter stats, and bot health.
- [ ] **M4.6** Database backend — replace JSON/JSONL files with SQLite for better querying and scalability.
- [ ] **M4.7** Multi-account support — poll multiple Profi.ru accounts or categories simultaneously.
- [ ] **M4.8** Auto-response — optionally auto-respond to matching orders on Profi.ru (requires careful rate limiting).

## M5 — Testing & CI  *(Phase 5 — Ongoing)*

**Goal:** Ensure code quality and prevent regressions.

- [ ] **M5.1** Add unit tests for `filters.py` (keyword matching, budget extraction, disallowed topic/platform exclusion).
- [ ] **M5.2** Add unit tests for `parser.py` (DOM extraction with mock Playwright locators).
- [ ] **M5.3** Add unit tests for `storage.py` (seen IDs, JSONL append).
- [ ] **M5.4** Add unit tests for `tg_formatter.py` (HTML escaping, truncation, URL handling).
- [ ] **M5.5** Add integration tests for `run_all.py` orchestrator (mock subprocess + Telegram).
- [ ] **M5.6** Set up CI pipeline (GitHub Actions) with linting (ruff/flake8) and test execution.
- [ ] **M5.7** Add type checking (mypy) — codebase already uses type hints in some places.