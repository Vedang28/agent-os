from agents.prompts import BACKEND_SCHEMA_DESIGNER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("backend.schema_designer")


class SchemaDesigner:
    name = "backend.schema_designer"
    role = "worker"

    SYSTEM_PROMPT = BACKEND_SCHEMA_DESIGNER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        prior = state.get("result", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)

        user_prompt = (
            f"Existing implementation:\n{prior}\n\nOriginal request: {request}"
        )

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("schema_designer produced schemas, revision=%d", revisions)
        return {"result": result}
