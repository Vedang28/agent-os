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


def _config(thread_id="integration"):
    return {"configurable": {"thread_id": thread_id}}


def test_deep_request_full_flow():
    """Deep request flows: User → Dispatcher → Orchestrator → Engineering triad → approved output."""
    graph = build_company_graph()
    result = graph.invoke(
        {"request": "build a REST API for user management"},
        config=_config("full-flow-1"),
    )
    assert result["lane"] == "deep"
    assert result["department"] == "engineering"
    assert result["approved"] is True
    assert result["result"]


def test_instant_short_circuits_company():
    """Instant request does NOT enter the orchestrator or department."""
    graph = build_company_graph()
    result = graph.invoke(
        {"request": "hello"},
        config=_config("instant-flow"),
    )
    assert result["lane"] == "instant"
    assert result["approved"] is True
    assert result.get("department") is None or result.get("department") == ""


def test_revise_loop_then_passes():
    """A bad first result triggers the critic loop, then passes on revision."""
    from unittest.mock import patch

    call_count = {"n": 0}
    original_review = None

    from agents.departments.engineering.code_doctor import CodeDoctor
    original_review = CodeDoctor._review

    def flaky_review(self, result, draft):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ["First attempt has issues"]
        return []

    with patch.object(CodeDoctor, "_review", flaky_review):
        from core.graph import _department_keywords
        graph = build_engineering_graph()
        _department_graphs.clear()
        _department_keywords.clear()
        register_department_graph("engineering", graph, keywords=["build", "complex"])

        company = build_company_graph()
        result = company.invoke(
            {"request": "build something complex"},
            config=_config("revise-flow"),
        )
        assert result["approved"] is True
        assert result.get("revisions", 0) >= 1
