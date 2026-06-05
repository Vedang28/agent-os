import asyncio
import os

import pytest

from tools.base import Permission
from tools.file import FileTool


@pytest.fixture()
def file_tool(tmp_path):
    return FileTool(allowed_root=tmp_path), tmp_path


def test_write_and_read(file_tool):
    tool, _ = file_tool
    asyncio.run(tool.execute(operation="write", path="test.txt", content="hello"))
    result = asyncio.run(tool.execute(operation="read", path="test.txt"))
    assert result == "hello"


def test_list_dir(file_tool):
    tool, tmp = file_tool
    (tmp / "a.txt").write_text("a")
    (tmp / "b.txt").write_text("b")
    result = asyncio.run(tool.execute(operation="list_dir", path="."))
    assert "a.txt" in result
    assert "b.txt" in result


def test_exists_true(file_tool):
    tool, _ = file_tool
    asyncio.run(tool.execute(operation="write", path="exists.txt", content="yes"))
    result = asyncio.run(tool.execute(operation="exists", path="exists.txt"))
    assert result == "true"


def test_exists_false(file_tool):
    tool, _ = file_tool
    result = asyncio.run(tool.execute(operation="exists", path="nope.txt"))
    assert result == "false"


def test_path_traversal_blocked(file_tool):
    tool, _ = file_tool
    with pytest.raises(PermissionError):
        asyncio.run(tool.execute(operation="read", path="../../../etc/passwd"))


def test_symlink_outside_root_blocked(file_tool):
    tool, tmp = file_tool
    target = tmp.parent / "outside.txt"
    target.write_text("secret")
    link = tmp / "link.txt"
    os.symlink(target, link)
    with pytest.raises(PermissionError):
        asyncio.run(tool.execute(operation="read", path="link.txt"))


def test_write_creates_parent_dirs(file_tool):
    tool, _ = file_tool
    asyncio.run(
        tool.execute(operation="write", path="sub/dir/file.txt", content="nested")
    )
    result = asyncio.run(tool.execute(operation="read", path="sub/dir/file.txt"))
    assert result == "nested"


def test_permission_is_write():
    assert FileTool().permission == Permission.WRITE
