from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("engineering.code_doctor")


class CodeDoctor:
    name = "engineering.code_doctor"
    role = "critic"

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)

        if issues:
            logger.info(
                "code_doctor rejected, revisions=%d, reason=%s",
                revisions + 1, issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("code_doctor approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues = []
        if not result or not result.strip():
            issues.append("Result is empty")
        if draft and result and draft.strip() and "Implementation" not in result:
            issues.append("Result does not reference the implementation plan")
        return issues
