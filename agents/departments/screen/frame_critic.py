import json

from agents.prompts import SCREEN_FRAME_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("screen.frame_critic")


class FrameCritic:
    name = "screen.frame_critic"
    role = "critic"

    SYSTEM_PROMPT = SCREEN_FRAME_CRITIC

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info(
                "frame_critic rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("frame_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []

        if not result or not result.strip():
            return ["Screen analysis is empty"]

        try:
            analysis = json.loads(result)
        except json.JSONDecodeError:
            return ["Screen analysis is not valid structured output"]

        try:
            plan = json.loads(draft) if draft else {}
        except json.JSONDecodeError:
            plan = {}
        objectives = plan.get("objectives", [])

        elements = analysis.get("ui_elements", [])
        interactive = analysis.get("interactive_elements", [])

        if not elements:
            issues.append("Missing UI elements: no interface elements were identified")

        if not interactive:
            issues.append(
                "No clickable/interactive elements identified (buttons, links)"
            )

        classified_types = {el.get("type") for el in elements if isinstance(el, dict)}
        if elements and None in classified_types:
            issues.append("Incorrect element classification: element missing a type")

        if "text" in objectives and not analysis.get("extracted_text"):
            issues.append(
                "Incomplete text extraction: no text captured from screen regions"
            )

        if "ui_elements" in objectives and not any(
            el.get("type") in ("input", "select") for el in elements if isinstance(el, dict)
        ):
            issues.append("Missing form field detection (no input/select elements)")

        if "error" in objectives and "error_states" not in analysis:
            issues.append("Missing error/warning state detection")

        if "layout" in objectives and not analysis.get("layout"):
            issues.append(
                "Layout structure not captured (grid/flex/columns missing)"
            )

        if "responsive_state" not in analysis or analysis.get("responsive_state") in (
            None,
            "unknown",
        ):
            issues.append("No responsive state assessment")

        accessibility = analysis.get("accessibility")
        if not accessibility or not accessibility.get("assessed"):
            issues.append(
                "Missing accessibility assessment (focus rings, aria indicators)"
            )

        return issues
