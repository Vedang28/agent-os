import base64
import ipaddress
import socket
from urllib.parse import urlparse

from infra.telemetry import get_logger
from tools.base import Permission, Tool

logger = get_logger("tools.browser")

MAX_PAGE_TIMEOUT = 30_000
MAX_CONTENT_LENGTH = 50_000
BLOCKED_SCHEMES = frozenset({"file", "data", "javascript", "ftp"})


class BrowserTool(Tool):
    name = "browser"
    permission = Permission.SHELL

    def __init__(self, headless: bool = True, timeout: float = 30_000):
        self._headless = headless
        self._timeout = timeout
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._actions = {
            "navigate": self._navigate,
            "screenshot": self._screenshot,
            "click": self._click,
            "type": self._type,
            "get_text": self._get_text,
            "get_html": self._get_html,
            "evaluate": self._evaluate,
            "wait_for": self._wait_for,
            "back": self._back,
            "forward": self._forward,
            "scroll": self._scroll,
            "close": self._close,
        }

    async def _ensure_browser(self):
        if self._page is not None:
            return self._page
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720}
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self._timeout)
        logger.info("browser launched (headless=%s)", self._headless)
        return self._page

    async def _run(self, *, action: str, **kwargs) -> str:
        handler = self._actions.get(action)
        if handler is None:
            raise ValueError(
                f"unknown browser action: {action}. "
                f"Available: {', '.join(sorted(self._actions))}"
            )
        logger.info("browser.%s %s", action, str(kwargs)[:200])
        try:
            return await handler(**kwargs)
        except Exception as exc:
            if "Timeout" in type(exc).__name__:
                logger.warning("browser.%s timed out", action)
                return f"error: browser action '{action}' timed out"
            raise

    def _check_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme in BLOCKED_SCHEMES:
            raise ValueError(f"Blocked scheme: {parsed.scheme}")
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Blocked scheme: {parsed.scheme}")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("No hostname in URL")

        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror as e:
            raise ValueError(f"DNS resolution failed for {hostname}") from e

        for info in infos:
            ip_str = info[4][0]
            if self._is_private_ip(ip_str):
                raise ValueError(f"Blocked private/internal IP: {ip_str}")

    @staticmethod
    def _is_private_ip(ip: str) -> bool:
        addr = ipaddress.ip_address(ip)
        return (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        )

    async def _navigate(self, *, url: str) -> str:
        self._check_url(url)
        page = await self._ensure_browser()
        response = await page.goto(url, timeout=self._timeout, wait_until="domcontentloaded")
        final_url = page.url
        if final_url != url:
            try:
                self._check_url(final_url)
            except ValueError:
                await page.goto("about:blank")
                raise ValueError(
                    f"Redirect to blocked URL: {final_url}"
                )
        status = response.status if response else "unknown"
        return f"navigated to {final_url} (status: {status})"

    async def _screenshot(self, *, path: str | None = None, full_page: bool = False) -> str:
        page = await self._ensure_browser()
        screenshot_bytes = await page.screenshot(full_page=full_page, type="png")
        if path:
            import pathlib

            pathlib.Path(path).write_bytes(screenshot_bytes)
            logger.info("screenshot saved to %s", path)
            return f"screenshot saved to {path} ({len(screenshot_bytes)} bytes)"
        encoded = base64.b64encode(screenshot_bytes).decode()
        return f"screenshot:base64:{encoded}"

    async def _click(self, *, selector: str) -> str:
        page = await self._ensure_browser()
        await page.click(selector, timeout=self._timeout)
        return f"clicked: {selector}"

    async def _type(self, *, selector: str, text: str) -> str:
        page = await self._ensure_browser()
        await page.fill(selector, text, timeout=self._timeout)
        return f"typed into {selector}: {text[:100]}"

    async def _get_text(self) -> str:
        page = await self._ensure_browser()
        text = await page.inner_text("body")
        return f"page_url: {page.url}\ntext:\n{text[:MAX_CONTENT_LENGTH]}"

    async def _get_html(self, *, selector: str = "html") -> str:
        page = await self._ensure_browser()
        html = await page.inner_html(selector)
        return f"page_url: {page.url}\nhtml:\n{html[:MAX_CONTENT_LENGTH]}"

    async def _evaluate(self, *, expression: str) -> str:
        page = await self._ensure_browser()
        result = await page.evaluate(expression)
        return f"result: {result}"

    async def _wait_for(
        self, *, selector: str, state: str = "visible", timeout: float | None = None
    ) -> str:
        page = await self._ensure_browser()
        t = timeout or self._timeout
        await page.wait_for_selector(selector, state=state, timeout=t)
        return f"element found: {selector} (state={state})"

    async def _back(self) -> str:
        page = await self._ensure_browser()
        await page.go_back(timeout=self._timeout)
        return f"navigated back to {page.url}"

    async def _forward(self) -> str:
        page = await self._ensure_browser()
        await page.go_forward(timeout=self._timeout)
        return f"navigated forward to {page.url}"

    async def _scroll(self, *, direction: str = "down", amount: int = 500) -> str:
        if direction not in ("up", "down"):
            raise ValueError(f"direction must be 'up' or 'down', got: {direction}")
        page = await self._ensure_browser()
        delta = amount if direction == "down" else -amount
        await page.mouse.wheel(0, delta)
        return f"scrolled {direction} by {amount}px"

    async def _close(self) -> str:
        await self.cleanup()
        return "browser closed"

    async def cleanup(self) -> None:
        for name, obj in [
            ("page", self._page),
            ("context", self._context),
            ("browser", self._browser),
        ]:
            if obj is not None:
                try:
                    await obj.close()
                except Exception:
                    logger.warning("error closing %s", name)
        self._page = None
        self._context = None
        self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                logger.warning("error stopping playwright")
        self._playwright = None
        logger.info("browser cleaned up")

    def __del__(self):
        if self._browser is not None:
            logger.warning("BrowserTool garbage collected without cleanup()")
