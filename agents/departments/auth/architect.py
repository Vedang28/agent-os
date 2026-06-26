from agents.llm import call_llm
from agents.prompts import AUTH_ARCHITECT
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("auth.architect")


class AuthArchitect:
    name = "auth.architect"
    role = "proposer"

    SYSTEM_PROMPT = AUTH_ARCHITECT

    def __init__(self, librarian=None, obsidian=None):
        self._librarian = librarian
        self._obsidian = obsidian

    async def run(self, state: AgentState) -> AgentState:
        request = state.get("request", "")
        brain_context: list[dict] = []

        if self._librarian:
            notes = self._librarian.query(request)
            brain_context = [{"title": n.title, "content": n.content} for n in notes]

        if self._obsidian:
            from brain.playbook import get_playbooks

            for pb in get_playbooks("auth", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            context_text = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{context_text}\n\n{user_prompt}"

        draft = await call_llm(
            task_type="code",
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
        )
        logger.info("auth architect produced auth design for request=%r", request[:80])
        return {"draft": draft, "brain_context": brain_context}

    def _design(self, request: str, context: list[dict]) -> str:
        lines = [f"AUTH DESIGN for: {request}", ""]
        if context:
            lines.append("Prior auth patterns from brain:")
            lines += [f"- {c['title']}" for c in context]
            lines.append("")
        lines += [
            "Flow: OAuth2 authorization-code + PKCE; short-lived JWT access tokens.",
            "Token lifecycle: access TTL 15m, refresh TTL 7d, rotate refresh on use.",
            "Key rotation: signing keys rotated via JWKS; kid in header; overlap window.",
            "Session management: server-side refresh store, revocation list, logout-all.",
            "Permission model: RBAC with role hierarchy; ABAC attributes for fine grain.",
            "Storage: refresh tokens hashed at rest; access tokens never persisted.",
            "Transport: HttpOnly + Secure + SameSite cookies; never localStorage.",
            "Protections: CSRF tokens on state-changing routes, MFA optional step-up.",
        ]
        return "\n".join(lines)
