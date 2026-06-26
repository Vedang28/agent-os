from agents.prompts import LEAD_GEN_PROSPECTOR
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("lead_gen.prospector")


class Prospector:
    """Proposer: defines the ICP, scoring model and outreach plan.

    Reads brain for past lead-quality and conversion patterns, then drafts
    a prospect spec the enricher fills in.
    """

    name = "lead_gen.prospector"
    role = "proposer"

    SYSTEM_PROMPT = LEAD_GEN_PROSPECTOR

    def __init__(self, librarian=None, obsidian=None):
        self._librarian = librarian
        self._obsidian = obsidian

    async def run(self, state: AgentState) -> AgentState:
        request = state.get("request", "")
        brain_context: list[dict] = []

        if self._librarian:
            for n in self._librarian.query(request):
                brain_context.append({"title": n.title, "content": n.content})

        if self._obsidian:
            from brain.playbook import get_playbooks

            for pb in get_playbooks("lead_gen", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            lines = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{lines}\n\n{user_prompt}"

        draft = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info(
            "prospector drafted ICP plan for request=%r with %d brain notes",
            request[:80],
            len(brain_context),
        )
        return {"draft": draft, "brain_context": brain_context}
