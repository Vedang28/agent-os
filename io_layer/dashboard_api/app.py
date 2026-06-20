from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from infra.telemetry import get_logger
from io_layer.dashboard_api.routes import router, set_services
from io_layer.dashboard_api.ws import websocket_activity

logger = get_logger("io.dashboard_api.app")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("dashboard API starting")
    yield
    logger.info("dashboard API shutting down")


def create_app(
    *,
    services: dict[str, Any] | None = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Agent OS Dashboard",
        version="0.1.0",
        lifespan=_lifespan,
    )

    if cors_origins is None:
        env_origins = os.environ.get("AGENT_OS_CORS_ORIGINS", "http://localhost:3000")
        cors_origins = [o.strip() for o in env_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        )
        return response

    app.include_router(router)
    app.add_api_websocket_route("/ws/activity", websocket_activity)

    if services:
        set_services(**services)

    return app
