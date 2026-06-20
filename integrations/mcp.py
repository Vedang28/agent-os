from __future__ import annotations

import ipaddress
import json
import socket
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from infra.telemetry import get_logger
from tools.base import Permission, Tool

logger = get_logger("integrations.mcp")

PERMISSION_MAP = {
    "read": Permission.READ,
    "write": Permission.WRITE,
    "execute": Permission.SHELL,
    "delete": Permission.DESTRUCTIVE,
    "destroy": Permission.DESTRUCTIVE,
}


class MCPServerConfig(BaseModel):
    name: str
    url: str
    auth_token: str | None = None


class MCPConfig(BaseModel):
    servers: list[MCPServerConfig] = []


class MCPTool(Tool):
    def __init__(
        self,
        *,
        tool_name: str,
        server_name: str,
        description: str,
        permission: Permission,
        bridge: MCPBridge,
    ):
        self.name = f"mcp.{server_name}.{tool_name}"
        self.permission = permission
        self._tool_name = tool_name
        self._server_name = server_name
        self._description = description
        self._bridge = bridge

    async def _run(self, **kwargs) -> str:
        result = await self._bridge.call_tool(
            self._server_name, self._tool_name, kwargs
        )
        return json.dumps(result, indent=2, default=str)


class MCPBridge:
    def __init__(self, config: MCPConfig | None = None):
        self._config = config or MCPConfig()
        self._connections: dict[str, MCPServerConfig] = {}
        self._timeout = 30.0

    def _check_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Blocked scheme: {parsed.scheme}")
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("No hostname in URL")
        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror as e:
            raise ValueError(f"DNS resolution failed for {hostname}") from e
        for info in infos:
            ip_str = info[4][0]
            addr = ipaddress.ip_address(ip_str)
            if (
                addr.is_private
                or addr.is_loopback
                or addr.is_link_local
                or addr.is_reserved
                or addr.is_multicast
            ):
                raise ValueError(f"Blocked private/internal IP: {ip_str}")

    async def connect(self, server: MCPServerConfig) -> None:
        self._check_url(server.url)
        self._connections[server.name] = server
        logger.info("connected to MCP server=%s url=%s", server.name, server.url)

    async def discover_tools(self, server_name: str) -> list[Tool]:
        server = self._connections.get(server_name)
        if not server:
            raise ValueError(f"Not connected to MCP server: {server_name}")

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if server.auth_token:
            headers["Authorization"] = f"Bearer {server.auth_token}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{server.url}/tools",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        tools: list[Tool] = []
        for tool_def in data.get("tools", []):
            name = tool_def.get("name", "unknown")
            desc = tool_def.get("description", "")
            perm_hint = tool_def.get("permission", "read").lower()
            permission = PERMISSION_MAP.get(perm_hint, Permission.READ)

            tools.append(
                MCPTool(
                    tool_name=name,
                    server_name=server_name,
                    description=desc,
                    permission=permission,
                    bridge=self,
                )
            )

        logger.info(
            "discovered %d tools from MCP server=%s", len(tools), server_name
        )
        return tools

    async def call_tool(
        self, server_name: str, tool_name: str, args: dict
    ) -> dict:
        server = self._connections.get(server_name)
        if not server:
            raise ValueError(f"Not connected to MCP server: {server_name}")

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if server.auth_token:
            headers["Authorization"] = f"Bearer {server.auth_token}"

        logger.info("calling MCP tool=%s on server=%s", tool_name, server_name)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{server.url}/tools/{tool_name}/call",
                headers=headers,
                json=args,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_servers(self) -> list[str]:
        return list(self._connections.keys())
