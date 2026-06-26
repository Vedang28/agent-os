from agents.prompts import BACKEND_API_BUILDER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("backend.api_builder")


class ApiBuilder:
    name = "backend.api_builder"
    role = "worker"

    SYSTEM_PROMPT = BACKEND_API_BUILDER

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
            for s in self._fixes_for(critique):
                user_prompt += f"- {s}\n"

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("api_builder produced implementation, revision=%d", revisions)
        return {"result": result}

    def _fixes_for(self, critique: dict) -> list[str]:
        return critique.get("suggestions", [critique.get("reason", "")])
