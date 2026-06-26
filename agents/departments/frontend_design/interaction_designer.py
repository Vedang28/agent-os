from agents.llm import call_llm
from agents.prompts import FRONTEND_DESIGN_INTERACTION
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("frontend_design.interaction_designer")


class InteractionDesigner:
    name = "frontend_design.interaction_designer"
    role = "worker"
    SYSTEM_PROMPT = FRONTEND_DESIGN_INTERACTION

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
            f"Styles/tokens to add interactions to:\n{result}\n\n"
            f"Original request: {request}"
        )
        if critique and revisions > 0:
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n"
            for s in critique.get("suggestions", [critique.get("reason", "")]):
                user_prompt += f"- {s}\n"

        if self._tools:
            mt = self._tools.list_tools(namespace="stitch")
            if mt:
                user_prompt += f"\n\nAvailable motion tools: {', '.join(mt)}"

        interactions = await call_llm(
            task_type="code", system=self.SYSTEM_PROMPT, user=user_prompt
        )
        logger.info(
            "interaction_designer produced motion specs, revision=%d", revisions
        )
        return {"result": interactions}
