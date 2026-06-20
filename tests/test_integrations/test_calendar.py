import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from integrations.tools.calendar import CalendarCreateTool, CalendarReadTool
from tools.base import Permission


def _mock_bridge():
    bridge = MagicMock()
    bridge.execute_action = AsyncMock(
        return_value={"id": "evt-1", "summary": "Meeting"}
    )
    return bridge


def test_calendar_read_permission():
    assert CalendarReadTool(_mock_bridge()).permission == Permission.READ


def test_calendar_create_permission():
    assert CalendarCreateTool(_mock_bridge()).permission == Permission.WRITE


def test_calendar_read_executes():
    bridge = _mock_bridge()
    bridge.execute_action = AsyncMock(
        return_value={"events": [{"id": "1", "summary": "Standup"}]}
    )
    tool = CalendarReadTool(bridge)
    result = asyncio.run(tool.execute(start="2026-01-01", end="2026-01-02"))
    bridge.execute_action.assert_called_once()
    assert "Standup" in result


def test_calendar_create_executes():
    bridge = _mock_bridge()
    tool = CalendarCreateTool(bridge)
    result = asyncio.run(
        tool.execute(title="Meeting", start="2026-01-01T10:00", end="2026-01-01T11:00")
    )
    bridge.execute_action.assert_called_once()
    parsed = json.loads(result)
    assert parsed["status"] == "created"


def test_calendar_create_with_attendees():
    bridge = _mock_bridge()
    tool = CalendarCreateTool(bridge)
    result = asyncio.run(
        tool.execute(
            title="Team Sync",
            start="2026-01-01T10:00",
            end="2026-01-01T11:00",
            attendees=["a@test.com", "b@test.com"],
        )
    )
    call_args = bridge.execute_action.call_args
    params = call_args[0][2]
    assert len(params["attendees"]) == 2


def test_calendar_names():
    b = _mock_bridge()
    assert CalendarReadTool(b).name == "composio.calendar.read"
    assert CalendarCreateTool(b).name == "composio.calendar.create"
