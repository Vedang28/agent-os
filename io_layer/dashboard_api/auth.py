from __future__ import annotations

import hmac
import os

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from infra.telemetry import get_logger

logger = get_logger("io.dashboard_api.auth")

_bearer_scheme = HTTPBearer(auto_error=False)


def _get_configured_token() -> str | None:
    return os.environ.get("AGENT_OS_API_TOKEN")


def verify_token(token: str) -> bool:
    configured = _get_configured_token()
    if configured is None:
        logger.warning("AGENT_OS_API_TOKEN not set — all tokens rejected")
        return False
    return hmac.compare_digest(token.encode(), configured.encode())


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    if not verify_token(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return credentials.credentials


def verify_ws_token(token: str | None) -> bool:
    if token is None:
        return False
    return verify_token(token)
