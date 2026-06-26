from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import DEV_TESTING_PLANNER

logger = get_logger("dev_testing.test_planner")


class TestPlanner:
    """Proposer: plans the test strategy for a code change.

    Decides the test pyramid mix, enumerates edge cases per function, and
    plans fixtures and mock boundaries so the writer has a concrete matrix.
    """

    name = "dev_testing.test_planner"
    role = "proposer"

    SYSTEM_PROMPT = DEV_TESTING_PLANNER

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

            for pb in get_playbooks("dev_testing", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            context_text = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{context_text}\n\n{user_prompt}"

        draft = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("test_planner produced draft for request=%r", request[:80])
        return {"draft": draft, "brain_context": brain_context}
