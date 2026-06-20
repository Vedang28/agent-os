from __future__ import annotations

import json
from typing import TYPE_CHECKING

from infra.telemetry import get_logger
from tools.base import Permission, Tool

if TYPE_CHECKING:
    from integrations.composio import ComposioBridge

logger = get_logger("integrations.tools.calendar")


class CalendarReadTool(Tool):
    name = "composio.calendar.read"
    permission = Permission.READ

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(self, *, start: str, end: str) -> str:
        logger.info("reading calendar events start=%s end=%s", start, end)
        result = await self._bridge.execute_action(
            "calendar",
            "CALENDAR_LIST_EVENTS",
            {"timeMin": start, "timeMax": end},
        )
        return json.dumps(result, indent=2, default=str)


class CalendarCreateTool(Tool):
    name = "composio.calendar.create"
    permission = Permission.WRITE

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(
        self,
        *,
        title: str,
        start: str,
        end: str,
        attendees: list[str] | None = None,
    ) -> str:
        logger.info("creating calendar event title=%r", title[:80])
        params: dict = {"summary": title, "start": start, "end": end}
        if attendees:
            params["attendees"] = [{"email": a} for a in attendees]
        result = await self._bridge.execute_action(
            "calendar", "CALENDAR_CREATE_EVENT", params
        )
        return json.dumps(
            {"id": result.get("id", ""), "status": "created"},
        )
