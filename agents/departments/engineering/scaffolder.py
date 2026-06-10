from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("engineering.scaffolder")


class Scaffolder:
    name = "engineering.scaffolder"
    role = "worker"

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        if critique and revisions > 0:
            result = f"Revised implementation (revision {revisions}):\n"
            result += f"Based on: {draft}\n"
            result += f"Addressing feedback: {critique.get('reason', '')}\n"
            result += f"Implementation for: {request}"
        else:
            result = f"Implementation:\n"
            result += f"Based on: {draft}\n"
            result += f"Implementation for: {request}"

        logger.info(
            "scaffolder produced result, revision=%d", revisions
        )
        return {"result": result}
