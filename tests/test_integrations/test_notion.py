import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from integrations.tools.notion import NotionReadTool, NotionSearchTool, NotionWriteTool
from tools.base import Permission


def _mock_bridge():
    bridge = MagicMock()
    bridge.execute_action = AsyncMock(return_value={"id": "page-1", "url": "https://notion.so/page-1"})
    return bridge


def test_notion_read_permission():
    assert NotionReadTool(_mock_bridge()).permission == Permission.READ


def test_notion_write_permission():
    assert NotionWriteTool(_mock_bridge()).permission == Permission.WRITE


def test_notion_search_permission():
    assert NotionSearchTool(_mock_bridge()).permission == Permission.READ


def test_notion_read_executes():
    bridge = _mock_bridge()
    tool = NotionReadTool(bridge)
    result = asyncio.run(tool.execute(page_id="page-1"))
    bridge.execute_action.assert_called_once()
    assert "page-1" in result


def test_notion_write_executes():
    bridge = _mock_bridge()
    tool = NotionWriteTool(bridge)
    result = asyncio.run(tool.execute(title="Test", content="Hello"))
    bridge.execute_action.assert_called_once()
    parsed = json.loads(result)
    assert "id" in parsed


def test_notion_search_executes():
    bridge = _mock_bridge()
    bridge.execute_action = AsyncMock(return_value={"results": []})
    tool = NotionSearchTool(bridge)
    result = asyncio.run(tool.execute(query="test"))
    bridge.execute_action.assert_called_once()
