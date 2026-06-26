from agents.llm import call_llm
from agents.prompts import DATABASE_MIGRATION_RUNNER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("database.migration_runner")


class MigrationRunner:
    name = "database.migration_runner"
    role = "worker"

    SYSTEM_PROMPT = DATABASE_MIGRATION_RUNNER

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
        logger.info("migration_runner produced migration, revision=%d", revisions)
        return {"result": result}
