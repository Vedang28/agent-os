import json
from unittest.mock import MagicMock

import pytest

from agents.departments.intelligence.scout import Scout
from brain.schema import Note


class TestScout:
    @pytest.mark.asyncio
    async def test_produces_nonempty_draft(self):
        scout = Scout()
        result = await scout.run({"request": "Generate intelligence briefing"})
        assert result.get("draft")
        items = json.loads(result["draft"])
        assert len(items) > 0

    @pytest.mark.asyncio
    async def test_each_item_has_required_fields(self):
        scout = Scout()
        result = await scout.run({"request": "briefing"})
        items = json.loads(result["draft"])
        for item in items:
            assert "title" in item
            assert "source" in item
            assert "summary" in item

    @pytest.mark.asyncio
    async def test_queries_brain_context(self):
        mock_librarian = MagicMock()
        mock_librarian.query.return_value = [
            Note(title="Existing Note", content="old news", tags=["briefing"])
        ]
        scout = Scout(librarian=mock_librarian)
        result = await scout.run({"request": "briefing"})
        mock_librarian.query.assert_called_once()
        assert len(result.get("brain_context", [])) > 0

    @pytest.mark.asyncio
    async def test_filters_known_items(self):
        mock_librarian = MagicMock()
        mock_librarian.query.return_value = [
            Note(
                title="LangGraph adds native streaming support",
                content="already known",
            )
        ]
        scout = Scout(librarian=mock_librarian)
        result = await scout.run({"request": "briefing"})
        items = json.loads(result["draft"])
        titles = [i["title"] for i in items]
        assert "LangGraph adds native streaming support" not in titles

    @pytest.mark.asyncio
    async def test_sets_brain_context(self):
        scout = Scout()
        result = await scout.run({"request": "briefing"})
        assert "brain_context" in result
