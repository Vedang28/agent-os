import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from cryptography.fernet import Fernet

from integrations.composio import ComposioBridge, ComposioConfig, OAuthResult
from integrations.token_store import TokenStore


@pytest.fixture()
def token_store(tmp_path):
    key = Fernet.generate_key().decode()
    return TokenStore(store_dir=tmp_path, key=key)


@pytest.fixture()
def config():
    return ComposioConfig(api_key="test-key")


@pytest.fixture()
def bridge(config, token_store):
    return ComposioBridge(config, token_store)


def _mock_transport(status=200, body=None):
    def handler(request):
        return httpx.Response(status, json=body or {})
    return httpx.MockTransport(handler)


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("COMPOSIO_API_KEY", "env-key")
    c = ComposioConfig.from_env()
    assert c.api_key == "env-key"


def test_config_missing_key():
    c = ComposioConfig.from_env()
    assert c.api_key == ""


def test_connect_app(bridge):
    transport = _mock_transport(200, {"redirectUrl": "https://oauth.example.com/auth"})

    async def run():
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, **kwargs):
            kwargs["transport"] = transport
            original_init(self, **kwargs)

        with patch.object(httpx.AsyncClient, "__init__", patched_init):
            return await bridge.connect_app("gmail")

    result = asyncio.run(run())
    assert isinstance(result, OAuthResult)
    assert result.success is True
    assert result.app_name == "gmail"
    assert "https://oauth.example.com/auth" in result.auth_url


def test_disconnect_app(bridge, token_store):
    token_store.store_token("gmail", {"token": "abc"})

    async def run():
        return await bridge.disconnect_app("gmail")

    result = asyncio.run(run())
    assert result is True
    assert token_store.get_token("gmail") is None


def test_list_connected_apps(bridge, token_store):
    token_store.store_token("gmail", {"t": "1"})
    token_store.store_token("slack", {"t": "2"})

    result = asyncio.run(bridge.list_connected_apps())
    assert sorted(result) == ["gmail", "slack"]


def test_execute_action(bridge, token_store):
    token_store.store_token("gmail", {"access_token": "tok123"})
    transport = _mock_transport(200, {"data": [{"id": "1", "subject": "Hi"}]})

    async def run():
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, **kwargs):
            kwargs["transport"] = transport
            original_init(self, **kwargs)

        with patch.object(httpx.AsyncClient, "__init__", patched_init):
            return await bridge.execute_action("gmail", "GMAIL_LIST_EMAILS", {"query": "is:unread"})

    result = asyncio.run(run())
    assert "data" in result


def test_execute_action_no_credentials(bridge):
    with pytest.raises(ValueError, match="No credentials"):
        asyncio.run(bridge.execute_action("gmail", "GMAIL_LIST_EMAILS", {}))


def test_get_tools(bridge):
    tools = bridge.get_tools("gmail")
    assert len(tools) == 3
    names = {t.name for t in tools}
    assert "composio.gmail.read" in names
    assert "composio.gmail.send" in names
    assert "composio.gmail.delete" in names


def test_get_tools_unknown_app(bridge):
    tools = bridge.get_tools("unknown_app")
    assert tools == []
