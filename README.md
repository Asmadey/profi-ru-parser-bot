# Profi.ru Parser Bot

Telegram-бот для автоматического мониторинга бэкофиса Profi.ru. Парсит новые заказы, фильтрует по настраиваемым специальностям (multi-specialty), обогащает деталями со страницы заказа, и отправляет уведомления в Telegram с интерактивными командами управления.

## Возможности

### Парсинг и фильтрация
- Парсинг ленты заказов Profi.ru через Playwright + Chrome DevTools Protocol (CDP)
- **Multi-specialty** — настраиваемые наборы ключевых слов для разных доменов (AI/ML, Web Dev, Data Science)
- Фильтрация по 35+ ключевым словам (ИИ, ML, чат-боты, парсеры, CRM, автоматизация — RU + EN)
- Отсев нерелевантных тем (таргетинг/реклама/SMM) и запрещённых платформ (Instagram, WhatsApp, Facebook, Discord)
- Проверка бюджета (настраиваемый порог, по умолчанию ≥ 10 000 ₽)
- Дедупликация заказов (seen\_ids)

### Обогащение заказов
- Автоматический переход на страницу заказа для извлечения полного описания
- Дополнительные поля: рейтинг клиента, количество откликов, вложения, категория
- Rate-limited (3с между запросами, max 5 за цикл)
- Graceful fallback: при ошибке возвращается исходный заказ

### Telegram-уведомления
- Отправка в Telegram через SOCKS5-прокси
- HTML-форматирование с эмодзи
- Flood control (TelegramRetryAfter)
- **Интерактивные команды**: `/status`, `/stats`, `/pause`, `/resume`, `/last`, `/test`, `/help`

### Надёжность
- Exponential backoff при повторных ошибках (5с × 2ⁿ, макс 900с)
- Автоматический re-auth при истечении сессии (> 24ч)
- Обработка сетевых ошибок (DNS, disconnect) с 3-strike restart
- Восстановление при краше браузера
- Graceful recovery при повреждении seen\_ids.json
- Pause/resume через файл-флаг

### Наблюдаемость
- Структурированное логирование (текст + JSON формат)
- Метрики: parsed, matched, sent, errors, restarts, uptime
- Telegram-алерты на критические ошибки
- Data retention: автоочистка скриншотов (7 дней), трим JSONL (10k строк)
- Heartbeat-файл для внешнего мониторинга

### Тестирование и CI
- 205 unit + integration тестов (pytest)
- GitHub Actions CI: ruff lint + pytest (matrix Python 3.10/3.11/3.12)
- mypy type checking
- pytest-asyncio для async-тестов

## Технологии

| Технология | Назначение |
|---|---|
| **Python 3.10+** | Основной язык |
| **Playwright 1.57** | Автоматизация браузера через CDP |
| **aiogram 3.24** | Telegram Bot API (async) |
| **aiohttp** | HTTP-сессия для Telegram с поддержкой SOCKS5 |
| **asyncio** | Оркестрация парсера, нотификатора и команд |
| **python-dotenv** | Загрузка переменных окружения (`.env`) |
| **PyYAML** | Конфигурация specialities |
| **pytest 9.x** | Unit + integration тесты |
| **ruff** | Линтер |
| **mypy** | Типизация |

## Архитектура

Проект работает как единый процесс `run_all.py`, запускающий три параллельных async-задачи:

```
                     run_all.py  (точка входа — оркестратор)
                    ┌──────┬────────────────┬──────────────────┐
                    │      │                │                  │
          supervise_parser()  telegram_notifier()  run_bot_commands()
          (asyncio task)      (asyncio task)       (asyncio task)
                    │                │                  │
                    ▼                ▼                  ▼
         ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐
         │  main.py        │  │  JSONL tail      │  │  aiogram       │
         │  (subprocess)   │  │  (cursor-based)  │  │  Dispatcher    │
         │                 │  │                  │  │  (polling)      │
         │  Playwright     │  │  format_order()  │  │                │
         │  ┌── CDP ──►    │  │  → send_message  │  │  /status       │
         │  │  Chrome:9225 │  │  (SOCKS5 proxy)  │  │  /stats        │
         │  │              │  │  (flood control)  │  │  /pause        │
         │  │ auth.py      │  │  (pause-aware)   │  │  /resume       │
         │  │ client.py    │  └──────────────────┘  │  /last        │
         │  │ parser.py    │                        │  /test        │
         │  │ filters.py   │                        │  /help        │
         │  │ specialties  │                        └────────────────┘
         │  │ enricher.py  │
         │  │ storage.py   │
         │  └─────────────│
         │                 │
         │  new_orders.jsonl ────► (общий файл между процессами)
         └─────────────────┘
```

