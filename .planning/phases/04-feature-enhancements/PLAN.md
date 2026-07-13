# Phase 4 — Feature Enhancements (M4)

## Goal
Expand bot functionality: multi-specialty filtering, interactive Telegram commands, order detail enrichment.

## Tasks

### M4.1 — Multi-Specialty Support
**Files:** `specialties.py` (new), `filters.py` (modify), `config.py` (modify)
- Create `specialties.py` with `Specialty` dataclass and `load_specialties()` from YAML
- Each specialty: name, target_keywords (regex list), dev_keywords (list), disallowed_topics (list), disallowed_platforms (regex list), budget_min, chat_id (optional)
- `filters.py`: `order_matches_filter()` accepts a `Specialty` param; default falls back to built-in patterns
- `config.py`: add `specialties_path` setting (default: `specialties.yaml`)
- Create `specialties.yaml.example` with 3 example specialties (AI/ML, Web Dev, Data Science)

### M4.3 — Interactive Telegram Commands
**Files:** `bot_commands.py` (new), `run_all.py` (modify in wave 2)
- Create `bot_commands.py` with aiogram Router containing handlers:
  - `/status` — bot alive, parser running, last poll time, uptime
  - `/stats` — metrics from metrics.json
  - `/pause` — set pause flag (parser stops processing new orders)
  - `/resume` — clear pause flag
  - `/last` — show last 5 matched orders from JSONL
  - `/test` — send a test formatted message
  - `/help` — list available commands
- Pause state via `pause.flag` file (simple, cross-process)
- Router is importable and can be included in a Dispatcher

### M4.4 — Order Detail Enrichment
**Files:** `enricher.py` (new), `main.py` (modify in wave 2)
- Create `enricher.py` with `enrich_order(page, order_dict)` function
- Opens order href in a new tab (same browser context)
- Extracts: full description, client info, attachments count, response count
- Returns enriched dict (original fields + new `detail` key)
- Rate-limited: 2-3 second delay between enrichment visits
- Timeout: 15s per page, graceful failure (returns original dict on error)

## Wave Plan

### Wave 1 (parallel, independent files)
- Task A: `specialties.py` + `filters.py` + `config.py` + `specialties.yaml.example`
- Task B: `bot_commands.py` (standalone router)
- Task C: `enricher.py` (standalone module)

### Wave 2 (parallel, integration)
- Task D: Integrate `bot_commands.py` into `run_all.py` — add Dispatcher polling
- Task E: Integrate `enricher.py` + multi-specialty into `main.py`

## Acceptance Criteria
1. `specialties.yaml` can define multiple specialties with different keyword sets
2. `filters.py` applies the correct specialty filter based on config
3. Bot responds to /status, /stats, /pause, /resume, /last, /test, /help
4. /pause stops processing, /resume continues
5. Enricher fetches full order details without crashing on errors
6. Enrichment is rate-limited and graceful on failure
7. All existing functionality preserved (no regressions)