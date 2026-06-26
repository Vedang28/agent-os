from agents.llm import call_llm
from agents.prompts import BACKEND_REVIEWER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("backend.reviewer")


class BackendReviewer:
    name = "backend.reviewer"
    role = "critic"

    SYSTEM_PROMPT = BACKEND_REVIEWER

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)

        llm_review = await call_llm(
            task_type="code",
            system=self.SYSTEM_PROMPT,
            user=f"Draft/Plan:\n{draft}\n\nImplementation to review:\n{result}",
        )
        if "APPROVED" not in llm_review.upper() and llm_review.strip():
            for line in llm_review.strip().split("\n"):
                line = line.strip().lstrip("-•*123456789. ")
                if line and line not in issues:
                    issues.append(line)

        if issues:
            logger.info("backend reviewer rejected, revisions=%d, reason=%s", revisions + 1, issues[0])
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }
        logger.info("backend reviewer approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty"]
        low = result.lower()

        if "try" not in low and "except" not in low and "error" not in low:
            issues.append("Missing error handling (no try/except or error middleware)")
        if "validate" not in low and "validation" not in low and "field(" not in low:
            issues.append("Missing input validation on request bodies")
        if "auth" not in low and "require_auth" not in low:
            issues.append("Missing authentication/authorization on endpoints")
        if "status_code" not in low and "200" not in low and "201" not in low:
            issues.append("No explicit HTTP status codes set")
        if "for " in low and ("await repo" in low or "query(" in low) and "n+1" not in low:
            # nested DB call inside a loop is the classic N+1 signature
            if low.count("for ") and "await repo." in low.split("for ", 1)[1]:
                issues.append("Potential N+1 query pattern: DB call inside a loop")
        return issues
