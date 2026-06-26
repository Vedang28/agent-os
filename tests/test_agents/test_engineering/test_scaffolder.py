import asyncio
from unittest.mock import AsyncMock, patch

from agents.departments.engineering.scaffolder import Scaffolder


def test_produces_result():
    scaff = Scaffolder()
    state = {"request": "build an API", "draft": "Plan: build endpoints"}
    result = asyncio.run(scaff.run(state))
    assert result["result"]
    assert len(result["result"]) > 0


def test_result_references_draft():
    scaff = Scaffolder()
    state = {"request": "build an API", "draft": "Plan: build endpoints"}
    result = asyncio.run(scaff.run(state))
    assert "Plan: build endpoints" in result["result"]


def test_revision_includes_feedback():
    scaff = Scaffolder()
    state = {
        "request": "build an API",
        "draft": "Plan: build endpoints",
        "revisions": 1,
        "critique": {"reason": "Missing error handling", "suggestions": []},
    }
    with patch(
        "agents.departments.engineering.scaffolder.call_llm",
        new=AsyncMock(return_value="some implementation"),
    ) as mock_llm:
        result = asyncio.run(scaff.run(state))
    assert result["result"]
    user_prompt = mock_llm.call_args.kwargs["user"]
    assert "revision 1" in user_prompt
    assert "Missing error handling" in user_prompt


def test_first_pass_no_revision_label():
    scaff = Scaffolder()
    state = {"request": "build an API", "draft": "Some plan", "revisions": 0}
    result = asyncio.run(scaff.run(state))
    assert "Revised" not in result["result"]
