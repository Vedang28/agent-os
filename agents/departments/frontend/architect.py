from agents.prompts import FRONTEND_ARCHITECT
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("frontend.architect")


class FrontendArchitect:
    name = "frontend.architect"
    role = "proposer"
    SYSTEM_PROMPT = FRONTEND_ARCHITECT

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

            for pb in get_playbooks("frontend", self._obsidian):
                brain_context.append({"title": pb.title, "content": pb.content})

        user_prompt = f"Request: {request}"
        if brain_context:
            context_text = "\n".join(
                f"- {c['title']}: {c['content'][:200]}" for c in brain_context
            )
            user_prompt = f"Context from brain:\n{context_text}\n\n{user_prompt}"

        draft = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info(
            "frontend architect produced component design for request=%r",
            request[:80],
        )
        return {"draft": draft, "brain_context": brain_context}

    def _design(self, request: str, context: list[dict]) -> str:
        lines = [f"FRONTEND ARCHITECTURE for: {request}", ""]
        if context:
            lines.append("Reused patterns from brain:")
            lines += [f"- {c['title']}" for c in context]
            lines.append("")

        lines += [
            "Framework: Next.js (App Router) + React + TypeScript",
            "",
            "Component hierarchy:",
            "- <AppShell>",
            "    - <Header nav>           (server component)",
            "    - <PageLayout>",
            "        - <FeatureView>      (client island)",
            "            - <List> -> <ListItem>",
            "            - <DetailPanel>",
            "        - <Sidebar filters>",
            "    - <Footer>",
            "",
            "Page structure (App Router):",
            "- app/layout.tsx       -> root layout, providers, metadata",
            "- app/page.tsx         -> landing / index route",
            "- app/[resource]/page.tsx -> dynamic resource route",
            "",
            "State management strategy:",
            "- Server state via React Query (SWR for simple reads)",
            "- Global UI state via Zustand (lightweight, no boilerplate)",
            "- Local form state via react-hook-form; avoid prop drilling >3 levels",
            "",
            "Data fetching patterns:",
            "- React Server Components for initial render (RSC)",
            "- React Query for client mutations + cache invalidation",
            "- Optimistic updates on writes, rollback on error",
            "",
            "API integration points:",
            "- typed client over /api/v1, generated from OpenAPI",
            "- WebSocket channel for live activity stream",
            "",
            "Shared state design: colocate state; lift only when two siblings share it.",
            "Build config: code-split per route, tree-shake icon/util imports.",
        ]
        return "\n".join(lines)
