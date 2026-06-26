from agents.llm import call_llm
from agents.prompts import GRAPHICS_ART_DIRECTOR
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("graphics.art_director")


class ArtDirector:
    name = "graphics.art_director"
    role = "proposer"
    SYSTEM_PROMPT = GRAPHICS_ART_DIRECTOR

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

            for pb in get_playbooks("graphics", self._obsidian):
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
            "art_director set visual direction for request=%r", request[:80]
        )
        return {"draft": draft, "brain_context": brain_context}

    def _direct(self, request: str, context: list[dict]) -> str:
        lines = [f"ART DIRECTION for: {request}", ""]
        if context:
            lines.append("Reused patterns from brain:")
            lines += [f"- {c['title']}" for c in context]
            lines.append("")

        lines += [
            "Visual direction: clean, confident, utilitarian; content-first.",
            "",
            "Mood board (described):",
            "- Geometric sans type paired with generous whitespace",
            "- Cool neutral base with a single saturated accent",
            "- Soft elevation (low-blur shadows) over hard borders",
            "- Photography: candid, natural light; illustrations: flat, 2-tone",
            "",
            "Composition guidelines:",
            "- 12-column grid, 8pt baseline rhythm",
            "- Clear focal point per view; avoid competing visual weights",
            "- Z-pattern scan for landing, F-pattern for dense lists",
            "",
            "Illustration style guide:",
            "- Flat vector, 2px stroke, rounded joins, no gradients in icons",
            "- Limited palette drawn from brand tokens only",
            "",
            "Asset requirements:",
            "- icon set (line, 24px grid)",
            "- favicon set (multiple sizes)",
            "- OG/social share image template",
            "- empty-state and error illustrations",
            "",
            "Brand rules: accent reserved for primary actions; never tint body text.",
            "Accessibility intent: all visuals colorblind-safe, never color-only meaning.",
        ]
        return "\n".join(lines)
