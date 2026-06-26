from agents.prompts import GRAPHICS_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("graphics.graphics_critic")


class GraphicsCritic:
    name = "graphics.graphics_critic"
    role = "critic"
    SYSTEM_PROMPT = GRAPHICS_CRITIC

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info(
                "graphics_critic rejected, revisions=%d, reason=%s",
                revisions + 1, issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }
        logger.info("graphics_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty"]
        low = result.lower()

        if "alt" not in low:
            issues.append("Missing alt text for images")
        if "favicon" not in low or "16x16" not in low:
            issues.append("Missing favicon sizes")
        if "svg" not in low and "vector" not in low:
            issues.append("Raster used where vector would be better")
        if "colorblind" not in low and "color-blind" not in low and "accessible" not in low:
            issues.append("Color combinations not verified colorblind-safe")
        if "24px" not in low and "grid" not in low and "consisten" not in low:
            issues.append("Inconsistent icon sizes or styles")
        if "token" not in low and "brand" not in low:
            issues.append("Colors not tied to brand tokens (brand guideline violation)")
        return issues
