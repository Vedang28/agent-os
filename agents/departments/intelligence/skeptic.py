import json

from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("intelligence.skeptic")


class Skeptic:
    name = "intelligence.skeptic"
    role = "critic"

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        revisions = state.get("revisions", 0)

        try:
            briefing = json.loads(result) if result else {}
        except json.JSONDecodeError:
            briefing = {}

        issues = self._review(briefing, state.get("brain_context", []))

        if issues:
            logger.info(
                "skeptic rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("skeptic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, briefing: dict, brain_context: list[dict]) -> list[str]:
        issues = []
        items = briefing.get("items", [])

        if not items:
            issues.append("Briefing contains no items")
            return issues

        known_titles = {ctx.get("title", "") for ctx in brain_context}
        duplicates = [
            item.get("title", "")
            for item in items
            if item.get("title", "") in known_titles
        ]
        if duplicates:
            issues.append(f"Duplicate items already in brain: {', '.join(duplicates)}")

        for item in items:
            if not item.get("source"):
                issues.append(f"Item missing source: {item.get('title', 'unknown')}")
            if not item.get("summary") or len(item.get("summary", "")) < 10:
                issues.append(
                    f"Low-signal item (summary too short): {item.get('title', 'unknown')}"
                )

        return issues
