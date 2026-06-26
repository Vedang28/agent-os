from agents.prompts import FINANCE_BOOKKEEPER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("finance.bookkeeper")


class Bookkeeper:
    name = "finance.bookkeeper"
    role = "proposer"

    SYSTEM_PROMPT = FINANCE_BOOKKEEPER

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

            for pb in get_playbooks("finance", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            ctx_lines = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{ctx_lines}\n\n{user_prompt}"

        draft = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"

        logger.info("bookkeeper produced financial summary")
        return {"draft": draft, "brain_context": brain_context}
