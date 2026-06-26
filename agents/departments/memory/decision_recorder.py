from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import MEMORY_DECISION_RECORDER

logger = get_logger("memory.decision_recorder")


class DecisionRecorder:
    """Worker: turns logged decisions into ADR entries and persists them.

    Consumes the session scribe's draft, extracts decisions worth recording,
    and emits a combined result (session log + ADRs) for the auditor.
    """

    name = "memory.decision_recorder"
    role = "worker"

    SYSTEM_PROMPT = MEMORY_DECISION_RECORDER

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
        logger.info("produced result, revision=%d", revisions)
        return {"result": result}
