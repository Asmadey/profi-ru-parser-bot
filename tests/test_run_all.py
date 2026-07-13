"""Integration tests for run_all.py.

These tests exercise the orchestrator module's pure-Python helpers and the
interaction between the cursor/heartbeat mechanism and the notifier loop —
without requiring a real Telegram bot token, network access, or a running
Chrome CDP instance.  External dependencies (Bot, AiohttpSession, subprocess,
Settings) are mocked.

Run with:  pytest -m integration   or   pytest tests/test_run_all.py
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Make the project root importable.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import run_all  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_cursor(tmp_path: Path) -> str:
    """Return a cursor file path inside tmp_path (file does not exist yet)."""
    return str(tmp_path / "cursor.json")


@pytest.fixture
def tmp_orders(tmp_path: Path) -> Path:
    """Return a path for the orders JSONL file (file does not exist yet)."""
    return tmp_path / "orders.jsonl"


# ---------------------------------------------------------------------------
# check_cdp_available
# ---------------------------------------------------------------------------

class TestCheckCdpAvailable:
    """CDP reachability check — pure socket test, no network needed."""

    def test_returns_true_when_socket_connects(self):
        """A socket that accepts connections should return True."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        original_port = run_all.CDP_PORT
        run_all.CDP_PORT = port
        try:
            assert run_all.check_cdp_available() is True
        finally:
            run_all.CDP_PORT = original_port
            srv.close()

    def test_returns_false_when_connection_refused(self):
        """If nothing listens on the port, check should return False."""
        # Use a port that's almost certainly free.
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.close()  # free the port immediately

        original_port = run_all.CDP_PORT
        run_all.CDP_PORT = port
        try:
            assert run_all.check_cdp_available() is False
        finally:
            run_all.CDP_PORT = original_port


# ---------------------------------------------------------------------------
# Cursor persistence — load_cursor / save_cursor round-trip
# ---------------------------------------------------------------------------

class TestCursorRoundTrip:
    def test_load_cursor_missing_file_returns_zero(self, tmp_cursor: str):
        assert run_all.load_cursor(tmp_cursor) == 0

    def test_save_then_load_preserves_offset(self, tmp_cursor: str):
        run_all.save_cursor(tmp_cursor, 12345)
        assert run_all.load_cursor(tmp_cursor) == 12345

    def test_save_cursor_writes_valid_json(self, tmp_cursor: str):
        run_all.save_cursor(tmp_cursor, 99)
        data = json.loads(Path(tmp_cursor).read_text(encoding="utf-8"))
        assert data == {"offset": 99}

    def test_load_cursor_corrupted_file_returns_zero(self, tmp_cursor: str):
        Path(tmp_cursor).write_text("{not json", encoding="utf-8")
        assert run_all.load_cursor(tmp_cursor) == 0

    def test_load_cursor_non_dict_returns_zero(self, tmp_cursor: str):
        Path(tmp_cursor).write_text("[1, 2, 3]", encoding="utf-8")
        assert run_all.load_cursor(tmp_cursor) == 0

    def test_load_cursor_missing_offset_key_returns_zero(self, tmp_cursor: str):
        Path(tmp_cursor).write_text('{"foo": "bar"}', encoding="utf-8")
        assert run_all.load_cursor(tmp_cursor) == 0

    def test_save_cursor_overwrites_previous(self, tmp_cursor: str):
        run_all.save_cursor(tmp_cursor, 10)
        run_all.save_cursor(tmp_cursor, 20)
        assert run_all.load_cursor(tmp_cursor) == 20


# ---------------------------------------------------------------------------
# send_order_message — retry-on-flood-control logic
# ---------------------------------------------------------------------------

class TestSendOrderMessage:
    @pytest.mark.asyncio
    async def test_sends_message_on_first_try(self):
        """A successful send should not retry."""
        bot = MagicMock()
        bot.send_message = AsyncMock()
        log = MagicMock()

        await run_all.send_order_message(bot, log, "hello")

        bot.send_message.assert_awaited_once()
        # First positional arg is the text.
        assert bot.send_message.await_args.args[1] == "hello"

    @pytest.mark.asyncio
    async def test_retries_after_flood_control(self):
        """TelegramRetryAfter should cause a retry, not a crash."""
        from aiogram.exceptions import TelegramRetryAfter

        bot = MagicMock()
        # Build a minimal TelegramMethod stub for the constructor.
        fake_method = MagicMock()
        retry_exc = TelegramRetryAfter(method=fake_method, message="retry", retry_after=0)
        bot.send_message = AsyncMock(
            side_effect=[retry_exc, None],
        )
        log = MagicMock()

        # Patch asyncio.sleep inside run_all to avoid real delay.
        with patch.object(run_all.asyncio, "sleep", new=AsyncMock()):
            await run_all.send_order_message(bot, log, "retry-me")

        assert bot.send_message.await_count == 2


