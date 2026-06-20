import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock

from io_layer.dashboard_api.app import create_app
from io_layer.dashboard_api.routes import set_services, _services, _active_tasks
from io_layer.event_bus import AgentEvent, get_event_bus, reset_event_bus
from io_layer.voice.controller import VoiceController


async def _audio_stream():
    yield b"fake-audio-data"


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setenv("AGENT_OS_API_TOKEN", "int-test-token")
    reset_event_bus()
    yield
    _services.clear()
    _active_tasks.clear()
    reset_event_bus()


@pytest.fixture()
def mock_graph():
    graph = MagicMock()
    graph.invoke.return_value = {
        "result": "API built successfully",
        "approved": True,
        "lane": "deep",
        "department": "engineering",
        "revisions": 1,
    }
    return graph


@pytest.fixture()
async def dashboard_client(mock_graph, tmp_path):
    from brain.obsidian import ObsidianVault
    from brain.outcome import OutcomeStore
    from brain.schema import Note

    vault = ObsidianVault(vault_path=tmp_path)
    vault.write_note(Note(title="TestNote", content="Integration test note"))
    outcome_store = OutcomeStore(obsidian=vault)

    guardian = MagicMock()
    daemon = MagicMock()
    daemon.is_running = True
    daemon.tick_count = 3

    services = {
        "obsidian": vault,
        "librarian": MagicMock(query=MagicMock(return_value=[])),
        "outcome_store": outcome_store,
        "daemon": daemon,
        "guardian": guardian,
        "graph_factory": lambda: mock_graph,
    }

    app = create_app(services=services, cors_origins=["*"])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_submit_request_and_check_status(dashboard_client):
    response = await dashboard_client.post(
        "/api/request",
        json={"request": "build a REST API"},
        headers={"Authorization": "Bearer int-test-token"},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["task_id"]

    status = await dashboard_client.get("/api/status")
    assert status.status_code == 200
    assert status.json()["daemon"] == "running"


@pytest.mark.asyncio
async def test_voice_deep_request_ack_first(mock_graph):
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(
        return_value="build a microservice for payments"
    )

    mock_tts = MagicMock()
    mock_tts.speak_sentence = AsyncMock(return_value=b"ack-audio")

    async def mock_speak(text):
        yield b"result-audio"

    mock_tts.speak = mock_speak

    controller = VoiceController(
        stt=mock_stt,
        tts=mock_tts,
        graph_factory=lambda: mock_graph,
    )

    chunks = []
    async for chunk in controller.handle_voice_input(_audio_stream()):
        chunks.append(chunk)

    assert len(chunks) >= 1
    assert chunks[0] == b"ack-audio"


@pytest.mark.asyncio
async def test_event_bus_receives_events_during_voice(mock_graph):
    events = []
    bus = get_event_bus()

    async def capture(event: AgentEvent):
        events.append(event)

    bus.subscribe(capture)

    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value="hello")

    mock_tts = MagicMock()
    mock_tts.speak_sentence = AsyncMock(return_value=b"audio")

    async def mock_speak(text):
        yield b"audio"

    mock_tts.speak = mock_speak

    controller = VoiceController(
        stt=mock_stt,
        tts=mock_tts,
        graph_factory=lambda: mock_graph,
    )

    async for _ in controller.handle_voice_input(_audio_stream()):
        pass

    event_types = [e.type for e in events]
    assert "voice_request" in event_types


@pytest.mark.asyncio
async def test_kill_via_dashboard(dashboard_client):
    response = await dashboard_client.post(
        "/api/kill",
        json={"reason": "integration test"},
        headers={"Authorization": "Bearer int-test-token"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "killed"
