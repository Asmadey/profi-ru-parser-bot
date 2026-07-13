"""Interactive Telegram commands for the Profi.ru Parser Bot.

Provides an aiogram 3.x Router (`commands_router`) with admin-only command
handlers: /status, /stats, /pause, /resume, /last, /test, /help.

All handlers are restricted to ``ADMIN_CHAT_ID`` (read from the environment).
Every handler is wrapped in defensive try/except so a single command never
crashes the bot.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from tg_formatter import format_order

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

commands_router = Router(name="commands_router")

# ---------------------------------------------------------------------------
# Constants / file paths
# ---------------------------------------------------------------------------

BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
HEARTBEAT_PATH: str = os.path.join(BASE_DIR, "heartbeat.json")
METRICS_PATH: str = os.path.join(BASE_DIR, "metrics.json")
PAUSE_FLAG_PATH: str = os.path.join(BASE_DIR, "pause.flag")
ORDERS_PATH: str = os.path.join(BASE_DIR, "new_orders.jsonl")

HEARTBEAT_TTL_SEC: int = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_admin_id() -> int:
    """Return ``ADMIN_CHAT_ID`` from the environment as an int.

    Raises ``RuntimeError`` if the variable is missing or not a valid integer.
    """
    raw = os.environ.get("ADMIN_CHAT_ID", "").strip()
    if not raw:
        raise RuntimeError("ADMIN_CHAT_ID is not set in the environment")
    return int(raw)


def is_paused() -> bool:
    """Return ``True`` if ``pause.flag`` exists, ``False`` otherwise."""
    return os.path.exists(PAUSE_FLAG_PATH)


def _read_json(path: str) -> dict[str, Any] | None:
    """Safely read a JSON file. Return ``None`` on any error."""
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _fmt_uptime(seconds: float) -> str:
    """Format an uptime duration into a short human-readable string."""
    if seconds < 0:
        return "—"
    days = int(seconds // 86_400)
    hours = int((seconds % 86_400) // 3_600)
    mins = int((seconds % 3_600) // 60)
    secs = int(seconds % 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}д")
    if hours:
        parts.append(f"{hours}ч")
    if mins:
        parts.append(f"{mins}м")
    if not parts:
        parts.append(f"{secs}с")
    return " ".join(parts)


def _fmt_age(seconds: float) -> str:
    """Format how long ago something happened."""
    if seconds < 0:
        return "—"
    return _fmt_uptime(seconds) + " назад"


# ---------------------------------------------------------------------------
# Admin guard
# ---------------------------------------------------------------------------

def _is_admin(message: Message) -> bool:
    """Check whether *message* originates from the admin chat."""
    try:
        return message.chat.id == get_admin_id()
    except (RuntimeError, ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

@commands_router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Show parser heartbeat, uptime, and last poll time."""
    if not _is_admin(message):
        return
    try:
        hb = _read_json(HEARTBEAT_PATH)
        now = time.time()

        if hb and "timestamp" in hb:
            age = now - float(hb.get("timestamp", 0))
            alive = age < HEARTBEAT_TTL_SEC
            heart = "🟢 <b>Парсер работает</b>" if alive else "🔴 <b>Парсер не отвечает</b>"
            heartbeat_line = f"{heart}\n⏱ Heartbeat: {_fmt_age(age)}"
            hb_status = str(hb.get("status", "—"))
            heartbeat_line += f"\n📌 Статус: {hb_status}"
        else:
            heartbeat_line = "🟡 <b>Heartbeat не найден</b>"

        metrics = _read_json(METRICS_PATH) or {}
        start_time = float(metrics.get("start_time", 0))
        uptime_str = _fmt_uptime(now - start_time) if start_time else "—"

        last_poll = float(metrics.get("last_poll_time", 0))
        last_poll_str = _fmt_age(now - last_poll) if last_poll else "—"

        paused = "⏸ <b>Парсинг на паузе</b>" if is_paused() else "▶️ Парсинг активен"

        text = (
            f"{heartbeat_line}\n\n"
            f"⏳ <b>Uptime:</b> {uptime_str}\n"
            f"🔄 <b>Последний опрос:</b> {last_poll_str}\n"
            f"{paused}"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"⚠️ Ошибка /status: {exc}")


