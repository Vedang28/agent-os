import json

from agents.llm import call_llm
from agents.prompts import CODE_REVIEW_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("code_review.critic")

_STYLE_CATEGORIES = {"naming", "style", "formatting"}
_LOGIC_CATEGORIES = {
    "correctness",
    "error_handling",
    "race_condition",
    "security",
    "complexity",
}


class ReviewCritic:
    """Critic: reviews the review itself for depth and balance.

    Rejects reviews that are all-nits-no-logic, skip security/performance,
    bikeshed minor issues while missing majors, or give no actionable
    suggestions and no positive feedback.
    """

    name = "code_review.critic"
    role = "critic"
    SYSTEM_PROMPT = CODE_REVIEW_CRITIC

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
                "review critic rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("review critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty — no review produced"]

        try:
            review = json.loads(result)
        except json.JSONDecodeError:
            return ["Review is not valid structured output"]

        comments = review.get("comments", [])
        if not comments:
            return ["Review contains no comments at all"]

        categories = [c.get("category", "") for c in comments]
        severities = [c.get("severity", "") for c in comments]

        if not any(cat in _LOGIC_CATEGORIES for cat in categories):
            issues.append(
                "Superficial review: only style/nit comments, no logic-level "
                "bugs or error-handling issues found"
            )

        plan = self._parse_plan(draft)
        planned_risks = set(plan.get("risk_areas", []))
        if "security" in planned_risks or "auth" in planned_risks:
            if not review.get("security_review", "").strip() and not any(
                c.get("category") == "security" for c in comments
            ):
                issues.append(
                    "Plan flagged security risk but review has no security assessment"
                )

        if not review.get("performance_review", "").strip():
            issues.append("Missing performance assessment")

        if not review.get("test_coverage_review", "").strip():
            issues.append("Missing test coverage check")

        nit_count = severities.count("nit") + severities.count("minor")
        major_count = severities.count("critical") + severities.count("major")
        if nit_count > 0 and major_count == 0 and len(comments) > 2:
            issues.append(
                "Bikeshedding: many minor/nit comments but no major issues "
                "identified — likely missing real problems"
            )

        if not any(c.get("suggestion") for c in comments):
            issues.append(
                "No actionable suggestions — comments say what's wrong but not "
                "how to fix it"
            )

        if not review.get("positive_feedback"):
            issues.append("Missing positive feedback for good patterns")

        focus_files = plan.get("focus_files") or []
        reviewed = set(review.get("files_reviewed", []))
        missing = [f for f in focus_files if f not in reviewed]
        if missing:
            issues.append(
                f"Planned focus files not reviewed: {', '.join(missing[:3])}"
            )

        return issues

    def _parse_plan(self, draft: str) -> dict:
        try:
            return json.loads(draft)
        except (json.JSONDecodeError, TypeError):
            return {}
