from agents.llm import call_llm
from agents.prompts import BUG_TRIAGE_REPRODUCER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("bug_triage.bug_reproducer")


class BugReproducer:
    """Worker: reproduces and diagnoses the bug."""

    name = "bug_triage.bug_reproducer"
    role = "worker"

    SYSTEM_PROMPT = BUG_TRIAGE_REPRODUCER

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

        result = await call_llm(
            task_type="code",
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
        )
        logger.info("bug_reproducer diagnosed (revision=%d)", revisions)
        return {"result": result}
