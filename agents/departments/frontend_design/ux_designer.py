from agents.llm import call_llm
from agents.prompts import FRONTEND_DESIGN_UX
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("frontend_design.ux_designer")


class UxDesigner:
    name = "frontend_design.ux_designer"
    role = "proposer"
    SYSTEM_PROMPT = FRONTEND_DESIGN_UX

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

            for pb in get_playbooks("frontend_design", self._obsidian):
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
            "ux_designer produced flows + wireframes for request=%r", request[:80]
        )
        return {"draft": draft, "brain_context": brain_context}

    def _design(self, request: str, context: list[dict]) -> str:
        lines = [f"UX DESIGN for: {request}", ""]
        if context:
            lines.append("Reused patterns from brain:")
            lines += [f"- {c['title']}" for c in context]
            lines.append("")

        lines += [
            "Information architecture:",
            "- Home -> Browse -> Detail -> Action (3-click max to primary task)",
            "- Persistent left nav for top-level sections; breadcrumbs for depth",
            "",
            "Primary user flow (happy path):",
            "1. Land on dashboard -> sees most-recent items first",
            "2. Search/filter narrows the list -> results update live",
            "3. Select an item -> detail panel slides in (no full reload)",
            "4. Take action -> inline confirmation -> list reflects the change",
            "",
            "Wireframe (text):",
            "+----------------------------------------------+",
            "| Header: logo | search........... | account   |",
            "+--------+-------------------------------------+",
            "| Nav    | Toolbar: filters | sort | new       |",
            "|  Home  |-------------------------------------|",
            "|  Items | [card][card][card]                  |",
            "|  Stats | [card][card][card]                  |",
            "+--------+-------------------------------------+",
            "",
            "Navigation pattern: primary nav (sidebar) + contextual tabs in detail.",
            "Interaction model: progressive disclosure; destructive actions confirmed.",
            "User journey map: discover -> evaluate -> act -> confirm -> repeat.",
            "Empty/edge states defined for: no results, first-run, permission-denied.",
        ]
        return "\n".join(lines)
