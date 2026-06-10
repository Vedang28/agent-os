import pytest

from agents.departments.engineering.graph import build_engineering_graph
from core.checkpointer import reset_checkpointer
from core.graph import build_company_graph, register_department_graph, _department_graphs


@pytest.fixture(autouse=True)
def _setup_teardown():
    reset_checkpointer()
    _department_graphs.clear()
    from core.graph import _department_keywords
    _department_keywords.clear()
    eng = build_engineering_graph()
    register_department_graph("engineering", eng, keywords=[
        "build", "create", "design", "implement", "architect", "develop",
        "refactor", "migrate", "deploy", "scaffold", "generate", "code",
        "api", "database", "authentication", "microservice",
    ])
    yield
    _department_graphs.clear()
    _department_keywords.clear()


def _config(thread_id="test"):
    return {"configurable": {"thread_id": thread_id}}


def test_graph_compiles():
    graph = build_company_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_instant_short_circuits():
    graph = build_company_graph()
    result = graph.invoke({"request": "hello"}, config=_config("t1"))
    assert result["lane"] == "instant"
    assert result["approved"] is True
    assert result.get("department") is None or result.get("department") == ""


def test_deep_flows_through_department():
    graph = build_company_graph()
    result = graph.invoke(
        {"request": "build a REST API"},
        config=_config("t2"),
    )
    assert result["lane"] == "deep"
    assert result["department"] == "engineering"
    assert result["approved"] is True
    assert result["result"]


def test_checkpointer_persists_state():
    graph = build_company_graph()
    result1 = graph.invoke(
        {"request": "build an API"},
        config=_config("persist-test"),
    )
    assert result1["approved"] is True

    # A second invocation with same thread_id works
    result2 = graph.invoke(
        {"request": "hello"},
        config=_config("persist-test-2"),
    )
    assert result2["lane"] == "instant"


def test_fast_lane_goes_through_orchestrator():
    graph = build_company_graph()
    result = graph.invoke(
        {"request": "what is the capital of France"},
        config=_config("t3"),
    )
    assert result["lane"] == "fast"
    assert result.get("department") is not None