# ---------------------------------------------------------------------------
# telegram_notifier — cursor init & order dispatch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestTelegramNotifier:
    async def test_missing_token_logs_and_returns(self, monkeypatch):
        """No BOT_TOKEN → notifier should log error and return immediately."""
        monkeypatch.setattr(run_all, "BOT_TOKEN", "")
        log = MagicMock()
        await run_all.telegram_notifier(log)
        log.error.assert_called_once()

    async def test_invalid_admin_id_logs_and_returns(self, monkeypatch):
        """BOT_TOKEN present but ADMIN_CHAT_ID == 0 → error + return."""
        monkeypatch.setattr(run_all, "BOT_TOKEN", "fake:token")
        monkeypatch.setattr(run_all, "ADMIN_CHAT_ID", 0)
        log = MagicMock()
        await run_all.telegram_notifier(log)
        log.error.assert_called_once()

    async def test_cursor_initialised_to_end_of_file(
        self, monkeypatch, tmp_orders: Path, tmp_path: Path,
    ):
        """When offset==0 and orders file exists, cursor should jump to EOF."""
        # Write some content to the orders file.
        order1 = {"order_id": "1", "title": "Foo"}
        order2 = {"order_id": "2", "title": "Bar"}
        tmp_orders.write_text(
            json.dumps(order1, ensure_ascii=False) + "\n" + json.dumps(order2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        cursor_path = str(tmp_path / "cursor.json")

        monkeypatch.setattr(run_all, "BOT_TOKEN", "fake:token")
        monkeypatch.setattr(run_all, "ADMIN_CHAT_ID", 100)
        monkeypatch.setattr(run_all, "TELEGRAM_PROXY", "")
        monkeypatch.setattr(run_all, "BOT_POLL_SEC", 0)

        # Mock Settings to point at our tmp files.
        fake_settings = MagicMock()
        fake_settings.out_jsonl_path = str(tmp_orders)
        fake_settings.bot_cursor_path = cursor_path
        monkeypatch.setattr(run_all, "Settings", lambda: fake_settings)

        # Mock the Bot + session so nothing touches the network.
        fake_bot = MagicMock()
        fake_bot.send_message = AsyncMock()
        fake_bot.session.close = AsyncMock()

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=fake_bot)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        # We need to stop the notifier loop after first iteration.
        call_count = {"n": 0}

        async def fake_sleep(_delay):
            call_count["n"] += 1
            if call_count["n"] >= 1:
                raise asyncio.CancelledError()

        with (
            patch.object(run_all, "AiohttpSession", return_value=MagicMock()),
            patch.object(run_all, "Bot", return_value=fake_bot),
            patch.object(run_all.asyncio, "sleep", side_effect=fake_sleep),
        ):
            log = MagicMock()
            try:
                await run_all.telegram_notifier(log)
            except asyncio.CancelledError:
                pass

        # Cursor file should now exist and contain the file size as offset.
        assert os.path.exists(cursor_path)
        saved = json.loads(Path(cursor_path).read_text(encoding="utf-8"))
        assert saved["offset"] == tmp_orders.stat().st_size

    async def test_sends_new_orders_then_advances_cursor(
        self, monkeypatch, tmp_orders: Path, tmp_path: Path,
    ):
        """Orders appended after cursor init should be sent once, then cursor advances."""
        # Pre-existing content (cursor starts here).
        existing = {"order_id": "old", "title": "Old"}
        tmp_orders.write_text(json.dumps(existing, ensure_ascii=False) + "\n", encoding="utf-8")
        initial_offset = tmp_orders.stat().st_size

        cursor_path = str(tmp_path / "cursor.json")
        run_all.save_cursor(cursor_path, initial_offset)

        # Append a new order.
        new_order = {"order_id": "new1", "title": "New Order", "href": "/x"}
        with tmp_orders.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(new_order, ensure_ascii=False) + "\n")

        monkeypatch.setattr(run_all, "BOT_TOKEN", "fake:token")
        monkeypatch.setattr(run_all, "ADMIN_CHAT_ID", 100)
        monkeypatch.setattr(run_all, "TELEGRAM_PROXY", "")
        monkeypatch.setattr(run_all, "BOT_POLL_SEC", 0)
        monkeypatch.setattr(run_all, "is_paused", lambda: False)

        fake_settings = MagicMock()
        fake_settings.out_jsonl_path = str(tmp_orders)
        fake_settings.bot_cursor_path = cursor_path
        monkeypatch.setattr(run_all, "Settings", lambda: fake_settings)

        fake_bot = MagicMock()
        fake_bot.send_message = AsyncMock()
        fake_bot.session.close = AsyncMock()

        call_count = {"n": 0}

        async def fake_sleep(_delay):
            call_count["n"] += 1
            # Allow the first sleep (inside send_order_message) to succeed,
            # cancel on the second (the notifier loop's poll sleep).
            if call_count["n"] >= 2:
                raise asyncio.CancelledError()

        with (
            patch.object(run_all, "AiohttpSession", return_value=MagicMock()),
            patch.object(run_all, "Bot", return_value=fake_bot),
            patch.object(run_all.asyncio, "sleep", side_effect=fake_sleep),
        ):
            log = MagicMock()
            try:
                await run_all.telegram_notifier(log)
            except asyncio.CancelledError:
                pass

        # The new order should have been sent exactly once.
        assert fake_bot.send_message.await_count == 1
        sent_text = fake_bot.send_message.await_args.args[1]
        assert "New Order" in sent_text

        # Cursor should have advanced to EOF.
        saved = json.loads(Path(cursor_path).read_text(encoding="utf-8"))
        assert saved["offset"] == tmp_orders.stat().st_size

    async def test_paused_skips_send_but_advances_cursor(
        self, monkeypatch, tmp_orders: Path, tmp_path: Path,
    ):
        """When paused, orders are read but not sent; cursor still advances."""
        existing = {"order_id": "old", "title": "Old"}
        tmp_orders.write_text(json.dumps(existing, ensure_ascii=False) + "\n", encoding="utf-8")
        initial_offset = tmp_orders.stat().st_size

        cursor_path = str(tmp_path / "cursor.json")
        run_all.save_cursor(cursor_path, initial_offset)

        new_order = {"order_id": "skip1", "title": "Skipped", "href": "/y"}
        with tmp_orders.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(new_order, ensure_ascii=False) + "\n")

        monkeypatch.setattr(run_all, "BOT_TOKEN", "fake:token")
        monkeypatch.setattr(run_all, "ADMIN_CHAT_ID", 100)
        monkeypatch.setattr(run_all, "TELEGRAM_PROXY", "")
        monkeypatch.setattr(run_all, "BOT_POLL_SEC", 0)
        monkeypatch.setattr(run_all, "is_paused", lambda: True)  # PAUSED

        fake_settings = MagicMock()
        fake_settings.out_jsonl_path = str(tmp_orders)
        fake_settings.bot_cursor_path = cursor_path
        monkeypatch.setattr(run_all, "Settings", lambda: fake_settings)

        fake_bot = MagicMock()
        fake_bot.send_message = AsyncMock()
        fake_bot.session.close = AsyncMock()

        call_count = {"n": 0}

        async def fake_sleep(_delay):
            call_count["n"] += 1
            if call_count["n"] >= 1:
                raise asyncio.CancelledError()

        with (
            patch.object(run_all, "AiohttpSession", return_value=MagicMock()),
            patch.object(run_all, "Bot", return_value=fake_bot),
            patch.object(run_all.asyncio, "sleep", side_effect=fake_sleep),
        ):
            log = MagicMock()
            try:
                await run_all.telegram_notifier(log)
            except asyncio.CancelledError:
                pass

        # Nothing sent because we're paused.
        fake_bot.send_message.assert_not_awaited()

        # But cursor still advanced past the new line.
        saved = json.loads(Path(cursor_path).read_text(encoding="utf-8"))
        assert saved["offset"] == tmp_orders.stat().st_size


