from __future__ import annotations

import json
import os
from typing import Any

import httpx
from pydantic import BaseModel

from infra.telemetry import get_logger
from integrations.token_store import TokenStore
from tools.base import Tool

logger = get_logger("integrations.composio")

DEFAULT_BASE_URL = "https://backend.composio.dev/api/v1"

APP_SCOPES: dict[str, list[str]] = {
    "gmail": ["gmail.readonly", "gmail.send"],
    "notion": ["read_content", "insert_content"],
    "slack": ["channels:read", "chat:write"],
    "github": ["repo", "read:org"],
    "calendar": ["calendar.readonly", "calendar.events"],
}


class ComposioConfig(BaseModel):
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    connected_apps: list[str] = []

    @classmethod
    def from_env(cls) -> ComposioConfig:
        return cls(api_key=os.environ.get("COMPOSIO_API_KEY", ""))


class OAuthResult(BaseModel):
    success: bool
    auth_url: str
    app_name: str
    scopes: list[str]


class ComposioBridge:
    def __init__(self, config: ComposioConfig, token_store: TokenStore):
        self._config = config
        self._token_store = token_store
        self._timeout = 30.0

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._config.api_key,
            "Content-Type": "application/json",
        }

    async def connect_app(self, app_name: str) -> OAuthResult:
        scopes = APP_SCOPES.get(app_name, [])
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._config.base_url}/connectedAccounts",
                headers=self._headers(),
                json={"integrationId": app_name, "scopes": scopes},
            )
            resp.raise_for_status()
            data = resp.json()

        auth_url = data.get("redirectUrl", "")
        logger.info("OAuth initiated for app=%s", app_name)
        return OAuthResult(
            success=True,
            auth_url=auth_url,
            app_name=app_name,
            scopes=scopes,
        )

    async def complete_connection(self, app_name: str, auth_code: str) -> bool:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._config.base_url}/connectedAccounts/callback",
                headers=self._headers(),
                json={"integrationId": app_name, "code": auth_code},
            )
            resp.raise_for_status()
            data = resp.json()

        token_data = {
            "access_token": data.get("accessToken", ""),
            "refresh_token": data.get("refreshToken", ""),
            "app_name": app_name,
        }
        self._token_store.store_token(app_name, token_data)

        if app_name not in self._config.connected_apps:
            self._config.connected_apps.append(app_name)

        logger.info("OAuth completed for app=%s", app_name)
        return True

    async def disconnect_app(self, app_name: str) -> bool:
        self._token_store.delete_token(app_name)
        if app_name in self._config.connected_apps:
            self._config.connected_apps.remove(app_name)
        logger.info("disconnected app=%s", app_name)
        return True

    async def list_connected_apps(self) -> list[str]:
        return self._token_store.list_apps()

    async def execute_action(
        self, app_name: str, action: str, params: dict[str, Any]
    ) -> dict:
        token_data = self._token_store.get_token(app_name)
        if not token_data:
            raise ValueError(f"No credentials for app: {app_name}. Connect it first.")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._config.base_url}/actions/{action}/execute",
                headers=self._headers(),
                json={
                    "connectedAccountId": app_name,
                    "input": params,
                    "authConfig": {"token": token_data.get("access_token", "")},
                },
            )
            resp.raise_for_status()
            return resp.json()

    def get_tools(self, app_name: str) -> list[Tool]:
        from integrations.tools.calendar import CalendarCreateTool, CalendarReadTool
        from integrations.tools.github import (
            GitHubCreateIssueTool,
            GitHubCreatePRTool,
            GitHubReadRepoTool,
        )
        from integrations.tools.gmail import (
            GmailDeleteTool,
            GmailReadTool,
            GmailSendTool,
        )
        from integrations.tools.notion import (
            NotionReadTool,
            NotionSearchTool,
            NotionWriteTool,
        )
        from integrations.tools.slack import SlackReadTool, SlackSendTool

        tool_map: dict[str, list[type]] = {
            "gmail": [GmailReadTool, GmailSendTool, GmailDeleteTool],
            "notion": [NotionReadTool, NotionWriteTool, NotionSearchTool],
            "slack": [SlackReadTool, SlackSendTool],
            "github": [GitHubReadRepoTool, GitHubCreateIssueTool, GitHubCreatePRTool],
            "calendar": [CalendarReadTool, CalendarCreateTool],
        }

        classes = tool_map.get(app_name, [])
        return [cls(bridge=self) for cls in classes]