### Поток данных

1. **`run_all.py`** запускает три параллельных asyncio-компонента.
2. **Парсер** (сабпроцесс `main.py`):
   - Подключается к Chrome через CDP (порт 9225)
   - Загружает `storage_state.json` для авторизованной сессии
   - Опрашивает backoffice Profi.ru с человекоподобными задержками (45±25с)
   - Извлекает карточки заказов из DOM (`parser.py`)
   - Фильтрует через `match_specialties()` — заказ может匹配 несколько специальностей
   - Обогащает через `enricher.py` — открывает страницу заказа в новой вкладке
   - Дедуплицирует через `seen_ids.json`
   - Дописывает подходящие заказы в `new_orders.jsonl`
   - Проверяет `pause.flag` — если пауза, пропускает цикл
3. **Нотификатор** (в `run_all.py`):
   - Читает `new_orders.jsonl` через байтовый курсор (`bot_cursor.json`)
   - Форматирует заказ через `tg_formatter.py`
   - Проверяет `pause.flag` — если пауза, пропускает отправку (курсор продолжает)
   - Отправляет в Telegram через SOCKS5-прокси с flood control
4. **Командный Dispatcher** (в `run_all.py`):
   - aiogram Dispatcher с Router из `bot_commands.py`
   - Обрабатывает /status, /stats, /pause, /resume, /last, /test, /help
   - Регистрирует команды в Telegram Bot API при старте

## Требования

- **Python 3.10+**
- **Chrome / Chromium** с удалённой отладкой на порту 9225 — должен быть запущен **до** старта бота:

  ```bash
  google-chrome --remote-debugging-port=9225 --user-data-dir=/tmp/chrome-profi
  ```

  Бот подключается к уже запущенному браузеру через CDP; сам он Chrome не запускает.

## Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Asmadey/profi-ru-parser-bot.git
cd profi-ru-parser-bot

# 2. Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Установить браузеры Playwright
playwright install

# 5. Создать .env из примера
cp .env.example .env
# Заполнить BOT_TOKEN, ADMIN_CHAT_ID, TELEGRAM_PROXY
```

### Переменные окружения (`.env`)

| Переменная | Описание | По умолчанию |
|---|---|---|
| `BOT_TOKEN` | Токен Telegram-бота от [@BotFather](https://t.me/BotFather) | — |
| `ADMIN_CHAT_ID` | ID чата для уведомлений | — |
| `TELEGRAM_PROXY` | SOCKS5-прокси для Telegram API | `socks5://127.0.0.1:10808` |
| `LOG_FORMAT` | Формат логов: `json` или текст | текст |

## Запуск

```bash
python run_all.py
```

### Первый запуск

При первом запуске откроется окно Chrome для ручного входа в аккаунт Profi.ru. После авторизации сессия сохраняется в `storage_state.json`, и последующие запуски используют сохранённую сессию автоматически. Сессия обновляется каждые 24 часа (proactive re-auth).

### Docker

```bash
# Сборка и запуск через docker-compose
docker-compose up -d

# Или через Docker
docker build -t profi-parser-bot .
docker run -d --env-file .env profi-parser-bot
```

### systemd

```bash
sudo cp systemd/profi-parser-bot.service /etc/systemd/system/
sudo systemctl enable --now profi-parser-bot
```

## Multi-specialty конфигурация

Создайте `specialties.yaml` для настройки нескольких специальностей:

```yaml
- name: AI/ML
  target_keywords:
    - "(?iu)\\bbot\\b"
    - "(?iu)\\bчат[- ]?бот\\b"
    - "(?iu)\\bавтоматизац\\w*\\b"
  dev_keywords:
    - разработка
    - создать
    - настроить
  disallowed_topics:
    - таргет
    - смм
  disallowed_platforms:
    - "(?iu)\\binstagram\\b"
  budget_min: 10000
  chat_id: null  # или ID Telegram-чата для этой специальности

- name: Web Development
  target_keywords:
    - "(?iu)\\breact\\b"
    - "(?iu)\\bvue\\b"
    - "(?iu)\\bdjango\\b"
  dev_keywords:
    - разработка
    - frontend
    - backend
  budget_min: 15000
  chat_id: null
```

См. `specialties.yaml.example` с 3 готовыми специальностями (AI/ML, Web Dev, Data Science).

Если `specialties.yaml` не существует, используется `DEFAULT_SPECIALTY` (встроенные паттерны из `filters.py`).

