from agents.llm import call_llm
from agents.prompts import ENGINEERING_CODE_DOCTOR
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("engineering.code_doctor")


class CodeDoctor:
    SYSTEM_PROMPT = ENGINEERING_CODE_DOCTOR
    name = "engineering.code_doctor"
    role = "critic"

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)

        llm_review = await call_llm(
            task_type="code",
            system=self.SYSTEM_PROMPT,
            user=f"Plan:\n{draft}\n\nImplementation:\n{result}",
        )

        if issues:
            logger.info(
                "code_doctor rejected, revisions=%d, reason=%s",
                revisions + 1, issues[0],
            )
            return {
                "approved": False,
                "critique": {
                    "reason": issues[0],
                    "suggestions": issues,
                    "llm_review": llm_review,
                },
                "revisions": revisions + 1,
            }

        logger.info("code_doctor approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues = []
        if not result or not result.strip():
            issues.append("Result is empty")
        return issues
