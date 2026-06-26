from agents.llm import call_llm
from agents.prompts import FRONTEND_DESIGN_UI_STYLIST
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("frontend_design.ui_stylist")


class UiStylist:
    name = "frontend_design.ui_stylist"
    role = "worker"
    SYSTEM_PROMPT = FRONTEND_DESIGN_UI_STYLIST

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
            for s in self._fixes_for(critique):
                user_prompt += f"- {s}\n"

        if self._tools:
            tk = self._tools.list_tools(namespace="stitch")
            if tk:
                user_prompt += f"\n\nAvailable design-system tools: {', '.join(tk)}"

        result = await call_llm(
            task_type="code", system=self.SYSTEM_PROMPT, user=user_prompt
        )
        logger.info("ui_stylist produced tokens + theme, revision=%d", revisions)
        return {"result": result}

    def _fixes_for(self, critique: dict) -> list[str]:
        return critique.get("suggestions", [critique.get("reason", "")])
