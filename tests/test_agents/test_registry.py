import pytest

from agents.protocol import Agent
from agents.registry import clear, get, list_agents, register


class FakeAgent:
    name: str = "fake"

    async def run(self, state):
        return state


@pytest.fixture(autouse=True)
def _clean_registry():
    clear()
    yield
    clear()


def test_empty_registry():
    assert list_agents() == []


def test_register_and_get():
    agent = FakeAgent()
    register("fake", agent)
    assert get("fake") is agent
    assert list_agents() == ["fake"]


def test_get_missing_raises():
    with pytest.raises(KeyError):
        get("nonexistent")


def test_duplicate_register_raises():
    register("fake", FakeAgent())
    with pytest.raises(ValueError):
        register("fake", FakeAgent())


def test_agent_satisfies_protocol():
    assert isinstance(FakeAgent(), Agent)
