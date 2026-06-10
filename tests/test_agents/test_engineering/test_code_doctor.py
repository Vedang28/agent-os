import asyncio

from agents.departments.engineering.code_doctor import CodeDoctor


def test_approves_good_result():
    doc = CodeDoctor()
    state = {
        "result": "Implementation:\nSome code here",
        "draft": "Plan for building",
        "revisions": 0,
    }
    result = asyncio.run(doc.run(state))
    assert result["approved"] is True


def test_rejects_empty_result():
    doc = CodeDoctor()
    state = {"result": "", "draft": "Plan for building", "revisions": 0}
    result = asyncio.run(doc.run(state))
    assert result["approved"] is False
    assert result["critique"]["reason"] == "Result is empty"


def test_rejects_whitespace_only():
    doc = CodeDoctor()
    state = {"result": "   \n  ", "draft": "Plan for building", "revisions": 0}
    result = asyncio.run(doc.run(state))
    assert result["approved"] is False


def test_increments_revisions():
    doc = CodeDoctor()
    state = {"result": "", "draft": "Plan", "revisions": 1}
    result = asyncio.run(doc.run(state))
    assert result["revisions"] == 2


def test_critique_has_suggestions():
    doc = CodeDoctor()
    state = {"result": "", "draft": "Plan", "revisions": 0}
    result = asyncio.run(doc.run(state))
    assert "suggestions" in result["critique"]
    assert isinstance(result["critique"]["suggestions"], list)
