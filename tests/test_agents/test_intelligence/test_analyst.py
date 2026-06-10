import json
from unittest.mock import MagicMock

import pytest

from agents.departments.intelligence.analyst import Analyst


class TestAnalyst:
    @pytest.mark.asyncio
    async def test_produces_nonempty_result(self):
        items = [{"title": "Test", "source": "HN", "summary": "A test item", "relevance": "relevant"}]
        analyst = Analyst()
        result = await analyst.run({"draft": json.dumps(items), "request": "briefing"})
        assert result.get("result")

    @pytest.mark.asyncio
    async def test_result_is_structured_briefing(self):
        items = [{"title": "Test", "source": "HN", "summary": "A test", "relevance": "yes"}]
        analyst = Analyst()
        result = await analyst.run({"draft": json.dumps(items)})
        briefing = json.loads(result["result"])
        assert "title" in briefing
        assert "items" in briefing
        assert "actionable_insights" in briefing

    @pytest.mark.asyncio
    async def test_writes_note_to_brain(self):
        mock_obsidian = MagicMock()
        items = [{"title": "Test", "source": "HN", "summary": "A test", "relevance": "yes"}]
        analyst = Analyst(obsidian=mock_obsidian)
        await analyst.run({"draft": json.dumps(items)})
        mock_obsidian.write_note.assert_called_once()
        note = mock_obsidian.write_note.call_args[0][0]
        assert "briefing" in note.tags

    @pytest.mark.asyncio
    async def test_handles_empty_draft(self):
        analyst = Analyst()
        result = await analyst.run({"draft": ""})
        briefing = json.loads(result["result"])
        assert briefing["items"] == []

    @pytest.mark.asyncio
    async def test_applies_feedback_on_revision(self):
        items = [{"title": "Test", "source": "HN", "summary": "A test", "relevance": "yes"}]
        analyst = Analyst()
        result = await analyst.run({
            "draft": json.dumps(items),
            "revisions": 1,
            "critique": {"reason": "Low quality", "suggestions": []},
        })
        assert result.get("result")
