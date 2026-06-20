from __future__ import annotations

import json
from typing import TYPE_CHECKING

from infra.telemetry import get_logger
from tools.base import Permission, Tool

if TYPE_CHECKING:
    from integrations.composio import ComposioBridge

logger = get_logger("integrations.tools.gmail")


class GmailReadTool(Tool):
    name = "composio.gmail.read"
    permission = Permission.READ

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(self, *, query: str = "is:unread", max_results: int = 10) -> str:
        logger.info("reading gmail query=%r max=%d", query[:80], max_results)
        result = await self._bridge.execute_action(
            "gmail", "GMAIL_LIST_EMAILS", {"query": query, "maxResults": max_results}
        )
        emails = result.get("data", result)
        return json.dumps(emails, indent=2, default=str)


class GmailSendTool(Tool):
    name = "composio.gmail.send"
    permission = Permission.WRITE

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(self, *, to: str, subject: str, body: str) -> str:
        logger.info("sending gmail to=%s subject=%r", to, subject[:80])
        result = await self._bridge.execute_action(
            "gmail",
            "GMAIL_SEND_EMAIL",
            {"to": to, "subject": subject, "body": body},
        )
        return json.dumps({"status": "sent", "id": result.get("id", "")})


class GmailDeleteTool(Tool):
    name = "composio.gmail.delete"
    permission = Permission.DESTRUCTIVE

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(self, *, message_id: str) -> str:
        logger.info("deleting gmail message_id=%s", message_id)
        result = await self._bridge.execute_action(
            "gmail", "GMAIL_DELETE_EMAIL", {"messageId": message_id}
        )
        return json.dumps({"status": "deleted", "id": message_id})
