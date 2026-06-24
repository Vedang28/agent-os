import pytest
from unittest.mock import MagicMock
from pathlib import Path

from infra.eval_harness import EvalHarness

EVAL_CASES_DIR = Path(__file__).resolve().parents[2] / "infra" / "eval_cases"


@pytest.fixture
def mock_graph():
    graph = MagicMock()
    graph.invoke.return_value = {
        "approved": True,
        "department": "engineering",
        "lane": "deep",
        "revisions": 1,
        "result": "generated code",
    }
    return graph


@pytest.fixture
def harness(mock_graph):
    h = EvalHarness(graph_factory=lambda: mock_graph)
    for yaml_file in sorted(EVAL_CASES_DIR.glob("*.yaml")):
        h.load_from_yaml(yaml_file)
    return h


class TestEvalCI:
    def test_eval_cases_exist(self, harness):
        assert len(harness._evals) > 0

    def test_all_evals_pass(self, harness, mock_graph):
        def smart_invoke(state, config=None):
            req = state.get("request", "")
            if "hello" in req.lower() or "ping" in req.lower():
                return {
                    "approved": True,
                    "lane": "instant",
                    "result": f"ACK: {req}",
                }
            if "intelligence" in req.lower() or "briefing" in req.lower():
                return {
                    "approved": True,
                    "department": "intelligence",
                    "lane": "deep",
                    "revisions": 1,
                    "result": "done",
                }
            return {
                "approved": True,
                "department": "engineering",
                "lane": "deep",
                "revisions": 1,
                "result": "done",
            }

        mock_graph.invoke.side_effect = smart_invoke
        results = harness.run_all()
        for r in results:
            assert r.passed, f"Eval {r.case_name} failed: {r.error}"
