from agents.llm import call_llm
from agents.prompts import SEO_KEYWORD_SCOUT
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("seo.keyword_scout")


class KeywordScout:
    """Proposer: researches keyword clusters and content opportunities.

    Analyzes search intent, difficulty and content gaps, reading brain for
    the existing content inventory and past keyword performance. Drafts
    keyword clusters and content briefs for the optimizer.
    """

    name = "seo.keyword_scout"
    role = "proposer"

    SYSTEM_PROMPT = SEO_KEYWORD_SCOUT

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

            for pb in get_playbooks("seo", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            context_lines = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{context_lines}\n\n{user_prompt}"

        draft = await call_llm(
            task_type="long_docs",
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
        )
        logger.info(
            "keyword_scout drafted plan for request=%r", request[:60]
        )
        return {"draft": draft, "brain_context": brain_context}
