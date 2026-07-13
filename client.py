import json
import logging
import os
import urllib.request
from datetime import datetime

from playwright.sync_api import TimeoutError as PWTimeoutError
from playwright.sync_api import Error as PlaywrightError


logger = logging.getLogger("parser.client")


def _get_browser_ws(cdp_url: str) -> str:
    """Fetch the webSocketDebuggerUrl from a Chrome CDP endpoint.

    The CDP endpoint (e.g. http://127.0.0.1:9225/json/version) returns JSON
    containing 'webSocketDebuggerUrl'. Playwright's connect_over_cdp needs
    this ws:// URL when connecting to an already-running Chrome instance.
    """
    resp = urllib.request.urlopen(cdp_url, timeout=10)
    data = json.loads(resp.read().decode("utf-8"))
    ws_url = data.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError(f"No webSocketDebuggerUrl in CDP response from {cdp_url}")
    logger.info("CDP websocket: %s", ws_url)
    return ws_url


class ProfiClient:
    def __init__(self, playwright, settings):
        self.p = playwright
        self.s = settings

        self.browser = None
        self.context = None
        self.page = None

    def start(self) -> "ProfiClient":
        if self.browser or self.context or self.page:
            self.close()

        launch_args = [
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-features=UseSkiaRenderer,Vulkan",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
        ]

        self.browser = self.p.chromium.launch(
            headless=getattr(self.s, "headless", True),
            args=launch_args,
        )

        storage_state = (
            getattr(self.s, "auth_state_path", None)
            or getattr(self.s, "storage_state_path", None)
        )

        if storage_state:
            self.context = self.browser.new_context(
                storage_state=storage_state,
                viewport={"width": 1440, "height": 900},
            )
            logger.info("Context created. storage_state=%s", storage_state)
        else:
            self.context = self.browser.new_context(
                viewport={"width": 1440, "height": 900},
            )
            logger.info("Context created. storage_state=None")

        self.page = self.context.new_page()
        logger.info("Client page created. url=%s", self.page.url)
        return self

    def close(self):
        try:
            if self.page:
                try:
                    self.page.close()
                except Exception:
                    pass
        finally:
            self.page = None

        try:
            if self.context:
                try:
                    self.context.close()
                except Exception:
                    pass
        finally:
            self.context = None

        try:
            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass
        finally:
            self.browser = None

    def __enter__(self) -> "ProfiClient":
        return self.start()

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def open_board(self):
        url = getattr(self.s, "page_url", "https://profi.ru/backoffice/")
        self.page.goto(url, wait_until="domcontentloaded", timeout=90_000)

    def soft_refresh(self):
        try:
            self.page.reload(wait_until="domcontentloaded", timeout=90_000)
            return
        except PlaywrightError as e:
            msg = str(e).lower()

            if any(x in msg for x in (
                "page crashed",
                "target page, context or browser has been closed",
                "browser has been closed",
                "context has been closed",
                "page has been closed",
            )):
                raise RuntimeError("PAGE_OR_BROWSER_CRASHED") from e

            if any(x in msg for x in (
                "err_name_not_resolved",
                "err_internet_disconnected",
                "net::err",
            )):
                url = getattr(self.s, "page_url", "https://profi.ru/backoffice/")
                self.page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                return

            raise

    def cards_locator(self):
        return self.page.locator(self.s.card_selector)

    def wait_cards(self) -> bool:
        try:
            self.page.wait_for_selector(
                self.s.card_selector,
                timeout=self.s.selector_timeout_ms,
                state="attached",
            )
            return True
        except PWTimeoutError:
            self.save_debug(prefix="no_cards")
            return False
        except PlaywrightError as e:
            msg = str(e).lower()
            if any(x in msg for x in (
                "page crashed",
                "target page, context or browser has been closed",
                "browser has been closed",
                "context has been closed",
                "page has been closed",
            )):
                raise RuntimeError("PAGE_OR_BROWSER_CRASHED") from e
            raise

    def save_debug(self, prefix: str = "debug"):
        debug_dir = getattr(self.s, "debug_dir", "logs/debug")
        try:
            os.makedirs(debug_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            png_path = os.path.join(debug_dir, f"{prefix}_{ts}.png")
            html_path = os.path.join(debug_dir, f"{prefix}_{ts}.html")

            try:
                if self.page:
                    self.page.screenshot(path=png_path, full_page=True)
            except Exception:
                pass

            try:
                if self.page:
                    html = self.page.content()
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html)
            except Exception:
                pass
        except Exception:
            return