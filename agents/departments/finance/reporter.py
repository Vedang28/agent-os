from agents.llm import call_llm
from agents.prompts import FINANCE_REPORTER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("finance.reporter")


class Reporter:
    name = "finance.reporter"
    role = "worker"

    SYSTEM_PROMPT = FINANCE_REPORTER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")
        prior_result = state.get("result", "")

        user_prompt = f"Request: {request}\n\nFinancial summary:\n{draft}"
        if prior_result:
            user_prompt += f"\n\nPrior result:\n{prior_result}"

        if critique and revisions > 0:
            suggestions = critique.get("suggestions", [critique.get("reason", "")])
            bullets = "\n".join(f"- {s}" for s in suggestions)
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n{bullets}"

        result = await call_llm(
            task_type="long_docs",
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
        )

        logger.info("reporter produced report revision=%d", revisions)
        return {"result": result}
