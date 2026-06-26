from agents.prompts import MARKETING_COPYWRITER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("marketing.copywriter")


class Copywriter:
    """Worker: turns the strategy brief into channel-ready marketing copy.

    Produces email sequences, social posts, blog outline, ad copy and CTAs
    with A/B variants, UTM tracking and CAN-SPAM compliant email footers.
    On revision, applies the critic's suggestions.
    """

    name = "marketing.copywriter"
    role = "worker"

    SYSTEM_PROMPT = MARKETING_COPYWRITER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        request = state.get("request", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")
        prior_result = state.get("result", "")

        user_prompt = (
            f"Original request: {request}\n\nStrategy brief:\n{draft}"
        )
        if prior_result:
            user_prompt += f"\n\nPrior output:\n{prior_result}"

        if critique and revisions > 0:
            suggestions = critique.get("suggestions", [critique.get("reason", "")])
            bullets = "\n".join(f"- {s}" for s in suggestions)
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n{bullets}"

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info(
            "copywriter produced content, revision=%d, has_critique=%s",
            revisions,
            bool(critique and revisions > 0),
        )
        return {"result": result}
