import asyncio
from unittest.mock import patch

import httpx
import pytest

from tools.base import Permission
from tools.web import WebTool


def _mock_transport(status=200, body="ok"):
    def handler(request):
        return httpx.Response(status, text=body)

    return httpx.MockTransport(handler)


def test_get_request():
    tool = WebTool()
    transport = _mock_transport(200, "response body")

    async def run():
        async with httpx.AsyncClient(transport=transport) as real_client:
            with patch.object(tool, "_check_url"):
                with patch("tools.web.httpx.AsyncClient") as mock_cls:

                    async def fake_init(*a, **kw):
                        return real_client

                    mock_cls.return_value.__aenter__ = fake_init
                    mock_cls.return_value.__aexit__ = lambda *a, **kw: asyncio.sleep(0)

                    # Simpler: just bypass the async-with and call directly
                    pass

        # Directly test by overriding the method
        pass

    # Simplest correct approach: patch _check_url and use a real AsyncClient with mock transport
    async def do_test():
        with patch.object(tool, "_check_url"):
            original_init = httpx.AsyncClient.__init__

            def patched_init(self_client, **kwargs):
                kwargs["transport"] = transport
                original_init(self_client, **kwargs)

            with patch.object(httpx.AsyncClient, "__init__", patched_init):
                return await tool.execute(url="http://example.com")

    result = asyncio.run(do_test())
    assert "status: 200" in result
    assert "response body" in result


def test_post_request():
    tool = WebTool()
    transport = _mock_transport(201, "created")

    async def do_test():
        with patch.object(tool, "_check_url"):
            original_init = httpx.AsyncClient.__init__

            def patched_init(self_client, **kwargs):
                kwargs["transport"] = transport
                original_init(self_client, **kwargs)

            with patch.object(httpx.AsyncClient, "__init__", patched_init):
                return await tool.execute(
                    method="POST", url="http://example.com", body="data"
                )

    result = asyncio.run(do_test())
    assert "status: 201" in result


def test_ssrf_localhost_blocked():
    tool = WebTool()
    with patch(
        "tools.web.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("127.0.0.1", 0))],
    ):
        with pytest.raises(ValueError, match="private"):
            tool._check_url("http://localhost/secret")


def test_ssrf_private_ip_blocked():
    tool = WebTool()
    for ip in ["10.0.0.1", "172.16.0.1", "192.168.1.1"]:
        with patch(
            "tools.web.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", (ip, 0))],
        ):
            with pytest.raises(ValueError, match="private"):
                tool._check_url(f"http://internal/{ip}")


def test_ssrf_metadata_blocked():
    tool = WebTool()
    with patch(
        "tools.web.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("169.254.169.254", 0))],
    ):
        with pytest.raises(ValueError, match="private"):
            tool._check_url("http://169.254.169.254/latest/meta-data/")


def test_ssrf_ipv6_loopback_blocked():
    tool = WebTool()
    with patch(
        "tools.web.socket.getaddrinfo",
        return_value=[(10, 1, 6, "", ("::1", 0, 0, 0))],
    ):
        with pytest.raises(ValueError, match="private"):
            tool._check_url("http://[::1]/")


def test_non_http_scheme_blocked():
    tool = WebTool()
    with pytest.raises(ValueError, match="scheme"):
        tool._check_url("file:///etc/passwd")


def test_permission_is_read():
    assert WebTool().permission == Permission.READ
