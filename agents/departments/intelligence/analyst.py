import json
from datetime import datetime, timezone

from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("intelligence.analyst")


class Analyst:
    name = "intelligence.analyst"
    role = "worker"

    def __init__(self, obsidian=None):
        self._obsidian = obsidian

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        try:
            items = json.loads(draft) if draft else []
        except json.JSONDecodeError:
            items = []

        if critique and revisions > 0:
            reason = critique.get("reason", "") if isinstance(critique, dict) else ""
            items = self._apply_feedback(items, reason)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        briefing = {
            "title": f"Daily Briefing — {today}",
            "items": items,
            "cross_references": [],
            "actionable_insights": [
                item.get("relevance", "") for item in items if item.get("relevance")
            ],
        }

        if self._obsidian:
            from brain.schema import Note

            note = Note(
                title=briefing["title"],
                content=json.dumps(briefing, indent=2),
                tags=["briefing", "intelligence"],
            )
            try:
                self._obsidian.write_note(note)
                logger.info("wrote briefing note: %s", briefing["title"])
            except Exception as e:
                logger.error("failed to write briefing note: %s", e)

        result = json.dumps(briefing, indent=2)
        logger.info(
            "analyst produced briefing with %d items, revision=%d",
            len(items),
            revisions,
        )
        return {"result": result}

    def _apply_feedback(self, items: list[dict], reason: str) -> list[dict]:
        filtered = []
        for item in items:
            if "duplicate" in reason.lower() and not item.get("title"):
                continue
            if "source" in reason.lower() and not item.get("url"):
                continue
            filtered.append(item)
        return filtered if filtered else items
