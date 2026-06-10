import asyncio
from unittest.mock import MagicMock

from agents.departments.engineering.architect import Architect
from brain.schema import Note


def test_produces_draft():
    arch = Architect()
    state = {"request": "build a REST API"}
    result = asyncio.run(arch.run(state))
    assert result["draft"]
    assert len(result["draft"]) > 0


def test_draft_references_request():
    arch = Architect()
    state = {"request": "build a user login system"}
    result = asyncio.run(arch.run(state))
    assert "user login system" in result["draft"]


def test_queries_brain():
    mock_librarian = MagicMock()
    mock_librarian.query.return_value = [
        Note(title="Auth patterns", content="Use JWT for stateless auth")
    ]
    arch = Architect(librarian=mock_librarian)
    state = {"request": "build auth"}
    result = asyncio.run(arch.run(state))

    mock_librarian.query.assert_called_once_with("build auth")
    assert len(result["brain_context"]) == 1
    assert result["brain_context"][0]["title"] == "Auth patterns"


def test_no_librarian_still_works():
    arch = Architect(librarian=None)
    state = {"request": "build something"}
    result = asyncio.run(arch.run(state))
    assert result["draft"]
    assert result["brain_context"] == []
