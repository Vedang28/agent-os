from agents.prompts import OBSERVABILITY_TELEMETRY
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("observability.telemetry_engineer")


class TelemetryEngineer:
    name = "observability.telemetry_engineer"
    role = "proposer"

    SYSTEM_PROMPT = OBSERVABILITY_TELEMETRY

    def __init__(self, librarian=None, obsidian=None, tool_registry=None):
        self._librarian = librarian
        self._obsidian = obsidian
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        request = state.get("request", "")
        brain_context: list[dict] = []
        if self._librarian:
            notes = self._librarian.query(request)
            brain_context = [{"title": n.title, "content": n.content} for n in notes]
        if self._obsidian:
            from brain.playbook import get_playbooks
            for pb in get_playbooks("observability", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            context_text = "\n".join(f"- {c['title']}: {c['content'][:200]}" for c in brain_context)
            user_prompt = f"Context from brain:\n{context_text}\n\n{user_prompt}"

        draft = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("produced draft for request=%r", request[:80])
        return {"draft": draft, "brain_context": brain_context}
