from agents.llm import call_llm
from agents.prompts import ML_DATA_CURATOR
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ml.data_curator")


class DataCurator:
    name = "ml.data_curator"
    role = "proposer"

    SYSTEM_PROMPT = ML_DATA_CURATOR

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

            for pb in get_playbooks("ml", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            context_block = "Context from brain:\n" + "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"{context_block}\n\n{user_prompt}"

        draft = await call_llm(
            task_type="code", system=self.SYSTEM_PROMPT, user=user_prompt
        )
        logger.info("data_curator produced data pipeline plan for request=%r", request[:80])
        return {"draft": draft, "brain_context": brain_context}
