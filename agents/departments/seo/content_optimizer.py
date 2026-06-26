from agents.llm import call_llm
from agents.prompts import SEO_CONTENT_OPTIMIZER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("seo.content_optimizer")


class ContentOptimizer:
    """Worker: produces on-page SEO assets from the keyword plan.

    Emits meta tags, heading structure, internal links, JSON-LD schema,
    image alt text, canonical URL and social cards. On revision, applies the
    auditor's fixes.
    """

    name = "seo.content_optimizer"
    role = "worker"

    SYSTEM_PROMPT = SEO_CONTENT_OPTIMIZER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")
        prior = state.get("result", "")

        user_prompt = f"Keyword plan:\n{draft}\n\nRequest: {request}"
        if prior:
            user_prompt += f"\n\nPrevious output:\n{prior}"
        if critique and revisions > 0:
            fixes = critique.get("suggestions", [critique.get("reason", "")])
            fix_lines = "\n".join(f"- {f}" for f in fixes)
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n{fix_lines}"

        result = await call_llm(
            task_type="long_docs",
            system=self.SYSTEM_PROMPT,
            user=user_prompt,
        )
        logger.info(
            "content_optimizer produced page, revision=%d", revisions
        )
        return {"result": result}
