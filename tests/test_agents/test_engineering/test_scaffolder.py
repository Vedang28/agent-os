import asyncio

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
    """Agent now builds prompt text directly — verify critique appears in output."""
    scaff = Scaffolder()
    state = {
        "request": "build an API",
        "draft": "Plan: build endpoints",
        "revisions": 1,
        "critique": {"reason": "Missing error handling", "suggestions": ["Missing error handling"]},
    }
    result = asyncio.run(scaff.run(state))
    assert result["result"]
    assert "Missing error handling" in result["result"]


def test_first_pass_no_revision_label():
    scaff = Scaffolder()
    state = {"request": "build an API", "draft": "Some plan", "revisions": 0}
    result = asyncio.run(scaff.run(state))
    assert "Revised" not in result["result"]
