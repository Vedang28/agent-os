from agents.llm import call_llm
from agents.prompts import BACKEND_ARCHITECT
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("backend.architect")


class BackendArchitect:
    name = "backend.architect"
    role = "proposer"

    SYSTEM_PROMPT = BACKEND_ARCHITECT

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

            for pb in get_playbooks("backend", self._obsidian):
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
        logger.info("backend architect produced API design for request=%r", request[:80])
        return {"draft": draft, "brain_context": brain_context}

    def _design(self, request: str, context: list[dict]) -> str:
        lines = [f"API DESIGN for: {request}", ""]
        if context:
            lines.append("Reused patterns from brain:")
            lines += [f"- {c['title']}" for c in context]
            lines.append("")

        lines += [
            "Service boundaries:",
            "- ResourceService: owns domain entities and business rules",
            "- AuthMiddleware -> ValidationMiddleware -> Handler -> Serializer",
            "",
            "REST contract (versioned under /api/v1):",
            "- GET    /resources         -> 200 [Resource], paginated",
            "- GET    /resources/{id}    -> 200 Resource | 404",
            "- POST   /resources         -> 201 Resource | 400 | 422",
            "- PATCH  /resources/{id}    -> 200 Resource | 404 | 422",
            "- DELETE /resources/{id}    -> 204 | 404",
            "",
            "Request/response shapes: typed DTOs, no raw dicts cross the boundary.",
            "Middleware chain: auth -> rate-limit -> validation -> handler.",
            "Error handling: central error middleware maps domain errors to status codes.",
            "Data flow: async handlers, repository layer, no blocking I/O on hot paths.",
        ]
        return "\n".join(lines)
