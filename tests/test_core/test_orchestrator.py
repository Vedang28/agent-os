import pytest

from core.graph import _department_keywords, register_department_graph, _department_graphs
from core.orchestrator import orchestrate


@pytest.fixture(autouse=True)
def _setup_keywords():
    _department_graphs.clear()
    _department_keywords.clear()
    _department_keywords["engineering"] = [
        "build", "create", "design", "implement", "code", "api",
    ]
    yield
    _department_graphs.clear()
    _department_keywords.clear()


def test_deep_routes_to_engineering():
    result = orchestrate({"request": "build a REST API", "lane": "deep"})
    assert result["department"] == "engineering"


def test_plan_is_list():
    result = orchestrate({"request": "build a REST API", "lane": "deep"})
    assert isinstance(result["plan"], list)
    assert len(result["plan"]) >= 1


def test_code_keyword_routes_engineering():
    result = orchestrate({"request": "write code for the login page", "lane": "deep"})
    assert result["department"] == "engineering"


def test_default_department():
    result = orchestrate({"request": "do something vague", "lane": "fast"})
    assert result["department"] == "engineering"
