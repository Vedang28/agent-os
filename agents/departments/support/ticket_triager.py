from agents.llm import call_llm
from agents.prompts import SUPPORT_TICKET_TRIAGER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("support.ticket_triager")


class TicketTriager:
    name = "support.ticket_triager"
    role = "proposer"

    SYSTEM_PROMPT = SUPPORT_TICKET_TRIAGER

    def __init__(self, librarian=None, obsidian=None):
        self._librarian = librarian
        self._obsidian = obsidian

    async def run(self, state: AgentState) -> AgentState:
        request = state.get("request", "")
        brain_context: list[dict] = []

        if self._librarian:
            notes = self._librarian.query(request)
            brain_context = [
                {"title": n.title, "content": n.content} for n in notes
            ]

        if self._obsidian:
            from brain.playbook import get_playbooks

            for pb in get_playbooks("support", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            ctx_lines = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{ctx_lines}\n\n{user_prompt}"

        draft = await call_llm(
            task_type="long_docs",
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
        )

        logger.info("ticket_triager produced triage assessment")
        return {"draft": draft, "brain_context": brain_context}
