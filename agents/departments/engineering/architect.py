from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("engineering.architect")


class Architect:
    name = "engineering.architect"
    role = "proposer"

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

            playbooks = get_playbooks("engineering", self._obsidian)
            for pb in playbooks:
                brain_context.append({"title": pb.title, "content": pb.content})

        draft = f"Plan for: {request}\n"
        if brain_context:
            draft += "Context:\n"
            for ctx in brain_context:
                draft += f"- {ctx['title']}\n"
        draft += "Steps:\n"
        draft += "1. Analyze requirements\n"
        draft += "2. Design solution architecture\n"
        draft += "3. Implement core logic\n"
        draft += "4. Write tests\n"
        draft += "5. Review and refine"

        logger.info("architect produced draft for request=%r", request[:80])
        return {
            "draft": draft,
            "brain_context": brain_context,
        }
