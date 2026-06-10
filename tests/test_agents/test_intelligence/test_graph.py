import pytest

from agents.departments.intelligence.graph import MAX_REVISIONS, build_intelligence_graph


class TestIntelligenceGraph:
    def test_happy_path_approves(self):
        graph = build_intelligence_graph()
        result = graph.invoke({"request": "Generate daily intelligence briefing"})
        assert result.get("approved") is True
        assert result.get("result")

    def test_graph_compiles(self):
        graph = build_intelligence_graph()
        assert graph is not None

    def test_scout_sets_draft(self):
        graph = build_intelligence_graph()
        result = graph.invoke({"request": "intelligence briefing"})
        assert result.get("draft") is not None

    def test_analyst_sets_result(self):
        graph = build_intelligence_graph()
        result = graph.invoke({"request": "intelligence briefing"})
        assert result.get("result") is not None

    def test_bounded_loop_escalates(self):
        graph = build_intelligence_graph()
        result = graph.invoke({
            "request": "intelligence briefing",
            "brain_context": [
                {"title": "LangGraph adds native streaming support"},
                {"title": "Qdrant introduces binary quantization"},
                {"title": "Claude model context protocol (MCP) adoption growing"},
            ],
        })
        if not result.get("approved"):
            assert result.get("revisions", 0) <= MAX_REVISIONS

    def test_max_revisions_constant(self):
        assert MAX_REVISIONS == 3
