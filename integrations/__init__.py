from __future__ import annotations

from typing import TYPE_CHECKING

from infra.telemetry import get_logger
from tools.registry import register

if TYPE_CHECKING:
    from integrations.composio import ComposioBridge
    from integrations.mcp import MCPBridge

logger = get_logger("integrations")


async def register_integrations(
    bridge: ComposioBridge | None = None,
    mcp: MCPBridge | None = None,
) -> int:
    count = 0

    if bridge:
        connected = await bridge.list_connected_apps()
        for app_name in connected:
            tools = bridge.get_tools(app_name)
            for tool in tools:
                try:
                    register(tool.name, tool)
                    count += 1
                except ValueError:
                    pass
        logger.info("registered %d Composio tools from %d apps", count, len(connected))

    if mcp:
        mcp_count = 0
        servers = await mcp.list_servers()
        for server_name in servers:
            tools = await mcp.discover_tools(server_name)
            for tool in tools:
                try:
                    register(tool.name, tool)
                    mcp_count += 1
                except ValueError:
                    pass
        logger.info("registered %d MCP tools from %d servers", mcp_count, len(servers))
        count += mcp_count

    return count
