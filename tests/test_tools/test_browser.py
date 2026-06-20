import asyncio
import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.base import Permission
from tools.browser import BrowserTool


def _mock_page():
    page = AsyncMock()
    page.url = "http://example.com"
    response = MagicMock()
    response.status = 200
    page.goto = AsyncMock(return_value=response)
    page.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\nfakeimage")
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.inner_text = AsyncMock(return_value="hello world")
    page.inner_html = AsyncMock(return_value="<div>content</div>")
    page.evaluate = AsyncMock(return_value=42)
    page.wait_for_selector = AsyncMock()
    page.go_back = AsyncMock()
    page.go_forward = AsyncMock()
    page.mouse = MagicMock()
    page.mouse.wheel = AsyncMock()
    page.close = AsyncMock()
    return page


def _tool_with_page(page=None):
    tool = BrowserTool()
    tool._page = page or _mock_page()
    tool._browser = AsyncMock()
    tool._context = AsyncMock()
    tool._playwright = AsyncMock()
    return tool


# --- Basic ---


def test_permission_is_shell():
    assert BrowserTool().permission == Permission.SHELL


def test_unknown_action_raises():
    tool = BrowserTool()

    with pytest.raises(ValueError, match="unknown browser action"):
        asyncio.run(tool.execute(action="dance"))


# --- Navigate ---


def test_navigate_success():
    page = _mock_page()
    tool = _tool_with_page(page)

    with patch.object(tool, "_check_url"):
        result = asyncio.run(tool.execute(action="navigate", url="http://example.com"))

    assert "navigated to" in result
    assert "status: 200" in result
    page.goto.assert_called_once()


def test_navigate_checks_url():
    tool = _tool_with_page()

    with patch.object(tool, "_check_url", side_effect=ValueError("blocked")):
        with pytest.raises(ValueError, match="blocked"):
            asyncio.run(tool.execute(action="navigate", url="http://evil.com"))


def test_navigate_post_redirect_ssrf():
    page = _mock_page()
    page.url = "http://169.254.169.254/latest/meta-data/"
    tool = _tool_with_page(page)

    with patch.object(tool, "_check_url") as mock_check:
        def side_effect(url):
            if "169.254" in url:
                raise ValueError("Blocked private/internal IP")

        mock_check.side_effect = side_effect

        with pytest.raises(ValueError, match="Redirect to blocked URL"):
            asyncio.run(tool.execute(action="navigate", url="http://example.com"))


# --- Screenshot ---


def test_screenshot_returns_base64():
    page = _mock_page()
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="screenshot"))
    assert result.startswith("screenshot:base64:")
    payload = result.split("screenshot:base64:")[1]
    decoded = base64.b64decode(payload)
    assert decoded == b"\x89PNG\r\n\x1a\nfakeimage"


def test_screenshot_full_page():
    page = _mock_page()
    tool = _tool_with_page(page)

    asyncio.run(tool.execute(action="screenshot", full_page=True))
    page.screenshot.assert_called_once_with(full_page=True, type="png")


def test_screenshot_save_to_file(tmp_path):
    page = _mock_page()
    tool = _tool_with_page(page)
    out = str(tmp_path / "shot.png")

    result = asyncio.run(tool.execute(action="screenshot", path=out))
    assert "screenshot saved to" in result
    assert (tmp_path / "shot.png").read_bytes() == b"\x89PNG\r\n\x1a\nfakeimage"


# --- Click ---


def test_click():
    page = _mock_page()
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="click", selector="#btn"))
    assert "clicked: #btn" in result
    page.click.assert_called_once()


# --- Type ---


def test_type():
    page = _mock_page()
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="type", selector="#input", text="hello"))
    assert "typed into #input" in result
    page.fill.assert_called_once_with("#input", "hello", timeout=tool._timeout)


# --- Get Text ---


def test_get_text():
    page = _mock_page()
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="get_text"))
    assert "hello world" in result
    assert "page_url:" in result


def test_get_text_truncation():
    page = _mock_page()
    page.inner_text = AsyncMock(return_value="x" * 100_000)
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="get_text"))
    assert len(result) < 100_000


# --- Get HTML ---


def test_get_html():
    page = _mock_page()
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="get_html"))
    assert "<div>content</div>" in result


# --- Evaluate ---


def test_evaluate():
    page = _mock_page()
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="evaluate", expression="1 + 1"))
    assert "result: 42" in result
    page.evaluate.assert_called_once_with("1 + 1")


# --- Wait For ---


def test_wait_for():
    page = _mock_page()
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="wait_for", selector=".loaded"))
    assert "element found: .loaded" in result
    page.wait_for_selector.assert_called_once()


# --- Back / Forward ---


def test_back():
    page = _mock_page()
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="back"))
    assert "navigated back" in result
    page.go_back.assert_called_once()


def test_forward():
    page = _mock_page()
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="forward"))
    assert "navigated forward" in result
    page.go_forward.assert_called_once()


# --- Scroll ---


def test_scroll_down():
    page = _mock_page()
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="scroll", direction="down", amount=300))
    assert "scrolled down by 300px" in result
    page.mouse.wheel.assert_called_once_with(0, 300)


def test_scroll_up():
    page = _mock_page()
    tool = _tool_with_page(page)

    result = asyncio.run(tool.execute(action="scroll", direction="up", amount=200))
    assert "scrolled up by 200px" in result
    page.mouse.wheel.assert_called_once_with(0, -200)


def test_scroll_invalid_direction():
    tool = _tool_with_page()

    with pytest.raises(ValueError, match="direction"):
        asyncio.run(tool.execute(action="scroll", direction="left"))


# --- Close / Cleanup ---


def test_close():
    tool = _tool_with_page()

    result = asyncio.run(tool.execute(action="close"))
    assert "browser closed" in result
    assert tool._page is None
    assert tool._browser is None


def test_cleanup_idempotent():
    tool = _tool_with_page()

    asyncio.run(tool.cleanup())
    asyncio.run(tool.cleanup())
    assert tool._page is None


# --- SSRF Security ---


def test_ssrf_localhost_blocked():
    tool = BrowserTool()
    with patch(
        "tools.browser.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("127.0.0.1", 0))],
    ):
        with pytest.raises(ValueError, match="private"):
            tool._check_url("http://localhost/secret")


def test_ssrf_private_ip_blocked():
    tool = BrowserTool()
    for ip in ["10.0.0.1", "172.16.0.1", "192.168.1.1"]:
        with patch(
            "tools.browser.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", (ip, 0))],
        ):
            with pytest.raises(ValueError, match="private"):
                tool._check_url(f"http://internal/{ip}")


def test_ssrf_metadata_blocked():
    tool = BrowserTool()
    with patch(
        "tools.browser.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("169.254.169.254", 0))],
    ):
        with pytest.raises(ValueError, match="private"):
            tool._check_url("http://169.254.169.254/latest/meta-data/")


def test_blocked_file_scheme():
    tool = BrowserTool()
    with pytest.raises(ValueError, match="scheme"):
        tool._check_url("file:///etc/passwd")


def test_blocked_data_scheme():
    tool = BrowserTool()
    with pytest.raises(ValueError, match="scheme"):
        tool._check_url("data:text/html,<h1>hi</h1>")
