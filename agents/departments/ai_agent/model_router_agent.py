from agents.prompts import AI_AGENT_MODEL_ROUTER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ai_agent.model_router_agent")


class ModelRouterAgent:
    name = "ai_agent.model_router_agent"
    role = "worker"

    SYSTEM_PROMPT = AI_AGENT_MODEL_ROUTER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        parts = [
            f"Original request: {request}",
            "",
            f"Prompt architecture / plan:\n{draft}",
            "",
            f"Tool definitions produced so far (build on these):\n{result}",
        ]

        if critique and revisions > 0:
            suggestions = critique.get("suggestions", [critique.get("reason", "")])
            parts.append("")
            parts.append(f"Revision {revisions}. Fix these issues:")
            parts += [f"- {s}" for s in suggestions]

        user_prompt = "\n".join(parts)

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("model_router_agent produced routing config, revision=%d", revisions)
        return {"result": result}
