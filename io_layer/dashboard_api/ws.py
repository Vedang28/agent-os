from __future__ import annotations

import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from infra.telemetry import get_logger
from io_layer.dashboard_api.auth import verify_ws_token
from io_layer.event_bus import AgentEvent, get_event_bus

logger = get_logger("io.dashboard_api.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def connect(self, ws: WebSocket, token: str | None) -> bool:
        if not verify_ws_token(token):
            await ws.close(code=1008, reason="Invalid token")
            return False
        await ws.accept()
        self._connections.add(ws)
        logger.info("ws client connected, total=%d", len(self._connections))
        return True

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("ws client disconnected, total=%d", len(self._connections))

    async def broadcast(self, event: AgentEvent) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(event.model_dump())
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)


manager = ConnectionManager()

_bus_subscribed = False


def _ensure_bus_subscription() -> None:
    global _bus_subscribed
    if _bus_subscribed:
        return
    bus = get_event_bus()
    bus.subscribe(manager.broadcast)
    _bus_subscribed = True


def reset_ws_state() -> None:
    global _bus_subscribed
    _bus_subscribed = False
    manager._connections.clear()


async def websocket_activity(ws: WebSocket) -> None:
    token = ws.query_params.get("token")
    accepted = await manager.connect(ws, token)
    if not accepted:
        return

    _ensure_bus_subscription()

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)
