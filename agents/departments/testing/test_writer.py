from agents.prompts import TESTING_TEST_WRITER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("testing.test_writer")


class TestWriter:
    name = "testing.test_writer"
    role = "worker"

    SYSTEM_PROMPT = TESTING_TEST_WRITER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        user_prompt = f"Plan/Draft:\n{draft}\n\nOriginal request: {request}"
        if critique and revisions > 0:
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n"
            for s in critique.get("suggestions", [critique.get("reason", "")]):
                user_prompt += f"- {s}\n"

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("test_writer produced result, revision=%d", revisions)
        return {"result": result}
