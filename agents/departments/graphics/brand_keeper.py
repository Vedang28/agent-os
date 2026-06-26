from agents.llm import call_llm
from agents.prompts import GRAPHICS_BRAND_KEEPER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("graphics.brand_keeper")


class BrandKeeper:
    name = "graphics.brand_keeper"
    role = "worker"
    SYSTEM_PROMPT = GRAPHICS_BRAND_KEEPER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        user_prompt = (
            f"Art direction:\n{draft}\n\n"
            f"Generated assets to enforce brand consistency on:\n{result}\n\n"
            f"Original request: {request}"
        )
        if critique and revisions > 0:
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n"
            for s in critique.get("suggestions", [critique.get("reason", "")]):
                user_prompt += f"- {s}\n"

        if self._tools:
            ds = self._tools.list_tools(namespace="stitch")
            if ds:
                user_prompt += f"\n\nAvailable design-system tools: {', '.join(ds)}"

        branded = await call_llm(
            task_type="code", system=self.SYSTEM_PROMPT, user=user_prompt
        )
        logger.info("brand_keeper enforced brand consistency, revision=%d", revisions)
        return {"result": branded}
