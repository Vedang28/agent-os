import json

from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import PERFORMANCE_VALIDATOR

logger = get_logger("performance.perf_validator")


class PerfValidator:
    name = "performance.perf_validator"
    role = "critic"

    SYSTEM_PROMPT = PERFORMANCE_VALIDATOR

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info(
                "perf_validator rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("perf_validator approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []

        if not result or not result.strip():
            return ["Performance output is empty"]

        try:
            output = json.loads(result)
        except json.JSONDecodeError:
            return ["Performance output is not valid structured output"]

        try:
            plan = json.loads(draft) if draft else {}
        except json.JSONDecodeError:
            plan = {}

        dimensions = plan.get("dimensions", [])
        optimizations = output.get("optimizations", [])

        if not optimizations:
            issues.append("No optimizations proposed")
            return issues

        addressed = {o.get("dimension") for o in optimizations}
        for dim in dimensions:
            if dim not in addressed:
                issues.append(f"Dimension not addressed: {dim}")

        if not output.get("baseline_metrics"):
            issues.append("Missing baseline metrics (no before/after comparison)")

        if not output.get("after_metrics"):
            issues.append("Missing post-optimization metrics")

        regressions = output.get("regressions", [])
        if regressions:
            issues.append(f"Performance regression detected: {regressions[0]}")

        if not output.get("correctness_preserved"):
            issues.append("Optimization does not preserve functional correctness")

        budget_status = output.get("budget_status", {})
        exceeded = [k for k, v in budget_status.items() if v == "exceeded"]
        if exceeded:
            issues.append(f"Budget exceeded after optimization: {', '.join(exceeded)}")

        return issues
