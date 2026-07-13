"""Unit tests for tg_formatter.py — HTML escaping, add_space_after_do, format_order."""

import pytest

from tg_formatter import add_space_after_do, format_order, h


# ---------------------------------------------------------------------------
# h()
# ---------------------------------------------------------------------------

class TestH:
    def test_escapes_lt_gt(self):
        assert h("<b>") == "&lt;b&gt;"

    def test_escapes_amp(self):
        assert h("a & b") == "a &amp; b"

    def test_escapes_quotes(self):
        # html.escape escapes quotes by default
        assert h('"x"') == "&quot;x&quot;"

    def test_empty_string(self):
        assert h("") == ""

    def test_none(self):
        assert h(None) == ""

    def test_falsy_zero(self):
        # 0 is falsy → ""
        assert h(0) == ""

    def test_non_string(self):
        assert h(123) == "123"


# ---------------------------------------------------------------------------
# add_space_after_do()
# ---------------------------------------------------------------------------

class TestAddSpaceAfterDo:
    def test_inserts_space_before_digit(self):
        assert add_space_after_do("до5 минут") == "до 5 минут"

    def test_already_has_space_unchanged(self):
        assert add_space_after_do("до 5") == "до 5"

    def test_word_starting_with_do(self):
        # "до" followed by non-space letter gets a space inserted — actual behavior
        assert add_space_after_do("дом") == "до м"

    def test_no_do_prefix(self):
        assert add_space_after_do("привет") == "привет"

    def test_multiple_occurrences(self):
        assert add_space_after_do("до5 и до6") == "до 5 и до 6"


# ---------------------------------------------------------------------------
# format_order()
# ---------------------------------------------------------------------------

class TestFormatOrder:
    def test_all_fields_populated(self):
        order = {
            "title": "Репетитор",
            "price": "от 1500 до 3000 ₽",
            "description": "Подготовка к ЕГЭ",
            "href": "/clients/order/123",
            "order_id": "ABC-123",
            "preferred_time": "по будням",
            "posted_ago": "5 минут назад",
        }
        out = format_order(order)
        assert "🧾 <b>Название:</b> Репетитор" in out
        assert "💰 <b>Бюджет:</b> от 1500 до 3000 ₽" in out
        assert "📝 <b>Описание:</b>" in out
        assert "Подготовка к ЕГЭ" in out
        assert "🔗 <b>Ссылка:</b> https://profi.ru/clients/order/123" in out
        assert "🆔 <b>ID:</b> <code>ABC-123</code>" in out
        assert "🗓 <b>Когда удобно:</b> по будням" in out
        assert "⏱ <b>Опубликовано:</b> 5 минут назад" in out

    def test_missing_price_no_budget_line(self):
        out = format_order({"title": "T", "description": "D"})
        assert "💰" not in out
        assert "Бюджет" not in out

    def test_missing_description_no_description_line(self):
        out = format_order({"title": "T"})
        assert "📝" not in out
        assert "Описание" not in out

    def test_relative_href_gets_prefix(self):
        out = format_order({"title": "T", "href": "/clients/123"})
        assert "https://profi.ru/clients/123" in out

    def test_absolute_href_unchanged(self):
        out = format_order({"title": "T", "href": "https://example.com/x"})
        assert "https://example.com/x" in out
        # should not be doubled
        assert "https://profi.ruhttps" not in out

    def test_long_description_truncated(self):
        long_text = "а" * 4000
        out = format_order({"title": "T", "description": long_text})
        # truncated to 3000 + ellipsis
        assert "а" * 3000 in out
        assert "а" * 4000 not in out
        assert "…" in out

    def test_description_exactly_3000_not_truncated(self):
        text = "б" * 3000
        out = format_order({"title": "T", "description": text})
        assert "…" not in out
        assert text in out

    def test_order_id_in_code_tags(self):
        out = format_order({"title": "T", "order_id": "X-1"})
        assert "<code>X-1</code>" in out

    def test_empty_dict_raises_keyerror(self):
        # title is required — accessing o['title'] raises KeyError
        with pytest.raises(KeyError):
            format_order({})

    def test_title_with_script_escaped(self):
        out = format_order({"title": "<script>alert(1)</script>"})
        assert "<script>" not in out
        assert "&lt;script&gt;" in out

    def test_price_with_do_gets_space(self):
        out = format_order({"title": "T", "price": "до5 000 ₽"})
        assert "до 5 000 ₽" in out

    def test_missing_optional_fields_minimal(self):
        out = format_order({"title": "Just title"})
        assert out == "🧾 <b>Название:</b> Just title"

    def test_href_with_html_chars_escaped(self):
        out = format_order({"title": "T", "href": "/x?a=1&b=2"})
        assert "&amp;" in out
        assert "&b=2" not in out or "&amp;b=2" in out