from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import MEMORY_SESSION_SCRIBE

logger = get_logger("memory.session_scribe")


class SessionScribe:
    """Proposer+worker hybrid: logs what a work session accomplished.

    The draft IS the deliverable, so it sets both ``draft`` and ``result``.
    """

    name = "memory.session_scribe"
    role = "proposer"

    SYSTEM_PROMPT = MEMORY_SESSION_SCRIBE

    def __init__(self, librarian=None, obsidian=None):
        self._librarian = librarian
        self._obsidian = obsidian

    async def run(self, state: AgentState) -> AgentState:
        request = state.get("request", "")
        brain_context: list[dict] = []

        # Read-before-act: pull session-log format and past entries from the brain.
        if self._librarian:
            for note in self._librarian.query(request):
                brain_context.append({"title": note.title, "content": note.content})

        if self._obsidian:
            from brain.playbook import get_playbooks

            for pb in get_playbooks("memory", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            context_text = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{context_text}\n\n{user_prompt}"

        response = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("session_scribe produced output for request=%r", request[:80])
        return {"draft": response, "result": response, "brain_context": brain_context}
