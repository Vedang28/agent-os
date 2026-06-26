from agents.llm import call_llm
from agents.prompts import API_GATEWAY_ARCHITECT
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("api_gateway.architect")


class GatewayArchitect:
    name = "api_gateway.architect"
    role = "proposer"

    SYSTEM_PROMPT = API_GATEWAY_ARCHITECT

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

            for pb in get_playbooks("api_gateway", self._obsidian):
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
        logger.info("gateway architect produced design for request=%r", request[:80])
        return {"draft": draft, "brain_context": brain_context}

    def _design(self, request: str, context: list[dict]) -> str:
        lines = [f"GATEWAY DESIGN for: {request}", ""]
        if context:
            lines.append("Prior gateway patterns from brain:")
            lines += [f"- {c['title']}" for c in context]
            lines.append("")
        lines += [
            "Versioning: URI-prefixed /api/v{n}; deprecation window with Sunset header.",
            "Routing: path-based to upstream services; health-checked targets only.",
            "Rate limiting: per-API-key sliding window; tighter limits on expensive routes.",
            "Circuit breaker: per-upstream, open after error threshold, half-open probe.",
            "Backpressure: bounded queues, 429 with Retry-After when saturated.",
            "Caching: read-through for idempotent GETs; per-route TTL; stampede protection.",
        ]
        return "\n".join(lines)
