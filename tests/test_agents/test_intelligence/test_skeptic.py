import json

import pytest

from agents.departments.intelligence.skeptic import Skeptic


class TestSkeptic:
    @pytest.mark.asyncio
    async def test_approves_good_briefing(self):
        briefing = {
            "title": "Daily Briefing",
            "items": [
                {"title": "News", "source": "HN", "summary": "A substantial news summary here"},
            ],
        }
        skeptic = Skeptic()
        result = await skeptic.run({"result": json.dumps(briefing)})
        assert result["approved"] is True

    @pytest.mark.asyncio
    async def test_rejects_empty_briefing(self):
        briefing = {"title": "Empty", "items": []}
        skeptic = Skeptic()
        result = await skeptic.run({"result": json.dumps(briefing)})
        assert result["approved"] is False
        assert "no items" in result["critique"]["reason"].lower()

    @pytest.mark.asyncio
    async def test_rejects_duplicate_items(self):
        briefing = {
            "items": [
                {"title": "Known Item", "source": "HN", "summary": "Already in brain with enough text"},
            ],
        }
        brain_context = [{"title": "Known Item", "content": "old"}]
        skeptic = Skeptic()
        result = await skeptic.run({
            "result": json.dumps(briefing),
            "brain_context": brain_context,
        })
        assert result["approved"] is False
        assert "duplicate" in result["critique"]["reason"].lower()

    @pytest.mark.asyncio
    async def test_rejects_missing_source(self):
        briefing = {
            "items": [
                {"title": "No Source", "source": "", "summary": "Some text that is long enough"},
            ],
        }
        skeptic = Skeptic()
        result = await skeptic.run({"result": json.dumps(briefing)})
        assert result["approved"] is False
        assert "source" in result["critique"]["reason"].lower()

    @pytest.mark.asyncio
    async def test_increments_revisions(self):
        briefing = {"items": []}
        skeptic = Skeptic()
        result = await skeptic.run({"result": json.dumps(briefing), "revisions": 2})
        assert result["revisions"] == 3

    @pytest.mark.asyncio
    async def test_rejects_short_summary(self):
        briefing = {
            "items": [
                {"title": "Short", "source": "HN", "summary": "Too short"},
            ],
        }
        skeptic = Skeptic()
        result = await skeptic.run({"result": json.dumps(briefing)})
        assert result["approved"] is False
