import pytest
from httpx import ASGITransport, AsyncClient

from io_layer.dashboard_api.app import create_app


@pytest.fixture()
def app():
    return create_app(cors_origins=["http://localhost:3000"])


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_create_app_returns_fastapi(app):
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)


@pytest.mark.asyncio
async def test_security_headers(client):
    response = await client.get("/api/status")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert "strict-origin" in response.headers.get("referrer-policy", "")
    assert "max-age=" in response.headers.get("strict-transport-security", "")
    assert "default-src" in response.headers.get("content-security-policy", "")


@pytest.mark.asyncio
async def test_cors_preflight(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/agents",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "http://localhost:3000" in response.headers.get(
            "access-control-allow-origin", ""
        )
