from agents.llm import call_llm
from agents.prompts import CODE_REVIEW_PLANNER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("code_review.review_planner")

_RISK_KEYWORDS = {
    "auth": ["auth", "login", "password", "token", "session", "jwt", "oauth"],
    "data": ["migration", "schema", "drop", "delete", "alter table", "truncate"],
    "security": ["eval", "exec", "subprocess", "pickle", "deserialize", "secret"],
    "concurrency": ["thread", "async", "lock", "mutex", "race", "atomic"],
    "api_contract": ["endpoint", "route", "api", "public", "interface", "signature"],
}


class ReviewPlanner:
    """Proposer: plans the code-review strategy for a changeset.

    Reads the diff/request, classifies risk areas, and drafts a review
    checklist so the reviewer focuses on what matters instead of nits.
    """

    name = "code_review.review_planner"
    role = "proposer"
    SYSTEM_PROMPT = CODE_REVIEW_PLANNER

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

            for pb in get_playbooks("code_review", self._obsidian):
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
        logger.info(
            "review_planner drafted plan for request=%r", request[:80]
        )
        return {"draft": draft, "brain_context": brain_context}

    def _detect_risk_areas(self, request: str) -> list[str]:
        low = request.lower()
        hits = []
        for area, keywords in _RISK_KEYWORDS.items():
            if any(kw in low for kw in keywords):
                hits.append(area)
        return hits or ["general"]

    def _infer_focus_files(self, request: str) -> list[str]:
        tokens = [
            t.strip(",.()[]")
            for t in request.split()
            if "." in t and "/" in t or t.endswith((".py", ".ts", ".tsx", ".js", ".go"))
        ]
        return tokens[:10]

    def _recall_past_issues(self, brain_context: list[dict]) -> list[str]:
        patterns = []
        for ctx in brain_context:
            content = ctx.get("content", "").lower()
            if "bug" in content or "regression" in content or "incident" in content:
                patterns.append(ctx.get("title", "recurring issue"))
        return patterns[:5]
