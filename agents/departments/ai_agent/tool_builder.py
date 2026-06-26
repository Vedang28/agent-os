from agents.prompts import AI_AGENT_TOOL_BUILDER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ai_agent.tool_builder")


class ToolFunctionBuilder:
    name = "ai_agent.tool_builder"
    role = "worker"

    SYSTEM_PROMPT = AI_AGENT_TOOL_BUILDER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        parts = [
            f"Original request: {request}",
            "",
            f"Prompt architecture / plan to implement against:\n{draft}",
        ]

        if self._tools:
            mcp = self._tools.list_tools(namespace="mcp")
            if mcp:
                parts.append("")
                parts.append(f"Discoverable MCP tools available to wrap: {', '.join(mcp)}")

        if critique and revisions > 0:
            suggestions = critique.get("suggestions", [critique.get("reason", "")])
            parts.append("")
            parts.append(f"Revision {revisions}. Fix these issues:")
            parts += [f"- {s}" for s in suggestions]

        user_prompt = "\n".join(parts)

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("tool_builder produced tool schemas, revision=%d", revisions)
        return {"result": result}