## Команды Telegram-бота

| Команда | Описание |
|---|---|
| `/status` | Состояние парсера: heartbeat, uptime, последний опрос, пауза |
| `/stats` | Метрики: распарсено, совпадений, отправлено, ошибок, restarts |
| `/pause` | Приостановить парсинг (создаёт `pause.flag`) |
| `/resume` | Возобновить парсинг (удаляет `pause.flag`) |
| `/last` | Последние 5 заказов из `new_orders.jsonl` |
| `/test` | Тестовое сообщение с фейковым заказом |
| `/help` | Список команд |

Все команды доступны только из чата `ADMIN_CHAT_ID`.

## Фильтрация заказов

Заказ проходит в уведомления, если выполняются **все** условия (проверяются для каждой специальности):

| Критерий | Логика |
|---|---|
| **Целевые ключевые слова** | Паттерны специальности (RU+EN): бот/чат-бот/bot, CRM/ЦРМ, парсер/parse, автоматизация/automation и др. |
| **Намерение разработки** | Маркеры: разработка, создать, написать, настроить, внедрить, интеграция, требуется, нужен |
| **Запрещённые темы** | Отсев: таргет, SMM, контекстная реклама, продвижение |
| **Запрещённые платформы** | Отсев: Instagram, WhatsApp, Facebook, Discord |
| **Бюджет** | ≥ `budget_min` специальности (если указан; если не указан — пропускается) |

Заказ может匹配 несколько специальностей — тогда в `order["matched_specialties"]` сохраняется список имён.

## Структура проекта

| Файл | Назначение |
|---|---|
| `run_all.py` | Точка входа: оркестратор (parser + notifier + commands) |
| `main.py` | Сабпроцесс парсера: цикл опроса, multi-specialty, enrichment, pause |
| `client.py` | `ProfiClient` — обёртка над Playwright |
| `auth.py` | Авторизация на Profi.ru (ручной логин + proactive re-auth) |
| `parser.py` | Извлечение карточек заказов из DOM |
| `filters.py` | Фильтрация: order\_matches\_filter, order\_matches\_specialty, match\_specialties |
| `specialties.py` | `Specialty` dataclass, `load_specialties()` из YAML |
| `enricher.py` | Обогащение заказов: full\_description, rating, responses, attachments |
| `bot_commands.py` | aiogram Router: 7 интерактивных команд |
| `storage.py` | seen\_ids + JSONL + corruption recovery |
| `tg_formatter.py` | Форматирование заказа в HTML-сообщение |
| `logger_setup.py` | Логирование: rotating + JSON формат |
| `metrics.py` | Счётчики метрик с JSON-персистенцией |
| `alerting.py` | Telegram-алерты на критические ошибки |
| `cleanup.py` | Data retention: скриншоты (7д), JSONL trim (10k) |
| `config.py` | Settings dataclass (URL, таймауты, пути, specialties\_path) |
| `.env.example` | Шаблон переменных окружения |
| `specialties.yaml.example` | 3 примера специальностей |

## Тестирование

```bash
# Установить dev-зависимости
pip install -r requirements-dev.txt

# Запустить все тесты
pytest tests/ -v

# С покрытием
pytest tests/ -v --cov=. --cov-report=term-missing

# Только определённый модуль
pytest tests/test_filters.py -v

# Линт
ruff check .

# Типизация
mypy filters.py specialties.py storage.py tg_formatter.py
```

### CI

GitHub Actions workflow (`.github/workflows/ci.yml`) запускается на push и PR:
- **Lint**: ruff check
- **Test**: pytest с покрытием, matrix Python 3.10 / 3.11 / 3.12

## Runtime-артефакты

Эти файлы создаются во время работы бота (не входят в репозиторий):

| Артефакт | Назначение |
|---|---|
| `storage_state.json` | Сохранённая сессия Profi.ru (cookies, localStorage) |
| `seen_ids.json` | Множество ID уже обработанных заказов |
| `new_orders.jsonl` | Лог прошедших фильтр заказов (по строкам JSON) |
| `bot_cursor.json` | Байтовый курсор чтения JSONL нотификатором |
| `metrics.json` | Метрики (parsed, matched, sent, errors, restarts, uptime) |
| `heartbeat.json` | Heartbeat-файл для мониторинга alive-статуса |
| `pause.flag` | Флаг паузы парсинга (создаётся /pause, удаляется /resume) |
| `logs/` | Логи парсера, нотификатора, команд + отладочные дампы |
| `logs/debug/` | Скриншоты и HTML-дампы при ошибках парсинга |

## Лицензия

MIT