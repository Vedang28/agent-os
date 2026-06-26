from unittest.mock import AsyncMock, patch

import pytest

from agents.departments.ai_agent.eval_critic import EvalCritic
from agents.departments.ai_agent.graph import MAX_REVISIONS, build_ai_agent_graph

_RICH_AI_OUTPUT = (
    "Prompt architecture with sanitized user input delimiters. "
    "Schema validation on all model outputs with fallback retry logic. "
    "Token budget: max_tokens=4096. Rate limit: 10 req/min per user. "
    "Eval benchmark with golden test cases. Content safety filter on input/output. "
    "Cost tracking per request. Tool parameter definitions with required fields "
    "and additionalProperties=false."
)


def _mock_llm(**kwargs):
    return AsyncMock(return_value=_RICH_AI_OUTPUT)


def test_happy_path_approves():
    with patch("agents.departments.ai_agent.prompt_engineer.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ai_agent.tool_builder.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ai_agent.model_router_agent.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ai_agent.eval_critic.call_llm", new_callable=lambda: AsyncMock(return_value="APPROVED")):
        graph = build_ai_agent_graph()
        result = graph.invoke({"request": "build a JSON extraction AI feature with tools"})
        assert result["approved"] is True
        assert result["result"]
        assert result.get("revisions", 0) == 0


def test_output_carries_domain_signal():
    with patch("agents.departments.ai_agent.prompt_engineer.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ai_agent.tool_builder.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ai_agent.model_router_agent.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ai_agent.eval_critic.call_llm", new_callable=lambda: AsyncMock(return_value="APPROVED")):
        graph = build_ai_agent_graph()
        out = graph.invoke({"request": "RAG assistant over docs"})
        text = (out["result"] + out.get("draft", "")).lower()
        assert "fallback" in text
        assert "token" in text
        assert "rate limit" in text


def test_bounded_loop_escalates():
    with patch(
        "agents.departments.ai_agent.eval_critic.EvalCritic._review",
        return_value=["forced failure"],
    ), patch("agents.departments.ai_agent.eval_critic.call_llm", new_callable=lambda: AsyncMock(return_value="issues found")), \
       patch("agents.departments.ai_agent.prompt_engineer.call_llm", new_callable=_mock_llm), \
       patch("agents.departments.ai_agent.tool_builder.call_llm", new_callable=_mock_llm), \
       patch("agents.departments.ai_agent.model_router_agent.call_llm", new_callable=_mock_llm):
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
