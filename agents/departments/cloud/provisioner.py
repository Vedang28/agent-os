from core.state import AgentState
from infra.telemetry import get_logger
from agents.llm import call_llm
from agents.prompts import CLOUD_PROVISIONER

logger = get_logger("cloud.provisioner")


class Provisioner:
    name = "cloud.provisioner"
    role = "worker"

    SYSTEM_PROMPT = CLOUD_PROVISIONER

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

        result = await call_llm(task_type="code", system=self.SYSTEM_PROMPT, user=user_prompt)

        if self._tools:
            avail = self._tools.list_tools()
            if avail:
                result += f"\n# Tooling available for apply/plan automation: {len(avail)} registered tools\n"

        logger.info("produced result, revision=%d", revisions)
        return {"result": result}
