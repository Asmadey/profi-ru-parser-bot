# Phase 2: Configuration & Deployment (M2)

**Goal:** Make the project easy to deploy and configure.

## Decisions

- **D1:** Rewrite README to match actual architecture (run_all.py, Chrome CDP, filters.py, .env)
- **D2:** Add `pyproject.toml` with project metadata + dependencies from requirements.txt
- **D3:** Add `Dockerfile` + `docker-compose.yml` — Chrome with --remote-debugging-port=9225 + bot container
- **D4:** Add health check — write heartbeat file (`heartbeat.json`) with timestamp every poll cycle
- **D5:** Add systemd unit file for the bot (not Chrome — Chrome managed separately or via compose)
- **D6:** Move filter config (keyword patterns, budget threshold) to `config.py` Settings dataclass, keep filters.py logic reading from Settings

## Wave 1 (parallel — no file conflicts)

| Task | File(s) | Action |
|---|---|---|
| T1 | `README.md` | Full rewrite — actual architecture, Chrome CDP setup, .env, filters.py |
| T2 | `pyproject.toml` | Create with project metadata, dependencies, tool config |
| T3 | `Dockerfile` | Create — Python 3.11 slim, install deps, run run_all.py |
| T4 | `docker-compose.yml` | Create — Chrome container (CDP 9225) + bot container |
| T5 | `systemd/profi-parser-bot.service` | Create systemd unit |
| T6 | `run_all.py` | Add heartbeat file write in notifier loop |

## Wave 2 (depends on wave 1)

| Task | File(s) | Action |
|---|---|---|
| T7 | `config.py` | Add filter settings (budget threshold, configurable) |
| T8 | `filters.py` | Read budget threshold from Settings instead of hardcoded 10000 |

## Acceptance Criteria

- [ ] README matches actual code (run_all.py, Chrome CDP, .env, filters.py)
- [ ] pyproject.toml exists with dependencies
- [ ] Dockerfile + docker-compose.yml exist
- [ ] systemd unit file exists
- [ ] Heartbeat file written during operation
- [ ] Budget threshold configurable via Settings
- [ ] No existing functionality broken
- [ ] Git commit created