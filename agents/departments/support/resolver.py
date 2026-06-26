from agents.llm import call_llm
from agents.prompts import SUPPORT_RESOLVER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("support.resolver")


class Resolver:
    name = "support.resolver"
    role = "worker"

    SYSTEM_PROMPT = SUPPORT_RESOLVER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")
        prior_result = state.get("result", "")

        user_prompt = f"Request: {request}\n\nTriage assessment:\n{draft}"
        if prior_result:
            user_prompt += f"\n\nPrior result:\n{prior_result}"

        if critique and revisions > 0:
            suggestions = critique.get("suggestions", [critique.get("reason", "")])
            bullets = "\n".join(f"- {s}" for s in suggestions)
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n{bullets}"

        result = await call_llm(
            task_type="long_docs",
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
        )

        logger.info("resolver produced response revision=%d", revisions)
        return {"result": result}