@commands_router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Show all metrics counters with emojis."""
    if not _is_admin(message):
        return
    try:
        data = _read_json(METRICS_PATH) or {}
        now = time.time()
        uptime = _fmt_uptime(now - float(data.get("start_time", 0)))

        lines = [
            "📊 <b>Статистика</b>\n",
            f"🔍 Заказов распарсено: <b>{data.get('orders_parsed', 0)}</b>",
            f"✅ Совпадений фильтра: <b>{data.get('orders_matched', 0)}</b>",
            f"📤 Сообщений отправлено: <b>{data.get('orders_sent', 0)}</b>",
            f"⚠️ Ошибок парсинга: <b>{data.get('parse_errors', 0)}</b>",
            f"🔁 Перезапусков: <b>{data.get('restart_count', 0)}</b>",
            f"⏳ Uptime: <b>{uptime}</b>",
        ]
        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"⚠️ Ошибка /stats: {exc}")


@commands_router.message(Command("pause"))
async def cmd_pause(message: Message) -> None:
    """Create ``pause.flag`` to pause parsing."""
    if not _is_admin(message):
        return
    try:
        if is_paused():
            await message.answer("⏸ Парсинг уже на паузе.")
            return
        # touch the flag file
        with open(PAUSE_FLAG_PATH, "w", encoding="utf-8") as fh:
            fh.write(str(time.time()))
        await message.answer("⏸ Парсинг <b>приостановлен</b>.\nДля возобновления: /resume", parse_mode="HTML")
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"⚠️ Ошибка /pause: {exc}")


@commands_router.message(Command("resume"))
async def cmd_resume(message: Message) -> None:
    """Remove ``pause.flag`` to resume parsing."""
    if not _is_admin(message):
        return
    try:
        if not is_paused():
            await message.answer("▶️ Парсинг уже активен.")
            return
        os.remove(PAUSE_FLAG_PATH)
        await message.answer("▶️ Парсинг <b>возобновлён</b>.", parse_mode="HTML")
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"⚠️ Ошибка /resume: {exc}")


@commands_router.message(Command("last"))
async def cmd_last(message: Message) -> None:
    """Show the last 5 orders from ``new_orders.jsonl``."""
    if not _is_admin(message):
        return
    try:
        if not os.path.exists(ORDERS_PATH):
            await message.answer("📭 Файл заказов не найден.")
            return

        # Read the whole file, take last 5 non-empty lines
        orders: list[dict[str, Any]] = []
        try:
            with open(ORDERS_PATH, "r", encoding="utf-8") as fh:
                lines = [ln.strip() for ln in fh if ln.strip()]
        except OSError:
            await message.answer("⚠️ Не удалось прочитать файл заказов.")
            return

        for raw_line in lines[-5:]:
            try:
                orders.append(json.loads(raw_line))
            except json.JSONDecodeError:
                continue

        if not orders:
            await message.answer("📭 Нет заказов для отображения.")
            return

        for order in orders:
            try:
                text = format_order(order)
            except Exception:  # noqa: BLE001
                text = f"⚠️ Не удалось отформатировать заказ: {order.get('order_id', '?')}"
            try:
                await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
            except Exception:  # noqa: BLE001
                pass

    except Exception as exc:  # noqa: BLE001
        await message.answer(f"⚠️ Ошибка /last: {exc}")


@commands_router.message(Command("test"))
async def cmd_test(message: Message) -> None:
    """Send a test message formatted with ``format_order()``."""
    if not _is_admin(message):
        return
    try:
        fake_order: dict[str, Any] = {
            "title": "Тестовый заказ — Репетитор по математике",
            "price": "от 1500 до 3000 ₽ / 60 мин.",
            "description": (
                "Требуется репетитор по математике для подготовки к ЕГЭ. "
                "Ученик 11 класс, нужен системный подход и разбор пробных вариантов."
            ),
            "href": "https://profi.ru/example/test-order/",
            "order_id": "TEST-0001",
            "preferred_time": "по будням после 18:00",
            "posted_ago": "5 минут назад",
        }
        text = format_order(fake_order)
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"⚠️ Ошибка /test: {exc}")


@commands_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """List all available commands with descriptions."""
    if not _is_admin(message):
        return
    try:
        lines = [
            "ℹ️ <b>Команды бота</b>\n",
            "/status — состояние парсера, heartbeat, uptime, последний опрос",
            "/stats — статистика по счётчикам метрик",
            "/pause — приостановить парсинг (создаёт pause.flag)",
            "/resume — возобновить парсинг (удаляет pause.flag)",
            "/last — показать последние 5 заказов",
            "/test — отправить тестовое сообщение с фейковым заказом",
            "/help — показать этот список команд",
        ]
        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"⚠️ Ошибка /help: {exc}")