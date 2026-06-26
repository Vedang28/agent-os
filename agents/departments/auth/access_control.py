from agents.llm import call_llm
from agents.prompts import AUTH_ACCESS_CONTROL
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("auth.access_control")


class AccessControlBuilder:
    name = "auth.access_control"
    role = "worker"

    SYSTEM_PROMPT = AUTH_ACCESS_CONTROL

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        prior = state.get("result", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)

        user_prompt = (
            f"Existing implementation:\n{prior}\n\nOriginal request: {request}"
        )

        result = await call_llm(
            task_type="code",
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
        )
        logger.info("access_control produced rules, revision=%d", revisions)
        return {"result": result}
