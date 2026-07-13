# Requirements

Inferred from code behavior in the Profi.ru Parser Bot codebase.

---

## Functional Requirements

### REQ-001: Browser-Based Order Parsing
The system shall use Playwright with a real Chromium browser (via Chrome DevTools Protocol on port 9225) to load and render the Profi.ru backoffice order page, ensuring JavaScript-rendered content is fully available.

### REQ-002: Authenticated Session Management
The system shall require a one-time manual login on first run (interactive, non-headless browser) and persist the authenticated session state to `storage_state.json` for reuse across subsequent runs, avoiding repeated logins.

### REQ-003: Order Card Extraction
The system shall extract the following fields from each order card on the Profi.ru backoffice page:
- Order ID (from `data-testid` attribute)
- Title (from `aria-label` or `h3` element)
- Price (from `span[aria-hidden="true"]`)
- Description (from `p` element)
- Location (from `li[aria-label^="Дистанционно"]`)
- Preferred time (from `li[aria-label^="Удобное время"]`)
- Posted time ago (from `span:has-text("назад")`)
- Client name (from `div:has(svg) span`)
- Hyperlink (from `href` attribute)

### REQ-004: Keyword-Based Order Filtering
The system shall filter orders using multi-stage criteria:
1. **Target keywords** — Must contain at least one AI/ML/chatbot development term (ИИ, AI, LLM, ChatGPT, нейросеть, machine learning, Telegram-бот, RAG, LangChain, etc.)
2. **Development intent** — Must contain a development-related verb/noun (разработка, создать, настроить, интеграция, требуется, etc.)
3. **Disallowed topics exclusion** — Must NOT contain marketing/advertising terms (таргет, SMM, контекстная реклама, etc.)
4. **Disallowed platforms exclusion** — Must NOT reference non-target platforms (Instagram, WhatsApp, Facebook, Discord)
5. **Budget threshold** — If a budget is explicitly stated, it must be ≥ 10,000₽

### REQ-005: Order Deduplication
The system shall maintain a persistent set of seen order IDs (`seen_ids.json`) and shall not reprocess or re-send any order whose ID has already been recorded.

### REQ-006: JSONL Order Logging
The system shall append each new matching order as a JSON line to `new_orders.jsonl`, creating an append-only audit log of all matched orders.

### REQ-007: Telegram Notification
The system shall send formatted HTML messages to a configured Telegram chat (`ADMIN_CHAT_ID`) for each new matching order, including title, budget, description (truncated to 3000 chars), link, order ID, preferred time, and posted time.

### REQ-008: Telegram Proxy Support
The system shall connect to the Telegram Bot API through a configurable SOCKS5 proxy (`TELEGRAM_PROXY` env var, default `socks5://127.0.0.1:10808`).

### REQ-009: Telegram Flood Control Handling
The system shall handle `TelegramRetryAfter` exceptions by sleeping for the specified retry duration plus 2 seconds before retrying the message send.

### REQ-010: Human-Like Polling Behavior
The system shall poll the Profi.ru page with randomized human-like delays (base 45 seconds ± 25 seconds jitter) to mimic natural user behavior and minimize ban risk.

### REQ-011: Parser Subprocess Supervision
The system (`run_all.py`) shall launch the parser as a subprocess, pipe its stdout/stderr to the main logger, monitor its exit code, and automatically restart it (up to 50 times) with a 10-second delay between restarts.

### REQ-012: Session Re-Authentication
The system shall detect when the authenticated session has expired (by checking page title for "вход"/"login") and trigger re-authentication via `auth.py` followed by a client restart.

### REQ-013: Network Error Resilience
The system shall handle DNS resolution errors (`err_name_not_resolved`) and internet disconnection errors (`err_internet_disconnected`) with a 20-second sleep, and after 3 consecutive network errors, restart the Playwright client.

### REQ-014: Browser Crash Recovery
The system shall detect browser/page crashes and automatically restart the Playwright client (closing the old context, creating a new CDP connection and page).

### REQ-015: Debug Diagnostics
The system shall save a full-page PNG screenshot and the raw HTML of the page when order cards are not found within the selector timeout, storing them in `logs/debug/` with timestamps.

### REQ-016: Cursor-Based JSONL Tail Reading
The Telegram notifier shall track its read position in `new_orders.jsonl` using a byte-offset cursor (`bot_cursor.json`), enabling it to read only newly appended orders without re-reading the entire file. On first start with an existing file, the cursor shall be initialized to end-of-file.

### REQ-017: Rotating Logging
The system shall use rotating file loggers (2MB max per file, 5 backup files) with separate error-level logs, for each named logger (`run_all`, `bot`, `parser`).

### REQ-018: Graceful Shutdown
The system shall handle `KeyboardInterrupt` by cancelling asyncio tasks, terminating the parser subprocess (with a 5-second timeout before force-kill), and closing the Telegram bot session.

## Non-Functional Requirements

### REQ-019: Anti-Ban Behavior
The system shall use a real browser (not HTTP requests), interact via DOM (like a human user), apply randomized delays between polls, avoid aggressive page reloads, and process only new orders to minimize the risk of account suspension.

### REQ-020: Data Persistence
All state files (`seen_ids.json`, `new_orders.jsonl`, `bot_cursor.json`, `storage_state.json`) shall use human-readable JSON format with UTF-8 encoding and `ensure_ascii=False`.

### REQ-021: Configuration via Environment
Sensitive credentials (`BOT_TOKEN`, `ADMIN_CHAT_ID`, `TELEGRAM_PROXY`) shall be loaded from environment variables via `.env` file using `python-dotenv`, and shall never be hardcoded.

### REQ-022: Text Normalization
The system shall normalize extracted text by replacing special Unicode spaces (`\u202f`, `\xa0`), collapsing whitespace, and stripping leading/trailing spaces. Filter matching shall be case-insensitive and treat `ё` as `е`.

## Integration Requirements

### REQ-023: External Chrome Browser Dependency
The system requires an external Chrome/Chromium browser instance running with remote debugging enabled on port 9225 (CDP endpoint at `http://127.0.0.1:9225/json/version`). The system does not manage this browser lifecycle.

### REQ-024: Telegram Bot API Integration
The system shall use the aiogram 3.x library to send messages via the Telegram Bot API, with HTML parse mode and web page preview disabled.