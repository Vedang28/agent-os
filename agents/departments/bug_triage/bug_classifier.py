from core.state import AgentState
from infra.telemetry import get_logger
from agents.llm import call_llm
from agents.prompts import BUG_TRIAGE_CLASSIFIER

logger = get_logger("bug_triage.bug_classifier")


class BugClassifier:
    """Proposer: triages and classifies an incoming bug report.

    Assigns severity (P0-P3) and category, names the likely affected
    component, and drafts a root-cause hypothesis with an investigation
    path for the reproducer to follow.
    """

    name = "bug_triage.bug_classifier"
    role = "proposer"

    SYSTEM_PROMPT = BUG_TRIAGE_CLASSIFIER

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

            for pb in get_playbooks("bug_triage", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            context_text = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{context_text}\n\n{user_prompt}"

        draft = await call_llm(
            task_type="code", system=self.SYSTEM_PROMPT, user=user_prompt
        )
        logger.info("bug_classifier produced draft for request=%r", request[:80])
        return {"draft": draft, "brain_context": brain_context}
