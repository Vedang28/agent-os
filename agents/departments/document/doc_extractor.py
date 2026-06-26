from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import DOCUMENT_EXTRACTOR

logger = get_logger("document.doc_extractor")


class DocExtractor:
    name = "document.doc_extractor"
    role = "proposer"

    SYSTEM_PROMPT = DOCUMENT_EXTRACTOR

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

            for pb in get_playbooks("document", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            context_text = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{context_text}\n\n{user_prompt}"

        draft = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("doc_extractor produced draft for request=%r", request[:80])
        return {"draft": draft, "brain_context": brain_context}
