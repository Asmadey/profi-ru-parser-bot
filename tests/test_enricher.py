"""Unit tests for enricher.py.

Playwright is NOT installed in the CI environment, so we stub the
``playwright.sync_api`` module via sys.modules before importing enricher.
All Playwright objects are faked with unittest.mock.Mock instances.
"""

import sys
import types
from unittest.mock import MagicMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub playwright.sync_api so enricher.py can be imported without the package.
# ---------------------------------------------------------------------------

if "playwright" not in sys.modules:
    pw = types.ModuleType("playwright")
    pw_sync = types.ModuleType("playwright.sync_api")

    class _PWError(Exception):
        pass

    pw_sync.BrowserContext = object
    pw_sync.Page = object
    pw_sync.Error = _PWError
    pw.sync_api = pw_sync
    pw.Error = _PWError
    sys.modules["playwright"] = pw
    sys.modules["playwright.sync_api"] = pw_sync

from enricher import _build_url, enrich_order, enrich_orders_batch  # noqa: E402


# ---------------------------------------------------------------------------
# _build_url
# ---------------------------------------------------------------------------

class TestBuildUrl:
    def test_relative_path(self):
        assert _build_url("/clients/123") == "https://profi.ru/clients/123"

    def test_absolute_https_unchanged(self):
        assert _build_url("https://example.com/x") == "https://example.com/x"

    def test_absolute_http_unchanged(self):
        assert _build_url("http://example.com/x") == "http://example.com/x"

    def test_empty_string(self):
        assert _build_url("") == "https://profi.ru"

    def test_none(self):
        assert _build_url(None) == "https://profi.ru"

    def test_relative_no_leading_slash(self):
        assert _build_url("clients/123") == "https://profi.ru/clients/123"


# ---------------------------------------------------------------------------
# Helper to build a fake Playwright page / context
# ---------------------------------------------------------------------------

def _make_locator(count=0, text=None):
    """Return a Mock locator that supports .count(), .first, .nth()."""
    loc = MagicMock()
    loc.count.return_value = count
    first = MagicMock()
    if text is None:
        first.inner_text.side_effect = Exception("not found")
    else:
        first.inner_text.return_value = text
    loc.first = first

    def nth(i):
        m = MagicMock()
        m.inner_text.return_value = text or ""
        return m

    loc.nth.side_effect = nth
    return loc


def _make_page(*, goto_raises=None, selectors=None):
    """Build a fake Page. selectors maps selector-string -> text."""
    selectors = selectors or {}
    page = MagicMock()

    if goto_raises is not None:
        page.goto.side_effect = goto_raises
    else:
        page.goto.return_value = None

    def locator(sel):
        if sel in selectors:
            return _make_locator(count=1, text=selectors[sel])
        return _make_locator(count=0)

    page.locator.side_effect = locator
    page.close.return_value = None
    return page


def _make_context(page):
    ctx = MagicMock()
    ctx.new_page.return_value = page
    return ctx


# ---------------------------------------------------------------------------
# enrich_order
# ---------------------------------------------------------------------------

