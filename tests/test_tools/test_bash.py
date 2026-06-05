import asyncio

from tools.base import Permission
from tools.bash import BashTool


def test_execute_echo():
    tool = BashTool()
    result = asyncio.run(tool.execute(command="echo hello"))
    assert "hello" in result
    assert "exit_code: 0" in result


def test_execute_returns_stderr():
    tool = BashTool()
    result = asyncio.run(tool.execute(command="echo err >&2"))
    assert "err" in result


def test_execute_returns_exit_code():
    tool = BashTool()
    result = asyncio.run(tool.execute(command="exit 42"))
    assert "exit_code: 42" in result


def test_execute_timeout():
    tool = BashTool(timeout=0.5)
    result = asyncio.run(tool.execute(command="sleep 10"))
    assert "timed out" in result


def test_permission_is_shell():
    assert BashTool().permission == Permission.SHELL
