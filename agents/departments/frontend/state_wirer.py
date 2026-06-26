from agents.llm import call_llm
from agents.prompts import FRONTEND_STATE_WIRER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("frontend.state_wirer")


class StateWirer:
    name = "frontend.state_wirer"
    role = "worker"
    SYSTEM_PROMPT = FRONTEND_STATE_WIRER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        user_prompt = (
            f"Plan/Draft:\n{draft}\n\n"
            f"Components to wire state into:\n{result}\n\n"
            f"Original request: {request}"
        )
        if critique and revisions > 0:
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n"
            for s in critique.get("suggestions", [critique.get("reason", "")]):
                user_prompt += f"- {s}\n"

        if self._tools:
            api = self._tools.list_tools(namespace="composio.github")
            if api:
                user_prompt += f"\n\nAvailable integration tools: {', '.join(api)}"

        wired = await call_llm(
            task_type="code", system=self.SYSTEM_PROMPT, user=user_prompt
        )
        logger.info("state_wirer wired data + state, revision=%d", revisions)
        return {"result": wired}
