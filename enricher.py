"""
Order detail enrichment via Playwright page navigation.

Opens each order's detail page in a separate browser page (within the same
BrowserContext so cookies/session are shared) and extracts extended fields
not available on the listing/cards page.

Rate limiting:
    This module does NOT sleep before/after the first enrichment. The batch
    helper ``enrich_orders_batch`` sleeps ``delay_sec`` between successive
    enrichments. When calling ``enrich_order`` directly, the CALLER is
    responsible for pacing requests (e.g. ``time.sleep`` between calls) to
    avoid hammering Profi.ru and getting rate-limited/blocked.

All public functions are defensive: they never raise — on any error they
return the original order dict (with ``enriched: False``) so the parser
pipeline keeps running.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from playwright.sync_api import BrowserContext, Error as PlaywrightError, Page

logger = logging.getLogger("parser.enricher")

_BASE_URL = "https://profi.ru"


def _build_url(href: str) -> str:
    """Return an absolute URL.

    Prepends ``https://profi.ru`` when *href* is relative (starts with ``/``).
    Already-absolute URLs (starting with ``http://`` or ``https://``) are
    returned unchanged. Empty/None input falls back to the base URL.
    """
    if not href:
        return _BASE_URL
    href = href.strip()
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return _BASE_URL + href
    return _BASE_URL + "/" + href


def _safe_text(page: Page, selector: str) -> Optional[str]:
    """Try to read ``inner_text()`` of *selector* on *page*.

    Returns the trimmed text on success, ``None`` if the selector is not
    found or any Playwright error occurs. Never raises.
    """
    try:
        loc = page.locator(selector)
        if loc.count() == 0:
            return None
        text = loc.first.inner_text()
        if text is None:
            return None
        text = " ".join(text.split()).strip()
        return text or None
    except PlaywrightError:
        return None
    except Exception:
        return None


def _first_text(page: Page, selectors: list[str]) -> Optional[str]:
    """Try each selector in order; return the first non-empty text found."""
    for sel in selectors:
        text = _safe_text(page, sel)
        if text:
            return text
    return None


def _extract_responses_count(page: Page) -> Optional[str]:
    """Extract responses count trying data-testid selectors first, then
    text-content based fallbacks ("ответ", "response")."""
    # Direct selectors
    for sel in ('span[data-testid="responses-count"]', 'span[class*="response"]'):
        text = _safe_text(page, sel)
        if text:
            return text
    # Fallback: look for any element whose text mentions "ответ" / "response"
    for kw in ("ответ", "response", "отклик"):
        try:
            loc = page.locator(f"text=/{kw}/i")
            if loc.count() > 0:
                raw = loc.first.inner_text()
                text = " ".join(raw.split()).strip()
                if text:
                    return text
        except Exception:
            continue
    return None


def _extract_full_description(page: Page) -> Optional[str]:
    """Extract the full description text from the order detail page."""
    # Try specific/description containers first
    for sel in (
        'div[data-testid="order-description"]',
        'div[class*="description"]',
        'section[class*="description"]',
    ):
        text = _safe_text(page, sel)
        if text:
            return text
    # Fallback: <section> paragraphs
    try:
        sec = page.locator("section p")
        if sec.count() > 0:
            parts: list[str] = []
            for i in range(sec.count()):
                try:
                    t = sec.nth(i).inner_text()
                except Exception:
                    continue
                t = " ".join(t.split()).strip()
                if t:
                    parts.append(t)
            if parts:
                return "\n".join(parts)
    except Exception:
        pass
    # Last resort: all <p> text on the page
    try:
        ps = page.locator("p")
        if ps.count() > 0:
            parts = []
            for i in range(ps.count()):
                try:
                    t = ps.nth(i).inner_text()
                except Exception:
                    continue
                t = " ".join(t.split()).strip()
                if t:
                    parts.append(t)
            if parts:
                return "\n".join(parts)
    except Exception:
        pass
    return None


def enrich_order(context: BrowserContext, order: dict, timeout_ms: int = 15000) -> dict:
    """Enrich a single order dict by navigating to its detail page.

    Opens a *new page* within *context* (so the main parser page is left
    untouched), loads the order's ``href``, extracts extended fields, closes
    the page, and returns a new dict::

        {**order, **enriched_fields, "enriched": True}

    Enriched fields:
        - ``full_description``   — full text of the order detail description
        - ``client_rating``      — client rating if visible
        - ``responses_count``    — number of responses if visible
        - ``attachments_count``  — number of attachments if visible
        - ``category_path``      — breadcrumb category path if visible

    On ANY error (navigation failure, timeout, unexpected exception) the page
    is closed and the original *order* dict is returned with ``enriched`` set
    to ``False``. This function never raises.

    Rate limiting:
        No sleep is performed here. The caller must pace successive calls
        (see :func:`enrich_orders_batch` which handles pacing internally).
    """
    page: Optional[Page] = None
    try:
        href = order.get("href") if isinstance(order, dict) else None
        if not href:
            logger.warning("enrich_order: order missing 'href' (order_id=%s)",
                           order.get("order_id") if isinstance(order, dict) else "?")
            return {**order, "enriched": False} if isinstance(order, dict) else {"enriched": False}

        url = _build_url(href)
        logger.info("enrich_order: opening %s (order_id=%s)", url, order.get("order_id"))

        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        except PlaywrightError as e:
            logger.warning("enrich_order: navigation failed for %s: %s", url, e)
            try:
                page.close()
            except Exception:
                pass
            return {**order, "enriched": False}

        enriched: dict = {}

        full_description = _extract_full_description(page)
        if full_description:
            enriched["full_description"] = full_description

        client_rating = _first_text(
            page,
            (
                'span[data-testid="client-rating"]',
                'span[class*="rating"]',
                'div[class*="rating"]',
            ),
        )
        if client_rating:
            enriched["client_rating"] = client_rating

        responses_count = _extract_responses_count(page)
        if responses_count:
            enriched["responses_count"] = responses_count

        # Attachments count — try data-testid and class-based selectors
        attachments_count = _first_text(
            page,
            (
                'span[data-testid="attachments-count"]',
                'span[class*="attachment"]',
                'div[class*="attachment"]',
            ),
        )
        if attachments_count:
            enriched["attachments_count"] = attachments_count

        category_path = _first_text(
            page,
            (
                'nav[aria-label="breadcrumb"]',
                'nav[aria-label="Breadcrumb"]',
                'div[class*="breadcrumb"]',
                'ol[class*="breadcrumb"]',
            ),
        )
        if category_path:
            enriched["category_path"] = category_path

        logger.info("enrich_order: done order_id=%s fields=%s",
                    order.get("order_id"), list(enriched.keys()))

        return {**order, **enriched, "enriched": True}

    except Exception as e:
        logger.exception("enrich_order: unexpected error for order_id=%s: %s",
                         order.get("order_id") if isinstance(order, dict) else "?", e)
        try:
            if isinstance(order, dict):
                return {**order, "enriched": False}
        except Exception:
            pass
        return {"enriched": False}
    finally:
        if page is not None:
            try:
                page.close()
            except Exception:
                pass


def enrich_orders_batch(
    context: BrowserContext,
    orders: list[dict],
    delay_sec: float = 2.5,
    max_enrich: int = 5,
) -> list[dict]:
    """Enrich up to *max_enrich* orders from *orders*, pacing requests.

    Iterates over *orders*, enriching at most ``max_enrich`` of them. Sleeps
    ``delay_sec`` between successive enrichments to avoid rate limiting.
    Orders beyond ``max_enrich`` (or with no ``href``) are passed through
    unchanged with ``enriched: False``.

    Returns a new list of dicts in the same order as the input.
    """
    if not orders:
        return []

    results: list[dict] = []
    enriched_count = 0

    for idx, order in enumerate(orders):
        if enriched_count >= max_enrich:
            # Pass through remaining orders untouched
            if isinstance(order, dict):
                results.append({**order, "enriched": False})
            else:
                results.append({"enriched": False})
            continue

        if not isinstance(order, dict) or not order.get("href"):
            if isinstance(order, dict):
                results.append({**order, "enriched": False})
            else:
                results.append({"enriched": False})
            continue

        logger.info("enrich_orders_batch: [%d/%d] enriching order_id=%s",
                    enriched_count + 1, max_enrich, order.get("order_id"))

        enriched = enrich_order(context, order)
        results.append(enriched)
        if enriched.get("enriched"):
            enriched_count += 1

        # Pace between enrichments (but not after the last one we process)
        if enriched_count < max_enrich and idx < len(orders) - 1:
            # Check if there's another enrichable order ahead before sleeping
            has_more = any(
                isinstance(o, dict) and o.get("href")
                for o in orders[idx + 1:]
            )
            if has_more:
                logger.debug("enrich_orders_batch: sleeping %.1fs", delay_sec)
                time.sleep(delay_sec)

    logger.info("enrich_orders_batch: enriched %d/%d orders (max_enrich=%d)",
                enriched_count, len(orders), max_enrich)
    return results