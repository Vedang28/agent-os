import asyncio
from unittest.mock import patch

import httpx
import pytest

from integrations.mcp import MCPBridge, MCPConfig, MCPServerConfig, MCPTool
from tools.base import Permission


@pytest.fixture()
def bridge():
    return MCPBridge()


def test_ssrf_localhost_blocked(bridge):
    with patch(
        "integrations.mcp.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("127.0.0.1", 0))],
    ):
        with pytest.raises(ValueError, match="private"):
            bridge._check_url("http://localhost:8080")


def test_ssrf_private_ip_blocked(bridge):
    for ip in ["10.0.0.1", "172.16.0.1", "192.168.1.1"]:
        with patch(
            "integrations.mcp.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", (ip, 0))],
        ):
            with pytest.raises(ValueError, match="private"):
                bridge._check_url(f"http://internal/{ip}")


def test_blocked_file_scheme(bridge):
    with pytest.raises(ValueError, match="scheme"):
        bridge._check_url("file:///etc/passwd")


def test_connect_validates_url(bridge):
    server = MCPServerConfig(name="evil", url="file:///etc/passwd")
    with pytest.raises(ValueError, match="scheme"):
        asyncio.run(bridge.connect(server))


def test_connect_and_list(bridge):
    server = MCPServerConfig(name="test", url="http://example.com:8080")

    with patch.object(bridge, "_check_url"):
        asyncio.run(bridge.connect(server))

    result = asyncio.run(bridge.list_servers())
    assert result == ["test"]


def test_discover_tools(bridge):
    server = MCPServerConfig(name="tools1", url="http://example.com:8080")

    with patch.object(bridge, "_check_url"):
        asyncio.run(bridge.connect(server))

    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json={
                "tools": [
                    {"name": "search", "description": "Search docs", "permission": "read"},
                    {"name": "deploy", "description": "Deploy app", "permission": "execute"},
                ]
            },
        )
    )

    async def run():
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, **kwargs):
            kwargs["transport"] = transport
            original_init(self, **kwargs)

        with patch.object(httpx.AsyncClient, "__init__", patched_init):
            return await bridge.discover_tools("tools1")

    tools = asyncio.run(run())
    assert len(tools) == 2
    assert tools[0].name == "mcp.tools1.search"
    assert tools[0].permission == Permission.READ
    assert tools[1].name == "mcp.tools1.deploy"
    assert tools[1].permission == Permission.SHELL


def test_discover_tools_not_connected(bridge):
    with pytest.raises(ValueError, match="Not connected"):
        asyncio.run(bridge.discover_tools("nonexistent"))


def test_call_tool(bridge):
    server = MCPServerConfig(name="s1", url="http://example.com:8080", auth_token="tok")

    with patch.object(bridge, "_check_url"):
        asyncio.run(bridge.connect(server))

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"result": "ok"})
    )

    async def run():
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, **kwargs):
            kwargs["transport"] = transport
            original_init(self, **kwargs)

        with patch.object(httpx.AsyncClient, "__init__", patched_init):
            return await bridge.call_tool("s1", "search", {"q": "test"})

    result = asyncio.run(run())
    assert result == {"result": "ok"}


def test_mcp_tool_permission_mapping():
    from integrations.mcp import PERMISSION_MAP

    assert PERMISSION_MAP["read"] == Permission.READ
    assert PERMISSION_MAP["write"] == Permission.WRITE
    assert PERMISSION_MAP["execute"] == Permission.SHELL
    assert PERMISSION_MAP["delete"] == Permission.DESTRUCTIVE
