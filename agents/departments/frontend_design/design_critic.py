from agents.llm import call_llm
from agents.prompts import FRONTEND_DESIGN_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("frontend_design.design_critic")


class DesignCritic:
    name = "frontend_design.design_critic"
    role = "critic"
    SYSTEM_PROMPT = FRONTEND_DESIGN_CRITIC

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
            logger.info(
                "design_critic rejected, revisions=%d, reason=%s",
                revisions + 1, issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }
        logger.info("design_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty"]
        low = result.lower()

        if "dark" not in low:
            issues.append("Missing dark mode variants")
        if (
            "min-width" not in low
            and "breakpoint" not in low
            and "sm:" not in low
            and "md:" not in low
        ):
            issues.append("No responsive breakpoints defined")
        if "--text-" not in low and "type scale" not in low and "typography" not in low:
            issues.append("Inconsistent or missing typography scale")
        if "focus-visible" not in low and "focus" not in low:
            issues.append("Missing focus states for interactive elements")
        if "prefers-reduced-motion" not in low and "motion-reduce" not in low:
            issues.append("No prefers-reduced-motion / motion-reduce handling")
        if "contrast" not in low:
            issues.append("Contrast ratios not documented (target >= 4.5:1)")
        # mixed spacing units: px alongside rem without a consistency note
        if "px" in low and "rem" in low and "consisten" not in low:
            issues.append("Inconsistent spacing units (mixed px and rem)")
        return issues
