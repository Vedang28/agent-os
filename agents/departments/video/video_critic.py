import json

from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import VIDEO_CRITIC

logger = get_logger("video.video_critic")


class VideoCritic:
    name = "video.video_critic"
    role = "critic"

    SYSTEM_PROMPT = VIDEO_CRITIC

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info(
                "video_critic rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("video_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []

        if not result or not result.strip():
            return ["Video analysis is empty"]

        try:
            analysis = json.loads(result)
        except json.JSONDecodeError:
            return ["Video analysis is not valid structured output"]

        try:
            plan = json.loads(draft) if draft else {}
        except json.JSONDecodeError:
            plan = {}
        approaches = plan.get("analysis_approach", [])

        scenes = analysis.get("scenes", [])
        transcript = analysis.get("transcript", [])

        if "scene_detection" in approaches and not scenes:
            issues.append("Missing key scenes in timeline")

        for scene in scenes:
            if not scene.get("start"):
                issues.append("Timestamps don't match described content (scene missing start)")
                break
            if not scene.get("description"):
                issues.append("Scene missing description / temporal context")
                break

        if "transcript" in approaches and not transcript:
            issues.append("Incomplete transcript: no transcript segments extracted")

        if ("speakers" in approaches or "transcript" in approaches) and not analysis.get(
            "speakers"
        ):
            issues.append("Speaker changes not detected (no speakers identified)")

        if not analysis.get("on_screen_text"):
            issues.append("On-screen text/graphics not captured")

        if not analysis.get("content_categories"):
            issues.append("Content categorization missing or seems incorrect")

        coverage = analysis.get("timeline_coverage", {})
        if not coverage:
            issues.append("Missing temporal context: no timeline coverage reported")
        elif coverage.get("gaps"):
            issues.append(f"Timeline has coverage gaps: {coverage['gaps']}")
        elif coverage.get("covered_seconds", 0) < coverage.get("total_seconds", 0):
            issues.append("Timeline has coverage gaps (uncovered duration)")

        if "sentiment" in approaches and not analysis.get("sentiment"):
            issues.append("No sentiment or tone assessment")

        return issues
