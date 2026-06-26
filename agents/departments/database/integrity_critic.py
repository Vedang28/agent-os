from agents.llm import call_llm
from agents.prompts import DATABASE_INTEGRITY_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("database.integrity_critic")


class DataIntegrityCritic:
    name = "database.integrity_critic"
    role = "critic"

    SYSTEM_PROMPT = DATABASE_INTEGRITY_CRITIC

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
            logger.info("integrity_critic rejected, revisions=%d, reason=%s", revisions + 1, issues[0])
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }
        logger.info("integrity_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty"]
        low = result.lower()

        if "references" not in low and "foreign key" not in low:
            issues.append("Missing foreign key constraints between related tables")
        if "create index" not in low and "index" not in low:
            issues.append("Missing indexes on frequently queried / join columns")
        if "not null" not in low:
            issues.append("Missing NOT NULL constraints on required fields")
        if "down:" not in low and "rollback" not in low and "drop table" not in low:
            issues.append("No rollback plan in migration")
        if "on delete cascade" in low and "restrict" not in low:
            issues.append("CASCADE DELETE used without a safeguard (consider RESTRICT)")
        return issues
