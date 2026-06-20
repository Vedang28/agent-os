import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from integrations.tools.slack import SlackReadTool, SlackSendTool
from tools.base import Permission


def _mock_bridge():
    bridge = MagicMock()
    bridge.execute_action = AsyncMock(
        return_value={"messages": [{"text": "hello", "user": "U1"}]}
    )
    return bridge


def test_slack_read_permission():
    assert SlackReadTool(_mock_bridge()).permission == Permission.READ


def test_slack_send_permission():
    assert SlackSendTool(_mock_bridge()).permission == Permission.WRITE


def test_slack_read_executes():
    bridge = _mock_bridge()
    tool = SlackReadTool(bridge)
    result = asyncio.run(tool.execute(channel="general", limit=5))
    bridge.execute_action.assert_called_once()
    assert "hello" in result


def test_slack_send_executes():
    bridge = _mock_bridge()
    bridge.execute_action = AsyncMock(return_value={"ok": True})
    tool = SlackSendTool(bridge)
    result = asyncio.run(tool.execute(channel="general", message="Hi team"))
    bridge.execute_action.assert_called_once()
    parsed = json.loads(result)
    assert parsed["status"] == "sent"


def test_slack_read_name():
    assert SlackReadTool(_mock_bridge()).name == "composio.slack.read"


def test_slack_send_name():
    assert SlackSendTool(_mock_bridge()).name == "composio.slack.send"
