# Phase 1: Stabilization & Bug Fixes (M1)

**Goal:** Fix known bugs, remove dead code, ensure reliable startup.

## Context

- `run_all.py` is the sole working entry point (parser subprocess + Telegram notifier)
- `tg_bot.py` + `tg_watcher.py` are dead code with 3 bugs, superseded by `run_all.py`
- `tg_formatter.py` has a minor unused-import bug
- No `.env.example` exists — users guess env var names
- No startup validation for Chrome CDP — fails silently if Chrome is not running

## Decisions

- **D1:** Delete `tg_bot.py` and `tg_watcher.py` — dead code, `run_all.py` is the only entry point
- **D2:** Fix `tg_formatter.py` unused import — remove `from html import escape as h`
- **D3:** Add `.env.example` with all env vars documented
- **D4:** Add Chrome CDP startup validation in `run_all.py` — fail fast with clear error

## Tasks (single wave — no file conflicts)

| Task | File(s) | Action |
|---|---|---|
| T1 | `tg_bot.py` | Delete |
| T2 | `tg_watcher.py` | Delete |
| T3 | `tg_formatter.py` | Remove unused import line 3 |
| T4 | `.env.example` | Create with BOT_TOKEN, ADMIN_CHAT_ID, TELEGRAM_PROXY |
| T5 | `run_all.py` | Add CDP reachability check before starting |
| T6 | `.planning/STATE.md` | Update with phase 1 results |
| T7 | git commit | Atomic commit with all changes |

## Acceptance Criteria

- [ ] `tg_bot.py` and `tg_watcher.py` deleted
- [ ] `tg_formatter.py` has no unused import
- [ ] `.env.example` exists with documented vars
- [ ] `run_all.py` checks CDP before starting, exits with clear error if unreachable
- [ ] No other functionality changed
- [ ] Git commit created