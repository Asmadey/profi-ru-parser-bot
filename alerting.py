"""
Critical error alerting for the Profi.ru Parser Bot.

Sends alert messages to the admin Telegram chat via aiogram.
Never raises — always returns True on success, False on failure.
"""

import asyncio
import os

from dotenv import load_dotenv
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "0").strip()
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY", "socks5://127.0.0.1:10808").strip()

_LEVEL_ICONS = {
    "CRITICAL": "🔴",
    "WARNING": "⚠️",
    "INFO": "ℹ️",
}


async def send_alert(message: str, level: str = "CRITICAL") -> bool:
    """Send an alert message to the admin Telegram chat.

    Args:
        message: The alert text body.
        level: One of 'CRITICAL', 'WARNING', 'INFO'. Controls the prefix icon.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    try:
        token = BOT_TOKEN
        chat_id_raw = ADMIN_CHAT_ID

        if not token:
            print("[alerting] BOT_TOKEN is not set")
            return False

        try:
            chat_id = int(chat_id_raw)
        except ValueError:
            print("[alerting] ADMIN_CHAT_ID is invalid: %r" % chat_id_raw)
            return False

        icon = _LEVEL_ICONS.get(level.upper(), "🔴")
        text = f"{icon} [{level.upper()}]\n{message}"

        session = AiohttpSession(proxy=TELEGRAM_PROXY)
        bot = Bot(token=token, session=session)

        try:
            await bot.send_message(chat_id, text, disable_web_page_preview=True)
            return True
        finally:
            await bot.session.close()

    except Exception as exc:
        print("[alerting] Failed to send alert: %s" % exc)
        return False


def send_alert_sync(message: str, level: str = "CRITICAL") -> bool:
    """Synchronous wrapper around send_alert using asyncio.run()."""
    try:
        return asyncio.run(send_alert(message, level=level))
    except Exception as exc:
        print("[alerting] send_alert_sync failed: %s" % exc)
        return False


if __name__ == "__main__":
    ok = send_alert_sync("Test alert from alerting.py", level="INFO")
    if ok:
        print("Test alert sent successfully.")
    else:
        print("Test alert FAILED.")