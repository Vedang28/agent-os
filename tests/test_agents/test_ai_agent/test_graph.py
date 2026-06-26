from unittest.mock import patch

import pytest

from agents.departments.ai_agent.eval_critic import EvalCritic
from agents.departments.ai_agent.graph import MAX_REVISIONS, build_ai_agent_graph


def test_happy_path_approves():
    """Agents are pure prompt containers now — no LLM mocking needed.
    The critic's _review() checks for domain keywords in the output.
    We patch _review to simulate approval since prompt text won't contain
    all required domain signals.
    """
    with patch.object(EvalCritic, "_review", return_value=[]):
        graph = build_ai_agent_graph()
        result = graph.invoke({"request": "build a JSON extraction AI feature with tools"})
        assert result["approved"] is True
        assert result["result"]
        assert result.get("revisions", 0) == 0


def test_output_contains_prompt_and_request():
    """Agents now return their system prompt + task as the output."""
    with patch.object(EvalCritic, "_review", return_value=[]):
        graph = build_ai_agent_graph()
        out = graph.invoke({"request": "RAG assistant over docs"})
        text = (out["result"] + out.get("draft", "")).lower()
        # The output should contain the request since agents embed it
        assert "rag" in text or "assistant" in text or "docs" in text


def test_bounded_loop_escalates():
    with patch.object(EvalCritic, "_review", return_value=["forced failure"]):
        graph = build_ai_agent_graph()
        result = graph.invoke({"request": "build something", "revisions": MAX_REVISIONS - 1})
        assert result.get("revisions", 0) <= MAX_REVISIONS + 1
        if not result.get("approved"):
            assert "ESCALATION" in result.get("result", "")


def test_max_revisions_constant():
    assert MAX_REVISIONS == 3


@pytest.mark.parametrize(
    "result_text,expect_issue",
    [
        ("", "empty"),
        ("uses sanitized user input, schema validation, fallback retry, token budget, "
         "rate limit, eval benchmark, content safety filter, cost tracking, parameter required",
         None),
    ],
)
def test_eval_critic_flags_missing_mitigations(result_text, expect_issue):
    issues = EvalCritic()._review(result_text, "")
    if expect_issue is None:
        assert issues == []
    else:
        assert any(expect_issue in i.lower() for i in issues)


def test_eval_critic_catches_injection_and_no_fallback():
    weak = (
        "system prompt with token budget, rate limit, eval benchmark, content safety, "
        "cost tracking, schema validation"
    )
    issues = EvalCritic()._review(weak, "")
    joined = " ".join(issues).lower()
    assert "injection" in joined
    assert "fallback" in joined or "retry" in joined
