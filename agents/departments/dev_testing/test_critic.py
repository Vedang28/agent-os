import json
import re

from core.state import AgentState
from infra.telemetry import get_logger
from agents.llm import call_llm
from agents.prompts import DEV_TESTING_CRITIC

logger = get_logger("dev_testing.critic")

_BOUNDARY_TERMS = ("null", "none", "empty", "boundary", "0", "-1", "max")


class DevTestCritic:
    """Critic: reviews test quality, not just presence.

    Rejects tests that can't fail, lack assertion messages, skip error
    paths, hardcode data instead of fixtures, test implementation details,
    or omit parametrization for similar cases.
    """

    name = "dev_testing.critic"
    role = "critic"

    SYSTEM_PROMPT = DEV_TESTING_CRITIC

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
                "test critic rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("test critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty — no tests produced"]

        try:
            payload = json.loads(result)
        except json.JSONDecodeError:
            return ["Test output is not valid structured output"]

        test_files = payload.get("test_files", {})
        if not test_files:
            return ["No test files produced"]

        all_code = "\n".join(test_files.values())
        low = all_code.lower()

        if "assert" not in low:
            issues.append("Tests have no assertions — they can never fail")

        if re.search(r"assert\s+true\b", low) or "assert 1 == 1" in low:
            issues.append("Test that always passes (assert True / tautology)")

        if not re.search(r"assert[^\n]*,[^\n]*[\"']", all_code):
            issues.append("Assertions without messages — failures will be opaque")

        if "pytest.raises" not in all_code and "assertraises" not in low:
            issues.append("Missing error-path tests (no pytest.raises)")

        if not any(term in low for term in _BOUNDARY_TERMS):
            issues.append("Missing edge cases (null, empty, boundary values)")

        if "parametrize" not in low:
            issues.append("No parametrize for similar cases — duplicated test bodies")

        if "fixture" not in low and not payload.get("fixtures_defined"):
            issues.append("Hardcoded test data instead of fixtures")

        if not payload.get("has_cleanup", False) and "tmp_path" not in low and "teardown" not in low:
            issues.append("Missing cleanup — tests may leak state between runs")

        if self._tests_implementation_details(low):
            issues.append(
                "Testing implementation details (private attrs / call counts) "
                "instead of behavior"
            )

        return issues

    def _tests_implementation_details(self, low: str) -> bool:
        return ("._" in low and "assert" in low) or "call_count ==" in low
