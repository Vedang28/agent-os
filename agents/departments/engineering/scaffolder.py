from agents.prompts import ENGINEERING_SCAFFOLDER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("engineering.scaffolder")


class Scaffolder:
    SYSTEM_PROMPT = ENGINEERING_SCAFFOLDER
    name = "engineering.scaffolder"
    role = "worker"

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        integration_context = ""
        if self._tools:
            github_tools = self._tools.list_tools(namespace="composio.github")
            if github_tools:
                integration_context = f"\nAvailable GitHub tools: {', '.join(github_tools)}"

        user_prompt = f"Request: {request}\n\nArchitect's plan:\n{draft}"
        if critique and revisions > 0:
            user_prompt += (
                f"\n\nThis is revision {revisions}. Address this critique:\n"
                f"{critique.get('reason', '')}"
            )
        if integration_context:
            user_prompt += integration_context

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"

        logger.info(
            "scaffolder produced result, revision=%d", revisions
        )
        return {"result": result}
