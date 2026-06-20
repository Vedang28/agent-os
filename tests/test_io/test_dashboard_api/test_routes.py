import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import MagicMock

from brain.schema import Note
from brain.outcome import Outcome
from io_layer.dashboard_api.app import create_app
from io_layer.dashboard_api.routes import set_services, _services, _active_tasks


@pytest.fixture(autouse=True)
def _set_token(monkeypatch):
    monkeypatch.setenv("AGENT_OS_API_TOKEN", "test-token")


@pytest.fixture()
def mock_services(tmp_path):
    from brain.obsidian import ObsidianVault
    from brain.outcome import OutcomeStore

    vault = ObsidianVault(vault_path=tmp_path)
    vault.write_note(Note(title="TestNote", content="Hello world", tags=["test"]))
    vault.write_note(Note(title="OtherNote", content="Another note", tags=["other"]))

    outcome_store = OutcomeStore(obsidian=vault)
    outcome_store.record(
        Outcome(task_id="t1", department="engineering", success=True, revisions=1)
    )

    librarian = MagicMock()
    librarian.query.return_value = [
        Note(title="Found", content="Search result", tags=["search"])
    ]

    daemon = MagicMock()
    daemon.is_running = True
    daemon.tick_count = 5

    guardian = MagicMock()

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "result": "done",
        "approved": True,
        "lane": "fast",
    }

    return {
        "obsidian": vault,
        "librarian": librarian,
        "outcome_store": outcome_store,
        "daemon": daemon,
        "guardian": guardian,
        "graph_factory": lambda: mock_graph,
    }


@pytest.fixture()
async def client(mock_services):
    app = create_app(services=mock_services, cors_origins=["*"])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    _services.clear()
    _active_tasks.clear()


@pytest.mark.asyncio
async def test_get_agents(client):
    response = await client.get("/api/agents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_brain_notes(client):
    response = await client.get("/api/brain/notes")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["notes"]) >= 2


@pytest.mark.asyncio
async def test_get_brain_notes_with_tag_filter(client):
    response = await client.get("/api/brain/notes?tag=test")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["notes"][0]["title"] == "TestNote"


@pytest.mark.asyncio
async def test_get_brain_notes_pagination(client):
    response = await client.get("/api/brain/notes?limit=1&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["notes"]) == 1
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_get_brain_search(client):
    response = await client.get("/api/brain/search?q=test+query")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "test query"
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == "Found"


@pytest.mark.asyncio
async def test_get_status(client):
    response = await client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["daemon"] == "running"
    assert data["tick_count"] == 5
    assert "agents_registered" in data
    assert "tools_registered" in data


@pytest.mark.asyncio
async def test_get_history(client):
    response = await client.get("/api/history")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["tasks"][0]["department"] == "engineering"
    assert data["tasks"][0]["success"] is True


@pytest.mark.asyncio
async def test_post_request_requires_auth(client):
    response = await client.post(
        "/api/request", json={"request": "build something"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_request_with_auth(client):
    response = await client.post(
        "/api/request",
        json={"request": "build a REST API for user management"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "accepted"
    assert data["lane"] in ("instant", "fast", "deep")


@pytest.mark.asyncio
async def test_post_request_validates_body(client):
    response = await client.post(
        "/api/request",
        json={"request": ""},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_kill(client):
    response = await client.post(
        "/api/kill",
        json={"reason": "test kill"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "killed"


@pytest.mark.asyncio
async def test_post_kill_requires_auth(client):
    response = await client.post("/api/kill", json={"reason": "test"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_approve_not_found(client):
    response = await client.post(
        "/api/approve",
        json={"task_id": "nonexistent", "approved": True},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 404
