from __future__ import annotations

import json
from typing import TYPE_CHECKING

from infra.telemetry import get_logger
from tools.base import Permission, Tool

if TYPE_CHECKING:
    from integrations.composio import ComposioBridge

logger = get_logger("integrations.tools.notion")


class NotionReadTool(Tool):
    name = "composio.notion.read"
    permission = Permission.READ

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(self, *, page_id: str) -> str:
        logger.info("reading notion page=%s", page_id)
        result = await self._bridge.execute_action(
            "notion", "NOTION_GET_PAGE", {"pageId": page_id}
        )
        return json.dumps(result, indent=2, default=str)


class NotionWriteTool(Tool):
    name = "composio.notion.write"
    permission = Permission.WRITE

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(
        self, *, title: str, content: str, parent_id: str | None = None
    ) -> str:
        logger.info("writing notion page title=%r", title[:80])
        params: dict = {"title": title, "content": content}
        if parent_id:
            params["parentId"] = parent_id
        result = await self._bridge.execute_action(
            "notion", "NOTION_CREATE_PAGE", params
        )
        return json.dumps(
            {"id": result.get("id", ""), "url": result.get("url", "")},
        )


class NotionSearchTool(Tool):
    name = "composio.notion.search"
    permission = Permission.READ

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(self, *, query: str) -> str:
        logger.info("searching notion query=%r", query[:80])
        result = await self._bridge.execute_action(
            "notion", "NOTION_SEARCH", {"query": query}
        )
        return json.dumps(result, indent=2, default=str)
