from agents.llm import call_llm
from agents.prompts import DATABASE_QUERY_WRITER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("database.query_writer")


class QueryWriter:
    name = "database.query_writer"
    role = "worker"

    SYSTEM_PROMPT = DATABASE_QUERY_WRITER

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
            for s in critique.get("suggestions", [critique.get("reason", "")]):
                user_prompt += f"- {s}\n"

        result = await call_llm(
            task_type="code",
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
        )
        logger.info("query_writer produced queries, revision=%d", revisions)
        return {"result": result}
