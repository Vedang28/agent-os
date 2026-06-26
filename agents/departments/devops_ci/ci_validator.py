import json

from core.state import AgentState
from infra.telemetry import get_logger
from agents.llm import call_llm
from agents.prompts import DEVOPS_CI_VALIDATOR

logger = get_logger("devops_ci.ci_validator")

_FORBIDDEN_SHORTCUTS = ["--no-verify", "skip", "disable", "delete test"]


class CiValidator:
    name = "devops_ci.ci_validator"
    role = "critic"

    SYSTEM_PROMPT = DEVOPS_CI_VALIDATOR

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
                "ci_validator rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("ci_validator approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []

        if not result or not result.strip():
            return ["CI fix output is empty"]

        try:
            output = json.loads(result)
        except json.JSONDecodeError:
            return ["CI fix output is not valid structured output"]

        try:
            plan = json.loads(draft) if draft else {}
        except json.JSONDecodeError:
            plan = {}

        failure_types = plan.get("failure_types", [])
        fixes = output.get("fixes", [])

        if not fixes:
            issues.append("No fixes proposed for the CI failure")
            return issues

        addressed = {f.get("failure_type") for f in fixes}
        for ftype in failure_types:
            if ftype not in addressed:
                issues.append(f"Failure type not addressed: {ftype}")

        if any(not f.get("root_cause") for f in fixes):
            issues.append("Fix addresses symptom, not root cause")

        if output.get("checks_skipped"):
            issues.append(
                f"Fix skips required checks: {output['checks_skipped']}"
            )

        if output.get("forbidden_shortcuts_used"):
            issues.append(
                f"Forbidden shortcut used: {output['forbidden_shortcuts_used']}"
            )

        pipeline = output.get("pipeline_status", {})
        if pipeline.get("overall") != "green":
            issues.append("Pipeline is not green after fix")
        if output.get("stages_regressed"):
            issues.append(f"Other stages regressed: {output['stages_regressed']}")

        if "flaky" in failure_types and not output.get("quarantined_tests"):
            issues.append("Flaky failure not quarantined with a tracking note")

        return issues