# ---------------------------------------------------------------------------
# start_parser_process — env sanitisation & subprocess launch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestStartParserProcess:
    async def test_strips_proxy_env_vars(self, monkeypatch):
        """LD_PRELOAD / proxychains env vars should be removed from the child."""
        monkeypatch.setenv("LD_PRELOAD", "/some/lib.so")
        monkeypatch.setenv("LD_LIBRARY_PATH", "/opt/proxychains/lib")
        monkeypatch.setenv("PROXYCHAINS_CONF_FILE", "/etc/proxychains.conf")

        captured_env: dict[str, str] = {}

        async def fake_create_subprocess_exec(exe, script, *, stdout, stderr, env):
            captured_env.update(env)
            proc = MagicMock()
            proc.pid = 999
            proc.stdout = MagicMock()
            proc.stdout.readline = AsyncMock(return_value=b"")
            return proc

        monkeypatch.setattr(run_all.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

        log = MagicMock()
        await run_all.start_parser_process(log)

        assert "LD_PRELOAD" not in captured_env
        assert "LD_LIBRARY_PATH" not in captured_env
        assert "PROXYCHAINS_CONF_FILE" not in captured_env
        assert captured_env.get("PYTHONUTF8") == "1"
        assert captured_env.get("PYTHONIOENCODING") == "utf-8"

    async def test_sets_global_current_parser_proc(self, monkeypatch):
        """The module-level CURRENT_PARSER_PROC should be updated."""

        async def fake_create_subprocess_exec(exe, script, *, stdout, stderr, env):
            proc = MagicMock()
            proc.pid = 42
            proc.stdout = MagicMock()
            proc.stdout.readline = AsyncMock(return_value=b"")
            return proc

        monkeypatch.setattr(run_all.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
        monkeypatch.setattr(run_all, "CURRENT_PARSER_PROC", None)

        log = MagicMock()
        await run_all.start_parser_process(log)
        assert run_all.CURRENT_PARSER_PROC is not None
        assert run_all.CURRENT_PARSER_PROC.pid == 42

        # cleanup
        run_all.CURRENT_PARSER_PROC = None


# ---------------------------------------------------------------------------
# async_main — CDP gate & task orchestration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAsyncMain:
    async def test_exits_when_cdp_unavailable(self, monkeypatch):
        """If CDP is not reachable, async_main should call sys.exit(1)."""
        monkeypatch.setattr(run_all, "check_cdp_available", lambda: False)

        with pytest.raises(SystemExit) as exc_info:
            await run_all.async_main()

        assert exc_info.value.code == 1

    async def test_starts_all_tasks_when_cdp_ok(self, monkeypatch):
        """When CDP is up, async_main should start parser, notifier, and commands tasks."""
        monkeypatch.setattr(run_all, "check_cdp_available", lambda: True)

        started: list[str] = []

        async def fake_supervise_parser(log):
            started.append("supervisor")

        async def fake_notifier(log):
            started.append("notifier")

        async def fake_bot_commands(log):
            started.append("commands")

        monkeypatch.setattr(run_all, "supervise_parser", fake_supervise_parser)
        monkeypatch.setattr(run_all, "telegram_notifier", fake_notifier)
        monkeypatch.setattr(run_all, "run_bot_commands", fake_bot_commands)
        monkeypatch.setattr(run_all, "setup_logger", lambda name: MagicMock())

        # The three fake coroutines complete immediately, so gather returns
        # right away and async_main's finally block runs cleanly.
        try:
            await run_all.async_main()
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass

        assert "supervisor" in started
        assert "notifier" in started
        assert "commands" in started


# ---------------------------------------------------------------------------
# main() sync entry point
# ---------------------------------------------------------------------------

class TestMainEntryPoint:
    def test_keyboard_interrupt_is_swallowed(self, monkeypatch):
        """main() should silently handle KeyboardInterrupt from asyncio.run."""

        def raise_kbint(coro):
            # Consume the coroutine to avoid "never awaited" warning.
            coro.close()
            raise KeyboardInterrupt

        monkeypatch.setattr(run_all.asyncio, "run", raise_kbint)

        # Should not raise.
        run_all.main()

    def test_normal_completion(self, monkeypatch):
        """main() should call asyncio.run with async_main."""

        called = {"yes": False}

        def fake_run(coro):
            called["yes"] = True
            # Consume the coroutine to avoid "never awaited" warning.
            coro.close()

        monkeypatch.setattr(run_all.asyncio, "run", fake_run)
        run_all.main()
        assert called["yes"] is True