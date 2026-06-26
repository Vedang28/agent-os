from agents.llm import call_llm
from agents.prompts import FRONTEND_REVIEWER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("frontend.reviewer")


class FrontendReviewer:
    name = "frontend.reviewer"
    role = "critic"
    SYSTEM_PROMPT = FRONTEND_REVIEWER

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
                "frontend reviewer rejected, revisions=%d, reason=%s",
                revisions + 1, issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }
        logger.info("frontend reviewer approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty"]
        low = result.lower()

        if "aria-" not in low and "role=" not in low:
            issues.append(
                "Missing accessibility attributes (no aria-* or role on interactive elements)"
            )
        if ".map(" in low and "key=" not in low:
            issues.append("Missing keys in rendered lists")
        if (
            "usememo" not in low
            and "usecallback" not in low
            and "memo(" not in low
        ):
            issues.append(
                "Re-render performance: no memo/useMemo/useCallback for stable handlers"
            )
        if "errorboundary" not in low and "error boundary" not in low:
            issues.append("Missing error boundary around the rendered tree")
        if (
            "isloading" not in low
            and "skeleton" not in low
            and "loading" not in low
        ):
            issues.append("Missing loading/skeleton state")
        if (
            "interface" not in low
            and "type " not in low
            and ": react.fc" not in low
        ):
            issues.append("Missing TypeScript prop types")
        if (
            "sm:" not in low
            and "md:" not in low
            and "lg:" not in low
            and "responsive" not in low
            and "breakpoint" not in low
        ):
            issues.append("Missing responsive design considerations")
        if "import * as" in low and "tree-shak" not in low:
            issues.append("Large namespace import without tree-shaking")
        if "metadata" in low or "page.tsx" in low or "<page" in low:
            if "title" not in low and "meta" not in low and "opengraph" not in low:
                issues.append("Missing SEO meta tags for page")
        return issues
