from agents.prompts import LEAD_GEN_ENRICHER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("lead_gen.enricher")


class Enricher:
    """Worker: enriches seed prospects into qualified-ready lead records.

    Gathers firmographics, tech stack, funding news, decision-makers and
    engagement signals. On revision, deepens research on the leads the
    qualifier flagged.
    """

    name = "lead_gen.enricher"
    role = "worker"

    SYSTEM_PROMPT = LEAD_GEN_ENRICHER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        request = state.get("request", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")
        prior_result = state.get("result", "")

        user_prompt = f"Original request: {request}\n\nProspect plan:\n{draft}"
        if prior_result:
            user_prompt += f"\n\nPrior output:\n{prior_result}"

        if critique and revisions > 0:
            suggestions = critique.get("suggestions", [critique.get("reason", "")])
            bullets = "\n".join(f"- {s}" for s in suggestions)
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n{bullets}"

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info(
            "enricher produced leads, revision=%d, has_critique=%s",
            revisions,
            bool(critique and revisions > 0),
        )
        return {"result": result}
