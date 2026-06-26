import re

from agents.llm import call_llm
from agents.prompts import TESTING_TEST_EXECUTOR
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("testing.test_executor")

_SAFE_COMMAND = re.compile(r"^[\w\s\-./=:]+$")


class TestExecutor:
    name = "testing.test_executor"
    role = "worker"

    SYSTEM_PROMPT = TESTING_TEST_EXECUTOR

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        suite = state.get("result", "")
        request = state.get("request", "")
        command = self._infer_command(suite)

        report = f"Execution report for: {request}\n"
        report += f"Command: {command}\n\n"

        output = await self._execute(command)
        if output is None:
            report += "No executor tool available — static analysis only.\n"
            report += self._static_summary(suite)
        else:
            report += output + "\n\n"
            report += self._parse_results(output)

        analysis = await call_llm(
            task_type="code", system=self.SYSTEM_PROMPT,
            user=f"Test suite:\n{suite}\n\nExecution report:\n{report}",
        )
        report += "\n\nLLM analysis:\n" + analysis
        report += "\n\n" + suite
        logger.info("test_executor finished for request=%r", request[:80])
        return {"result": report}

    def _infer_command(self, suite: str) -> str:
        if "import pytest" in suite or "def test_" in suite:
            return "pytest -q --no-header"
        if "describe(" in suite or "it(" in suite:
            return "npx jest --silent"
        return "pytest -q"

    async def _execute(self, command: str) -> str | None:
        if not self._tools:
            return None
        if not _SAFE_COMMAND.match(command):
            logger.warning("refusing to run unsafe command: %r", command)
            return None
        try:
            bash = self._tools.get("bash")
        except (KeyError, AttributeError):
            return None
        try:
            return await bash.execute(command=command)
        except PermissionError as exc:
            logger.warning("executor blocked by permission gate: %s", exc)
            return f"BLOCKED: {exc}"

    def _parse_results(self, output: str) -> str:
        failed = len(re.findall(r"\bFAILED\b", output)) + len(re.findall(r"\bFAIL\b", output))
        passed = len(re.findall(r"\bPASSED\b", output)) + len(re.findall(r"\bPASS\b", output))
        exit_match = re.search(r"exit_code:\s*(-?\d+)", output)
        exit_code = exit_match.group(1) if exit_match else "unknown"

        summary = "Result summary:\n"
        summary += f"- exit_code: {exit_code}\n"
        summary += f"- passed: {passed}\n"
        summary += f"- failed: {failed}\n"
        if failed or exit_code not in ("0", "unknown"):
            summary += "- status: FAILURES DETECTED — see triage\n"
        else:
            summary += "- status: green\n"
        return summary

    def _static_summary(self, suite: str) -> str:
        test_count = len(re.findall(r"def test_\w+", suite)) + len(re.findall(r"\bit\(", suite))
        assert_count = len(re.findall(r"\bassert\b", suite)) + len(re.findall(r"expect\(", suite))
        return (
            "Static summary:\n"
            f"- declared tests: {test_count}\n"
            f"- assertions: {assert_count}\n"
        )
