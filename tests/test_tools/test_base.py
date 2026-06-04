import pytest

from tools.base import Permission, Tool


def test_permission_values():
    assert Permission.READ == "read"
    assert Permission.WRITE == "write"
    assert Permission.SHELL == "shell"
    assert Permission.DESTRUCTIVE == "destructive"


def test_permission_is_string():
    assert isinstance(Permission.READ, str)


def test_tool_cannot_be_instantiated():
    with pytest.raises(TypeError):
        Tool()
