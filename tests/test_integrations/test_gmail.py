import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from integrations.tools.gmail import GmailDeleteTool, GmailReadTool, GmailSendTool
from tools.base import Permission


def _mock_bridge():
    bridge = MagicMock()
    bridge.execute_action = AsyncMock(
        return_value={"data": [{"id": "1", "subject": "Test"}]}
    )
    return bridge


def test_gmail_read_permission():
    bridge = _mock_bridge()
    assert GmailReadTool(bridge).permission == Permission.READ


def test_gmail_send_permission():
    bridge = _mock_bridge()
    assert GmailSendTool(bridge).permission == Permission.WRITE


def test_gmail_delete_permission():
    bridge = _mock_bridge()
    assert GmailDeleteTool(bridge).permission == Permission.DESTRUCTIVE


def test_gmail_read_executes():
    bridge = _mock_bridge()
    tool = GmailReadTool(bridge)

    result = asyncio.run(tool.execute(query="is:unread", max_results=5))
    bridge.execute_action.assert_called_once()
    assert "Test" in result


def test_gmail_send_executes():
    bridge = _mock_bridge()
    bridge.execute_action = AsyncMock(return_value={"id": "msg-1"})
    tool = GmailSendTool(bridge)

    result = asyncio.run(tool.execute(to="user@test.com", subject="Hi", body="Hello"))
    bridge.execute_action.assert_called_once()
    parsed = json.loads(result)
    assert parsed["status"] == "sent"


def test_gmail_delete_executes():
    bridge = _mock_bridge()
    bridge.execute_action = AsyncMock(return_value={})
    tool = GmailDeleteTool(bridge)

    result = asyncio.run(tool.execute(message_id="msg-1"))
    bridge.execute_action.assert_called_once()
    parsed = json.loads(result)
    assert parsed["status"] == "deleted"


def test_gmail_read_name():
    bridge = _mock_bridge()
    assert GmailReadTool(bridge).name == "composio.gmail.read"


def test_gmail_send_name():
    bridge = _mock_bridge()
    assert GmailSendTool(bridge).name == "composio.gmail.send"


def test_gmail_delete_name():
    bridge = _mock_bridge()
    assert GmailDeleteTool(bridge).name == "composio.gmail.delete"
