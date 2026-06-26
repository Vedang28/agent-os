from agents.prompts import SDR_MESSAGE_WRITER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("sdr.message_writer")


class MessageWriter:
    name = "sdr.message_writer"
    role = "worker"

    SYSTEM_PROMPT = SDR_MESSAGE_WRITER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")
        prior = state.get("result", "")

        user_prompt = f"Outreach plan:\n{draft}\n\nRequest: {request}"
        if prior:
            user_prompt += f"\n\nPrevious output:\n{prior}"
        if critique and revisions > 0:
            fixes = critique.get("suggestions", [critique.get("reason", "")])
            fix_lines = "\n".join(f"- {f}" for f in fixes)
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n{fix_lines}"

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info(
            "message_writer produced messages revision=%d", revisions
        )
        return {"result": result}
