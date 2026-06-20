from __future__ import annotations

import json
from typing import TYPE_CHECKING

from infra.telemetry import get_logger
from tools.base import Permission, Tool

if TYPE_CHECKING:
    from integrations.composio import ComposioBridge

logger = get_logger("integrations.tools.slack")


class SlackReadTool(Tool):
    name = "composio.slack.read"
    permission = Permission.READ

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(self, *, channel: str, limit: int = 20) -> str:
        logger.info("reading slack channel=%s limit=%d", channel, limit)
        result = await self._bridge.execute_action(
            "slack",
            "SLACK_LIST_MESSAGES",
            {"channel": channel, "limit": limit},
        )
        return json.dumps(result, indent=2, default=str)


class SlackSendTool(Tool):
    name = "composio.slack.send"
    permission = Permission.WRITE

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(self, *, channel: str, message: str) -> str:
        logger.info("sending slack channel=%s", channel)
        result = await self._bridge.execute_action(
            "slack",
            "SLACK_SEND_MESSAGE",
            {"channel": channel, "text": message},
        )
        return json.dumps({"status": "sent", "channel": channel})
