from agents.llm import call_llm
from agents.prompts import SECURITY_DEV_ANALYST
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("security_dev.security_analyst")


class SecurityAnalyst:
    """Worker: performs the security analysis from the threat model.

    Produces findings with severity, a PoC, and a concrete fix for each
    applicable OWASP category. On revision, investigates deeper on the
    areas the skeptic flagged.
    """

    name = "security_dev.security_analyst"
    role = "worker"

    SYSTEM_PROMPT = SECURITY_DEV_ANALYST

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
            task_type="code", system=self.SYSTEM_PROMPT, user=user_prompt
        )
        logger.info("produced result, revision=%d", revisions)
        return {"result": result}
