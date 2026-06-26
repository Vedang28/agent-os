import re

from agents.llm import call_llm
from agents.prompts import TESTING_BUG_TRIAGER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("testing.bug_triager")

_SECRET_IMPORT = re.compile(
    r"(import|from)\s+.*(secret|credential|prod_config|production_settings)",
    re.IGNORECASE,
)


class BugTriager:
    name = "testing.bug_triager"
    role = "critic"

    SYSTEM_PROMPT = TESTING_BUG_TRIAGER

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)

        llm_review = await call_llm(
            task_type="code", system=self.SYSTEM_PROMPT,
            user=f"Draft/Plan:\n{draft}\n\nImplementation to review:\n{result}",
        )
        if "APPROVED" not in llm_review.upper() and llm_review.strip():
            for line in llm_review.strip().split("\n"):
                line = line.strip().lstrip("-•*123456789. ")
                if line and line not in issues:
                    issues.append(line)

        if issues:
            logger.info(
                "bug_triager rejected, revisions=%d, reason=%s",
                revisions + 1, issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("bug_triager approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []

        if not result or not result.strip():
            return ["Result is empty — no tests to triage"]

        if "FAILURES DETECTED" in result:
            issues.append(
                "Test failures detected — classify each as real bug vs flaky vs test bug before approval"
            )

        if re.search(r"def test_\w+\([^)]*\):\s*\n\s*pass\b", result):
            issues.append("Empty test body (pass) — test asserts nothing")

        if re.search(r"\bassert\s+True\b", result):
            issues.append("Tautological `assert True` — assert the actual value")

        test_funcs = re.findall(r"def (test_\w+)\([^)]*\):", result)
        has_assert = "assert" in result or "pytest.raises" in result or "expect(" in result
        if test_funcs and not has_assert:
            issues.append("Test functions present but no assertions found")

        if re.search(r"time\.sleep\(", result) or re.search(r"\bsleep\(\d", result):
            issues.append("Hardcoded sleep in tests — flaky; use polling/waits or fake the clock")

        if "boundary" not in result.lower() and "parametrize" not in result.lower():
            issues.append("Missing edge-case coverage (empty/null/boundary) — add parametrized cases")

        if "pytest.raises" not in result and "with pytest.raises" not in result and "assertRaises" not in result:
            issues.append("No negative tests — add expected-failure cases (pytest.raises)")

        for fn in test_funcs:
            if fn in ("test_1", "test_2", "test_foo", "test_case", "test_it", "test_thing"):
                issues.append(f"Non-descriptive test name `{fn}` — name should state the behavior")
                break

        mutates = re.search(r"(os\.environ\[|global \w+|\.append\(|\.update\()", result)
        cleans = "yield" in result or "teardown" in result.lower() or "tmp_path" in result or "addfinalizer" in result
        if mutates and not cleans:
            issues.append("Test mutates shared/global state without cleanup/teardown fixture")

        if _SECRET_IMPORT.search(result):
            issues.append("Test imports production secrets/credentials — use fixtures or fakes")

        return issues
