from __future__ import annotations

import json
from typing import TYPE_CHECKING

from infra.telemetry import get_logger
from tools.base import Permission, Tool

if TYPE_CHECKING:
    from integrations.composio import ComposioBridge

logger = get_logger("integrations.tools.github")


class GitHubReadRepoTool(Tool):
    name = "composio.github.read_repo"
    permission = Permission.READ

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(self, *, owner: str, repo: str) -> str:
        logger.info("reading github repo=%s/%s", owner, repo)
        result = await self._bridge.execute_action(
            "github", "GITHUB_GET_REPO", {"owner": owner, "repo": repo}
        )
        return json.dumps(result, indent=2, default=str)


class GitHubCreateIssueTool(Tool):
    name = "composio.github.create_issue"
    permission = Permission.WRITE

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(self, *, owner: str, repo: str, title: str, body: str) -> str:
        logger.info("creating github issue on %s/%s title=%r", owner, repo, title[:80])
        result = await self._bridge.execute_action(
            "github",
            "GITHUB_CREATE_ISSUE",
            {"owner": owner, "repo": repo, "title": title, "body": body},
        )
        return json.dumps(
            {"id": result.get("id", ""), "url": result.get("html_url", "")},
        )


class GitHubCreatePRTool(Tool):
    name = "composio.github.create_pr"
    permission = Permission.WRITE

    def __init__(self, bridge: ComposioBridge):
        self._bridge = bridge

    async def _run(
        self, *, owner: str, repo: str, title: str, body: str, head: str, base: str
    ) -> str:
        logger.info("creating github PR on %s/%s title=%r", owner, repo, title[:80])
        result = await self._bridge.execute_action(
            "github",
            "GITHUB_CREATE_PR",
            {
                "owner": owner,
                "repo": repo,
                "title": title,
                "body": body,
                "head": head,
                "base": base,
            },
        )
        return json.dumps(
            {"id": result.get("id", ""), "url": result.get("html_url", "")},
        )
