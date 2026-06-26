from agents.llm import call_llm
from agents.prompts import ML_EMBEDDING_ENGINEER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ml.embedding_engineer")


class EmbeddingEngineer:
    name = "ml.embedding_engineer"
    role = "worker"

    SYSTEM_PROMPT = ML_EMBEDDING_ENGINEER

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
            f"Data pipeline plan to implement against:\n{draft}",
        ]

        if self._tools:
            mcp = self._tools.list_tools(namespace="mcp")
            if mcp:
                parts.append("")
                parts.append(f"Available vector/MCP tools: {', '.join(mcp)}")

        if critique and revisions > 0:
            suggestions = critique.get("suggestions", [critique.get("reason", "")])
            parts.append("")
            parts.append(f"Revision {revisions}. Fix these issues:")
            parts += [f"- {s}" for s in suggestions]

        user_prompt = "\n".join(parts)

        result = await call_llm(
            task_type="code", system=self.SYSTEM_PROMPT, user=user_prompt
        )
        logger.info("embedding_engineer produced embedding pipeline, revision=%d", revisions)
        return {"result": result}
