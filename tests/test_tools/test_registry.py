import pytest

from tools.base import Permission, Tool
from tools.registry import clear, get, list_tools, register


class FakeTool(Tool):
    name = "fake"
    permission = Permission.READ

    async def _run(self, **kwargs) -> str:
        return "ok"


@pytest.fixture(autouse=True)
def _clean_registry():
    clear()
    yield
    clear()


def test_empty_registry():
    assert list_tools() == []


def test_register_and_get():
    tool = FakeTool()
    register("fake", tool)
    assert get("fake") is tool
    assert list_tools() == ["fake"]


def test_get_missing_raises():
    with pytest.raises(KeyError):
        get("nonexistent")


def test_duplicate_register_raises():
    register("fake", FakeTool())
    with pytest.raises(ValueError):
        register("fake", FakeTool())
