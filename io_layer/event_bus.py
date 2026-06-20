from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from infra.telemetry import get_logger

logger = get_logger("io.event_bus")

DEPARTMENT_ACTIVE = "department_active"
STAGE_CHANGE = "stage_change"
TOOL_CALL = "tool_call"
APPROVAL_REQUEST = "approval_request"
TASK_COMPLETE = "task_complete"
TICK_START = "tick_start"
TICK_COMPLETE = "tick_complete"
KILL_SWITCH = "kill_switch"
VOICE_REQUEST = "voice_request"
VOICE_ACK = "voice_ack"
VOICE_RESULT = "voice_result"
REQUEST_SUBMITTED = "request_submitted"


class AgentEvent(BaseModel):
    type: str
    timestamp: str
    data: dict[str, Any] = {}


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[Callable[[AgentEvent], Awaitable[None]]] = set()

    def subscribe(self, callback: Callable[[AgentEvent], Awaitable[None]]) -> None:
        self._subscribers.add(callback)

    def unsubscribe(self, callback: Callable[[AgentEvent], Awaitable[None]]) -> None:
        self._subscribers.discard(callback)

    async def publish(self, event: AgentEvent) -> None:
        for cb in list(self._subscribers):
            try:
                await cb(event)
            except Exception:
                logger.exception("event subscriber error for event=%s", event.type)


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def reset_event_bus() -> None:
    global _bus
    _bus = None


async def publish_event(event_type: str, **data: Any) -> None:
    bus = get_event_bus()
    event = AgentEvent(
        type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        data=data,
    )
    await bus.publish(event)


def sync_publish(event_type: str, **data: Any) -> None:
    event = AgentEvent(
        type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        data=data,
    )
    bus = get_event_bus()
    try:
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(asyncio.ensure_future, bus.publish(event))
    except RuntimeError:
        pass