class TestEnrichOrder:
    def test_none_context_returns_enriched_false(self):
        order = {"title": "T", "href": "/x"}
        # context is None → context.new_page() fails → caught → enriched:False
        result = enrich_order(None, order)
        assert result["enriched"] is False
        assert result["title"] == "T"

    def test_missing_href_returns_enriched_false(self):
        ctx = MagicMock()
        result = enrich_order(ctx, {"title": "T"})
        assert result["enriched"] is False
        ctx.new_page.assert_not_called()

    def test_navigation_success_extracts_fields(self):
        page = _make_page(selectors={
            'div[data-testid="order-description"]': "Full desc text",
            'span[data-testid="client-rating"]': "4.8",
            'span[data-testid="responses-count"]': "12 ответов",
            'span[data-testid="attachments-count"]': "3 файла",
            'nav[aria-label="breadcrumb"]': "Главная / Математика",
        })
        ctx = _make_context(page)

        order = {"title": "T", "href": "/clients/123", "order_id": "X1"}
        result = enrich_order(ctx, order)

        assert result["enriched"] is True
        assert result["full_description"] == "Full desc text"
        assert result["client_rating"] == "4.8"
        assert result["responses_count"] == "12 ответов"
        assert result["attachments_count"] == "3 файла"
        assert result["category_path"] == "Главная / Математика"
        # original fields preserved
        assert result["title"] == "T"
        assert result["order_id"] == "X1"
        page.close.assert_called()

    def test_navigation_failure_returns_enriched_false(self):
        from playwright.sync_api import Error as PWError  # our stub
        page = _make_page(goto_raises=PWError("timeout"))
        ctx = _make_context(page)

        result = enrich_order(ctx, {"title": "T", "href": "/x"})
        assert result["enriched"] is False
        assert result["title"] == "T"
        page.close.assert_called()

    def test_no_extractions_still_enriched_true(self):
        # navigation succeeds but no selectors match → enriched:True, no extra fields
        page = _make_page(selectors={})
        ctx = _make_context(page)

        result = enrich_order(ctx, {"title": "T", "href": "/x"})
        assert result["enriched"] is True
        # no enriched detail fields
        assert "full_description" not in result
        page.close.assert_called()

    def test_new_page_raises_returns_enriched_false(self):
        ctx = MagicMock()
        ctx.new_page.side_effect = Exception("no browser")
        result = enrich_order(ctx, {"title": "T", "href": "/x"})
        assert result["enriched"] is False

    def test_non_dict_order(self):
        result = enrich_order(MagicMock(), "not a dict")  # type: ignore[arg-type]
        assert result["enriched"] is False


# ---------------------------------------------------------------------------
# enrich_orders_batch
# ---------------------------------------------------------------------------

class TestEnrichOrdersBatch:
    def test_empty_list(self):
        assert enrich_orders_batch(MagicMock(), []) == []

    def test_all_orders_without_href(self):
        ctx = MagicMock()
        orders = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
        result = enrich_orders_batch(ctx, orders, delay_sec=0)
        assert len(result) == 3
        assert all(r["enriched"] is False for r in result)
        assert result[0]["title"] == "A"
        ctx.new_page.assert_not_called()

    def test_max_enrich_limits_enrichments(self):
        page = _make_page(selectors={
            'div[data-testid="order-description"]': "desc",
        })
        ctx = _make_context(page)

        orders = [{"title": f"T{i}", "href": f"/x{i}", "order_id": str(i)} for i in range(5)]
        result = enrich_orders_batch(ctx, orders, delay_sec=0, max_enrich=2)

        assert len(result) == 5
        # first two enriched
        assert result[0]["enriched"] is True
        assert result[1]["enriched"] is True
        # remaining three passthrough with enriched=False
        assert result[2]["enriched"] is False
        assert result[3]["enriched"] is False
        assert result[4]["enriched"] is False
        # original fields preserved on passthrough
        assert result[2]["title"] == "T2"
        # only 2 pages opened
        assert ctx.new_page.call_count == 2

    def test_passthrough_preserves_order(self):
        ctx = MagicMock()
        orders = [{"title": "A", "href": "/a"}, {"title": "B"}, {"title": "C", "href": "/c"}]
        # patch enrich_order to mark enriched True for those with href
        with patch("enricher.enrich_order") as mock_eo:
            mock_eo.side_effect = lambda c, o: {**o, "enriched": True}
            result = enrich_orders_batch(ctx, orders, delay_sec=0, max_enrich=5)
        assert result[0]["enriched"] is True
        assert result[1]["enriched"] is False  # no href → passthrough
        assert result[2]["enriched"] is True

    def test_max_enrich_zero_passes_all_through(self):
        ctx = MagicMock()
        orders = [{"title": "A", "href": "/a"}]
        result = enrich_orders_batch(ctx, orders, delay_sec=0, max_enrich=0)
        assert result[0]["enriched"] is False
        ctx.new_page.assert_not_called()