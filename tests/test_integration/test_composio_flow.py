import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet

from agents.guardian import (
    Guardian,
    _reset_approval_callback_for_testing,
    guardian_permission_checker,
    set_approval_callback,
)
from integrations.composio import ComposioBridge, ComposioConfig
from integrations.token_store import TokenStore
from integrations.tools.gmail import GmailDeleteTool, GmailReadTool
from integrations.tools.notion import NotionWriteTool
from tools.base import Permission, set_permission_checker
from tools.registry import clear, register


@pytest.fixture(autouse=True)
def _cleanup():
    clear()
    _reset_approval_callback_for_testing()
    set_approval_callback(lambda a, d: True)
    Guardian(timeout=1.0).reset_kill_switch()
    _reset_approval_callback_for_testing()
    set_permission_checker(None)
    yield
    clear()
    _reset_approval_callback_for_testing()
    set_approval_callback(lambda a, d: True)
    Guardian(timeout=1.0).reset_kill_switch()
    _reset_approval_callback_for_testing()
    set_permission_checker(None)


@pytest.fixture()
def bridge(tmp_path):
    key = Fernet.generate_key().decode()
    store = TokenStore(store_dir=tmp_path, key=key)
    store.store_token("gmail", {"access_token": "tok"})
    store.store_token("notion", {"access_token": "tok"})
    config = ComposioConfig(api_key="test")
    return ComposioBridge(config, store)


def test_gmail_read_no_approval_needed(bridge):
    tool = GmailReadTool(bridge)
    tool._bridge.execute_action = AsyncMock(
        return_value={"data": [{"id": "1", "subject": "Test"}]}
    )
    register("composio.gmail.read", tool)

    guardian = Guardian(timeout=1.0)
    set_approval_callback(lambda a, d: True)
    checker = guardian_permission_checker(guardian)
    set_permission_checker(checker)

    result = asyncio.run(tool.execute(query="is:unread"))
    assert "Test" in result


def test_notion_write_executes(bridge):
    tool = NotionWriteTool(bridge)
    tool._bridge.execute_action = AsyncMock(
        return_value={"id": "page-1", "url": "https://notion.so/page-1"}
    )

    result = asyncio.run(tool.execute(title="Report", content="Summary"))
    parsed = json.loads(result)
    assert "id" in parsed


def test_gmail_delete_blocked_without_approval(bridge):
    tool = GmailDeleteTool(bridge)
    tool._bridge.execute_action = AsyncMock(return_value={})
    register("composio.gmail.delete", tool)

    guardian = Guardian(timeout=1.0)
    set_approval_callback(lambda a, d: False)
    checker = guardian_permission_checker(guardian)
    set_permission_checker(checker)

    with pytest.raises(PermissionError):
        asyncio.run(tool.execute(message_id="msg-1"))


def test_gmail_delete_allowed_with_approval(bridge):
    tool = GmailDeleteTool(bridge)
    tool._bridge.execute_action = AsyncMock(return_value={})

    guardian = Guardian(timeout=1.0)
    set_approval_callback(lambda a, d: True)
    checker = guardian_permission_checker(guardian)
    set_permission_checker(checker)

    result = asyncio.run(tool.execute(message_id="msg-1"))
    parsed = json.loads(result)
    assert parsed["status"] == "deleted"


def test_end_to_end_read_gmail_write_notion(tmp_path):
    key = Fernet.generate_key().decode()
    store = TokenStore(store_dir=tmp_path / "e2e", key=key)
    store.store_token("gmail", {"access_token": "tok"})
    store.store_token("notion", {"access_token": "tok"})

    gmail_bridge = ComposioBridge(ComposioConfig(api_key="test"), store)
    gmail_bridge.execute_action = AsyncMock(
        return_value={"data": [{"id": "1", "subject": "Important", "snippet": "Details here"}]}
    )
    gmail_tool = GmailReadTool(gmail_bridge)

    notion_bridge = ComposioBridge(ComposioConfig(api_key="test"), store)
    notion_bridge.execute_action = AsyncMock(
        return_value={"id": "page-1", "url": "https://notion.so/page-1"}
    )
    notion_tool = NotionWriteTool(notion_bridge)

    async def flow():
        emails = await gmail_tool.execute(query="is:important")
        email_data = json.loads(emails)

        summary = f"Found emails: {json.dumps(email_data)}"
        result = await notion_tool.execute(title="Email Summary", content=summary)
        return result

    result = asyncio.run(flow())
    parsed = json.loads(result)
    assert parsed["id"] == "page-1"

    notion_bridge.execute_action.assert_called_once()
    call_params = notion_bridge.execute_action.call_args[0][2]
    assert "Important" in call_params["content"]
