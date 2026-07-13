"""Unit tests for bot_commands.py — helpers, admin guard, and command handlers.

Requires aiogram (installed in the test environment). Async handlers are
exercised with mocked Message objects whose .answer is an AsyncMock.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import bot_commands as bc


# ---------------------------------------------------------------------------
# is_paused
# ---------------------------------------------------------------------------

class TestIsPaused:
    def test_flag_exists_true(self, tmp_path, monkeypatch):
        flag = tmp_path / "pause.flag"
        flag.write_text("now")
        monkeypatch.setattr(bc, "PAUSE_FLAG_PATH", str(flag))
        assert bc.is_paused() is True

    def test_flag_missing_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bc, "PAUSE_FLAG_PATH", str(tmp_path / "nofile.flag"))
        assert bc.is_paused() is False


# ---------------------------------------------------------------------------
# get_admin_id
# ---------------------------------------------------------------------------

class TestGetAdminId:
    def test_valid_env(self, monkeypatch):
        monkeypatch.setenv("ADMIN_CHAT_ID", "123456")
        assert bc.get_admin_id() == 123456

    def test_missing_env_raises(self, monkeypatch):
        monkeypatch.delenv("ADMIN_CHAT_ID", raising=False)
        with pytest.raises(RuntimeError):
            bc.get_admin_id()

    def test_empty_env_raises(self, monkeypatch):
        monkeypatch.setenv("ADMIN_CHAT_ID", "   ")
        with pytest.raises(RuntimeError):
            bc.get_admin_id()

    def test_non_int_raises(self, monkeypatch):
        monkeypatch.setenv("ADMIN_CHAT_ID", "abc")
        with pytest.raises(ValueError):
            bc.get_admin_id()


# ---------------------------------------------------------------------------
# _fmt_uptime
# ---------------------------------------------------------------------------

class TestFmtUptime:
    def test_zero(self):
        assert bc._fmt_uptime(0) == "0с"

    def test_65_seconds(self):
        # 65s → 1m, seconds dropped when a larger unit present
        assert bc._fmt_uptime(65) == "1м"

    def test_3661(self):
        assert bc._fmt_uptime(3661) == "1ч 1м"

    def test_90061(self):
        assert bc._fmt_uptime(90061) == "1д 1ч 1м"

    def test_negative(self):
        assert bc._fmt_uptime(-1) == "—"

    def test_seconds_only(self):
        assert bc._fmt_uptime(5) == "5с"


# ---------------------------------------------------------------------------
# _fmt_age
# ---------------------------------------------------------------------------

class TestFmtAge:
    def test_60_seconds(self):
        assert bc._fmt_age(60) == "1м назад"

    def test_negative(self):
        assert bc._fmt_age(-1) == "—"

    def test_zero(self):
        assert bc._fmt_age(0) == "0с назад"


# ---------------------------------------------------------------------------
# _read_json
# ---------------------------------------------------------------------------

class TestReadJson:
    def test_valid_dict(self, tmp_path):
        p = tmp_path / "f.json"
        p.write_text('{"a": 1}', encoding="utf-8")
        assert bc._read_json(str(p)) == {"a": 1}

    def test_missing_file(self, tmp_path):
        assert bc._read_json(str(tmp_path / "no.json")) is None

    def test_corrupted(self, tmp_path):
        p = tmp_path / "f.json"
        p.write_text("{bad json", encoding="utf-8")
        assert bc._read_json(str(p)) is None

    def test_not_a_dict(self, tmp_path):
        p = tmp_path / "f.json"
        p.write_text("[1, 2, 3]", encoding="utf-8")
        assert bc._read_json(str(p)) is None

    def test_string_value(self, tmp_path):
        p = tmp_path / "f.json"
        p.write_text('"just a string"', encoding="utf-8")
        assert bc._read_json(str(p)) is None


# ---------------------------------------------------------------------------
# _is_admin
# ---------------------------------------------------------------------------

def _make_message(chat_id):
    msg = MagicMock()
    msg.chat.id = chat_id
    msg.answer = AsyncMock()
    return msg


class TestIsAdmin:
    def test_matching_id(self, monkeypatch):
        monkeypatch.setenv("ADMIN_CHAT_ID", "100")
        msg = _make_message(100)
        assert bc._is_admin(msg) is True

    def test_non_matching_id(self, monkeypatch):
        monkeypatch.setenv("ADMIN_CHAT_ID", "100")
        msg = _make_message(999)
        assert bc._is_admin(msg) is False

    def test_missing_env_returns_false(self, monkeypatch):
        monkeypatch.delenv("ADMIN_CHAT_ID", raising=False)
        msg = _make_message(100)
        assert bc._is_admin(msg) is False


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_env(monkeypatch):
    monkeypatch.setenv("ADMIN_CHAT_ID", "100")
    return 100


@pytest.mark.asyncio
class TestCommandHandlers:
    async def test_cmd_status_admin_calls_answer(self, admin_env, tmp_path, monkeypatch):
        # point file paths at tmp_path / nonexistent so reads return None gracefully
        monkeypatch.setattr(bc, "HEARTBEAT_PATH", str(tmp_path / "no_hb.json"))
        monkeypatch.setattr(bc, "METRICS_PATH", str(tmp_path / "no_metrics.json"))
        monkeypatch.setattr(bc, "PAUSE_FLAG_PATH", str(tmp_path / "no.flag"))

        msg = _make_message(100)
        await bc.cmd_status(msg)
        assert msg.answer.await_count >= 1
        # Should not be the error branch (no "Ошибка" since files missing is handled)
        first_call_text = msg.answer.await_args_list[0].args[0]
        assert "Heartbeat" in first_call_text or "heartbeat" in first_call_text.lower()

    async def test_cmd_status_non_admin_silent(self, admin_env):
        msg = _make_message(999)
        await bc.cmd_status(msg)
        msg.answer.assert_not_awaited()

    async def test_cmd_stats_admin_calls_answer(self, admin_env, tmp_path, monkeypatch):
        monkeypatch.setattr(bc, "METRICS_PATH", str(tmp_path / "no_metrics.json"))
        msg = _make_message(100)
        await bc.cmd_stats(msg)
        msg.answer.assert_awaited_once()
        text = msg.answer.await_args.args[0]
        assert "Статистика" in text

    async def test_cmd_stats_non_admin_silent(self, admin_env):
        msg = _make_message(999)
        await bc.cmd_stats(msg)
        msg.answer.assert_not_awaited()

    async def test_cmd_pause_creates_flag(self, admin_env, tmp_path, monkeypatch):
        flag = tmp_path / "pause.flag"
        monkeypatch.setattr(bc, "PAUSE_FLAG_PATH", str(flag))
        msg = _make_message(100)
        await bc.cmd_pause(msg)
        assert flag.exists()
        msg.answer.assert_awaited_once()
        assert "приостановлен" in msg.answer.await_args.args[0]

    async def test_cmd_pause_already_paused(self, admin_env, tmp_path, monkeypatch):
        flag = tmp_path / "pause.flag"
        flag.write_text("x")
        monkeypatch.setattr(bc, "PAUSE_FLAG_PATH", str(flag))
        msg = _make_message(100)
        await bc.cmd_pause(msg)
        msg.answer.assert_awaited_once()
        assert "уже на паузе" in msg.answer.await_args.args[0]

    async def test_cmd_resume_removes_flag(self, admin_env, tmp_path, monkeypatch):
        flag = tmp_path / "pause.flag"
        flag.write_text("x")
        monkeypatch.setattr(bc, "PAUSE_FLAG_PATH", str(flag))
        msg = _make_message(100)
        await bc.cmd_resume(msg)
        assert not flag.exists()
        msg.answer.assert_awaited_once()
        assert "возобновлён" in msg.answer.await_args.args[0]

    async def test_cmd_resume_already_active(self, admin_env, tmp_path, monkeypatch):
        monkeypatch.setattr(bc, "PAUSE_FLAG_PATH", str(tmp_path / "noflag"))
        msg = _make_message(100)
        await bc.cmd_resume(msg)
        msg.answer.assert_awaited_once()
        assert "уже активен" in msg.answer.await_args.args[0]

    async def test_cmd_last_no_file(self, admin_env, tmp_path, monkeypatch):
        monkeypatch.setattr(bc, "ORDERS_PATH", str(tmp_path / "no.jsonl"))
        msg = _make_message(100)
        await bc.cmd_last(msg)
        msg.answer.assert_awaited_once()
        assert "не найден" in msg.answer.await_args.args[0]

    async def test_cmd_last_with_orders(self, admin_env, tmp_path, monkeypatch):
        path = tmp_path / "orders.jsonl"
        orders = [
            {"title": f"Order {i}", "order_id": str(i), "href": f"/x{i}"}
            for i in range(3)
        ]
        path.write_text("\n".join(json.dumps(o) for o in orders), encoding="utf-8")
        monkeypatch.setattr(bc, "ORDERS_PATH", str(path))
        msg = _make_message(100)
        await bc.cmd_last(msg)
        # one answer per order
        assert msg.answer.await_count == 3

    async def test_cmd_test_sends_formatted(self, admin_env):
        msg = _make_message(100)
        await bc.cmd_test(msg)
        msg.answer.assert_awaited_once()
        text = msg.answer.await_args.args[0]
        assert "Тестовый заказ" in text
        assert "TEST-0001" in text

    async def test_cmd_help_lists_commands(self, admin_env):
        msg = _make_message(100)
        await bc.cmd_help(msg)
        msg.answer.assert_awaited_once()
        text = msg.answer.await_args.args[0]
        for cmd in ("/status", "/stats", "/pause", "/resume", "/last", "/test", "/help"):
            assert cmd in text

    async def test_cmd_help_non_admin_silent(self, admin_env):
        msg = _make_message(999)
        await bc.cmd_help(msg)
        msg.answer.assert_not_awaited()