from agents.llm import call_llm
from agents.prompts import MARKETING_STRATEGIST
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("marketing.strategist")


class MarketingStrategist:
    """Proposer: turns a request into a campaign strategy brief.

    Analyzes positioning, audience and channel mix, then drafts a structured
    brief the copywriter turns into content.
    """

    name = "marketing.strategist"
    role = "proposer"

    SYSTEM_PROMPT = MARKETING_STRATEGIST

    def __init__(self, librarian=None, obsidian=None):
        self._librarian = librarian
        self._obsidian = obsidian

    async def run(self, state: AgentState) -> AgentState:
        request = state.get("request", "")
        brain_context: list[dict] = []

        # Read-before-act: past campaign performance + brand guidelines.
        if self._librarian:
            for n in self._librarian.query(request):
                brain_context.append({"title": n.title, "content": n.content})

        if self._obsidian:
            from brain.playbook import get_playbooks

            for pb in get_playbooks("marketing", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            lines = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{lines}\n\n{user_prompt}"

        draft = await call_llm(
            task_type="long_docs",
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
        )
        logger.info(
            "strategist drafted campaign for request=%r with %d brain notes",
            request[:80],
            len(brain_context),
        )
        return {"draft": draft, "brain_context": brain_context}
