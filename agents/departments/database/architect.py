from agents.prompts import DATABASE_ARCHITECT
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("database.architect")


class DatabaseArchitect:
    name = "database.architect"
    role = "proposer"

    SYSTEM_PROMPT = DATABASE_ARCHITECT

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

            for pb in get_playbooks("database", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            context_text = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{context_text}\n\n{user_prompt}"

        draft = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("database architect produced schema design for request=%r", request[:80])
        return {"draft": draft, "brain_context": brain_context}

    def _design(self, request: str, context: list[dict]) -> str:
        lines = [f"SCHEMA DESIGN for: {request}", ""]
        if context:
            lines.append("Prior schema patterns from brain:")
            lines += [f"- {c['title']}" for c in context]
            lines.append("")
        lines += [
            "Normalization: 3NF; no repeating groups, no derived columns stored.",
            "",
            "Tables:",
            "- users(id PK, email UNIQUE NOT NULL, created_at NOT NULL)",
            "- resources(id PK, owner_id FK->users(id), name NOT NULL, status NOT NULL)",
            "",
            "Relationships: resources.owner_id -> users.id (many-to-one).",
            "Indexing plan: index on resources.owner_id (join column); UNIQUE on users.email.",
            "Constraints: NOT NULL on required fields, CHECK(status IN ...), FK enforced.",
            "Migration plan: additive, reversible, with backfill for existing rows.",
        ]
        return "\n".join(lines)
