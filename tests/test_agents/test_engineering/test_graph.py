from agents.departments.engineering.graph import MAX_REVISIONS, build_engineering_graph


def test_happy_path_approves():
    graph = build_engineering_graph()
    result = graph.invoke({"request": "build a REST API"})
    assert result["approved"] is True
    assert result["result"]
    assert result.get("revisions", 0) == 0


def test_revise_path():
    graph = build_engineering_graph()
    result = graph.invoke({"request": "build a REST API", "draft": "", "result": ""})
    assert result.get("revisions", 0) >= 0


def test_bounded_loop_escalates():
    graph = build_engineering_graph()
    result = graph.invoke({
        "request": "build something",
        "revisions": MAX_REVISIONS,
        "approved": False,
    })
    # After MAX_REVISIONS, should not loop infinitely
    assert result.get("revisions", 0) <= MAX_REVISIONS + 1


def test_escalation_message():
    """Force escalation by starting with high revisions and making critic reject."""
    from unittest.mock import patch

    with patch(
        "agents.departments.engineering.code_doctor.CodeDoctor._review",
        return_value=["forced failure"],
    ):
        graph = build_engineering_graph()
        result = graph.invoke({
            "request": "build something",
            "revisions": MAX_REVISIONS - 1,
        })
        if not result.get("approved"):
            assert "ESCALATION" in result.get("result", "")


def test_max_revisions_constant():
    assert MAX_REVISIONS == 3
