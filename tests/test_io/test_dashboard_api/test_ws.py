import pytest
from starlette.testclient import TestClient

from io_layer.dashboard_api.app import create_app
from io_layer.dashboard_api.ws import manager, reset_ws_state
from io_layer.event_bus import AgentEvent, get_event_bus, reset_event_bus


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    monkeypatch.setenv("AGENT_OS_API_TOKEN", "ws-test-token")
    reset_event_bus()
    reset_ws_state()
    yield
    reset_event_bus()
    reset_ws_state()


@pytest.fixture()
def app():
    return create_app(cors_origins=["*"])


def test_websocket_connects_with_valid_token(app):
    client = TestClient(app)
    with client.websocket_connect("/ws/activity?token=ws-test-token") as ws:
        assert manager.active_count >= 1


def test_websocket_rejects_invalid_token(app):
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/activity?token=bad-token"):
            pass


def test_websocket_rejects_no_token(app):
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/activity"):
            pass


@pytest.mark.asyncio
async def test_broadcast_sends_to_connections():
    event = AgentEvent(type="test_broadcast", timestamp="t1", data={"msg": "hi"})
    await manager.broadcast(event)


def test_connection_manager_starts_empty():
    reset_ws_state()
    assert manager.active_count == 0
