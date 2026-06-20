import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from integrations.tools.github import (
    GitHubCreateIssueTool,
    GitHubCreatePRTool,
    GitHubReadRepoTool,
)
from tools.base import Permission


def _mock_bridge():
    bridge = MagicMock()
    bridge.execute_action = AsyncMock(
        return_value={"id": 1, "html_url": "https://github.com/test/repo/issues/1"}
    )
    return bridge


def test_github_read_permission():
    assert GitHubReadRepoTool(_mock_bridge()).permission == Permission.READ


def test_github_create_issue_permission():
    assert GitHubCreateIssueTool(_mock_bridge()).permission == Permission.WRITE


def test_github_create_pr_permission():
    assert GitHubCreatePRTool(_mock_bridge()).permission == Permission.WRITE


def test_github_read_repo():
    bridge = _mock_bridge()
    tool = GitHubReadRepoTool(bridge)
    result = asyncio.run(tool.execute(owner="test", repo="repo"))
    bridge.execute_action.assert_called_once()


def test_github_create_issue():
    bridge = _mock_bridge()
    tool = GitHubCreateIssueTool(bridge)
    result = asyncio.run(tool.execute(owner="test", repo="repo", title="Bug", body="Fix it"))
    bridge.execute_action.assert_called_once()
    parsed = json.loads(result)
    assert "url" in parsed


def test_github_create_pr():
    bridge = _mock_bridge()
    tool = GitHubCreatePRTool(bridge)
    result = asyncio.run(
        tool.execute(
            owner="test", repo="repo", title="Feature", body="New",
            head="feature", base="main"
        )
    )
    bridge.execute_action.assert_called_once()
    parsed = json.loads(result)
    assert "url" in parsed


def test_github_names():
    b = _mock_bridge()
    assert GitHubReadRepoTool(b).name == "composio.github.read_repo"
    assert GitHubCreateIssueTool(b).name == "composio.github.create_issue"
    assert GitHubCreatePRTool(b).name == "composio.github.create_pr"
