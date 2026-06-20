import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from integrations.composio import ComposioBridge, ComposioConfig
from integrations.token_store import TokenStore
from tools.base import Permission
from tools.registry import clear, get, list_tools, register


@pytest.fixture(autouse=True)
def _clean_registry():
    clear()
    yield
    clear()


@pytest.fixture()
def token_store(tmp_path):
    key = Fernet.generate_key().decode()
    return TokenStore(store_dir=tmp_path, key=key)


@pytest.fixture()
def bridge(token_store):
    config = ComposioConfig(api_key="test")
    return ComposioBridge(config, token_store)


def test_composio_tools_register_with_namespace(bridge):
    tools = bridge.get_tools("gmail")
    for tool in tools:
        register(tool.name, tool)

    composio_tools = list_tools(namespace="composio")
    assert len(composio_tools) == 3
    assert all(t.startswith("composio.") for t in composio_tools)


def test_namespace_filtering_isolates():
    from tools.bash import BashTool

    register("bash", BashTool())

    mock_bridge = MagicMock()
    mock_bridge.execute_action = AsyncMock()

    from integrations.tools.gmail import GmailReadTool

    register("composio.gmail.read", GmailReadTool(bridge=mock_bridge))

    all_tools = list_tools()
    assert "bash" in all_tools
    assert "composio.gmail.read" in all_tools

    composio_only = list_tools(namespace="composio")
    assert composio_only == ["composio.gmail.read"]
    assert "bash" not in composio_only


def test_list_tools_no_namespace_returns_all():
    from tools.bash import BashTool

    register("bash", BashTool())
    register("composio.test.tool", MagicMock())

    all_tools = list_tools()
    assert len(all_tools) == 2


def test_list_tools_empty_namespace():
    from tools.bash import BashTool

    register("bash", BashTool())
    mcp_tools = list_tools(namespace="mcp")
    assert mcp_tools == []


def test_composio_and_mcp_coexist():
    mock_bridge = MagicMock()
    mock_bridge.execute_action = AsyncMock()

    from integrations.tools.gmail import GmailReadTool

    register("composio.gmail.read", GmailReadTool(bridge=mock_bridge))

    mcp_tool = MagicMock()
    mcp_tool.name = "mcp.server1.search"
    mcp_tool.permission = Permission.READ
    register("mcp.server1.search", mcp_tool)

    from tools.bash import BashTool

    register("bash", BashTool())

    assert len(list_tools()) == 3
    assert len(list_tools(namespace="composio")) == 1
    assert len(list_tools(namespace="mcp")) == 1


def test_register_integrations_function(bridge, token_store):
    token_store.store_token("gmail", {"access_token": "tok"})

    async def run():
        from integrations import register_integrations

        return await register_integrations(bridge=bridge)

    count = asyncio.run(run())
    assert count == 3
    assert "composio.gmail.read" in list_tools()
    assert "composio.gmail.send" in list_tools()
    assert "composio.gmail.delete" in list_tools()
