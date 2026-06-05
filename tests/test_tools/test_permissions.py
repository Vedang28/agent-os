import asyncio

import pytest

from tools.base import Permission, Tool, set_permission_checker
from tools.permissions import default_checker, install_default_checker


class FakeReadTool(Tool):
    name = "reader"
    permission = Permission.READ

    async def _run(self, **kwargs) -> str:
        return "read result"


class FakeShellTool(Tool):
    name = "shell"
    permission = Permission.SHELL

    async def _run(self, **kwargs) -> str:
        return "shell result"


class FakeDestructiveTool(Tool):
    name = "destroyer"
    permission = Permission.DESTRUCTIVE

    async def _run(self, **kwargs) -> str:
        return "destroyed"


class FakeWriteTool(Tool):
    name = "writer"
    permission = Permission.WRITE

    async def _run(self, **kwargs) -> str:
        return "write result"


@pytest.fixture(autouse=True)
def _reset_checker():
    set_permission_checker(None)
    yield
    set_permission_checker(None)


def test_read_permission_auto_approved():
    assert default_checker(FakeReadTool()) is True


def test_write_permission_auto_approved():
    assert default_checker(FakeWriteTool()) is True


def test_shell_permission_blocked():
    assert default_checker(FakeShellTool()) is False


def test_destructive_permission_blocked():
    assert default_checker(FakeDestructiveTool()) is False


def test_execute_allows_without_checker():
    result = asyncio.run(FakeShellTool().execute())
    assert result == "shell result"


def test_execute_blocks_shell_with_default_checker():
    install_default_checker()
    with pytest.raises(PermissionError, match="shell"):
        asyncio.run(FakeShellTool().execute())


def test_execute_allows_read_with_default_checker():
    install_default_checker()
    result = asyncio.run(FakeReadTool().execute())
    assert result == "read result"


def test_custom_checker_can_approve_shell():
    set_permission_checker(lambda tool: True)
    result = asyncio.run(FakeShellTool().execute())
    assert result == "shell result"
