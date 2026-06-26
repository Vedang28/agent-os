from agents.llm import call_llm
from agents.prompts import AI_AGENT_PROMPT_ENGINEER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ai_agent.prompt_engineer")


class PromptEngineer:
    name = "ai_agent.prompt_engineer"
    role = "proposer"

    SYSTEM_PROMPT = AI_AGENT_PROMPT_ENGINEER

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

            for pb in get_playbooks("ai_agent", self._obsidian):
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
        logger.info("prompt_engineer produced prompt architecture for request=%r", request[:80])
        return {"draft": draft, "brain_context": brain_context}
