import json

from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("intelligence.scout")

SYSTEM_PROMPT = (
    "You are an intelligence scout. Research the topic thoroughly. Query brain "
    "for context, identify key trends, gather data from available sources. "
    "Produce a comprehensive research brief."
)

_STUB_ITEMS = [
    {
        "title": "LangGraph adds native streaming support",
        "source": "GitHub Trending",
        "summary": "LangGraph released v0.3 with built-in streaming for agent nodes, reducing boilerplate for real-time UIs.",
        "url": "https://github.com/langchain-ai/langgraph",
        "relevance": "Directly relevant to our orchestration layer.",
    },
    {
        "title": "Qdrant introduces binary quantization",
        "source": "Hacker News",
        "summary": "Binary quantization reduces memory usage by 32x with minimal recall loss. Good for large-scale deployments.",
        "url": "https://qdrant.tech/blog/binary-quantization",
        "relevance": "Could optimize our brain layer vector storage.",
    },
    {
        "title": "Claude model context protocol (MCP) adoption growing",
        "source": "X/Twitter",
        "summary": "MCP adoption is accelerating with 50+ tool servers now available. Standard for connecting AI to external tools.",
        "url": "https://modelcontextprotocol.io",
        "relevance": "Aligns with our Phase 6 integration plans.",
    },
]


class Scout:
    name = "intelligence.scout"
    role = "proposer"

    def __init__(self, librarian=None, tool_registry=None):
        self._librarian = librarian
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        request = state.get("request", "")
        brain_context: list[dict] = []

        if self._librarian:
            notes = self._librarian.query(request)
            brain_context = [
                {"title": n.title, "content": n.content} for n in notes
            ]

        known_titles = {ctx.get("title", "") for ctx in brain_context}
        items = [
            item
            for item in _STUB_ITEMS
            if item["title"] not in known_titles
        ]

        if self._tools:
            slack_tools = self._tools.list_tools(namespace="composio.slack")
            if slack_tools:
                try:
                    slack_tool = self._tools.get("composio.slack.read")
                    slack_data = await slack_tool.execute(channel="general", limit=5)
                    items.append({
                        "title": "Slack channel activity",
                        "source": "Slack/general",
                        "summary": slack_data[:500],
                        "url": "",
                        "relevance": "Real-time team communication.",
                    })
                except Exception:
                    logger.warning("failed to read slack, continuing without it")

        user_prompt = f"Research request: {request}"
        if brain_context:
            context_text = "\n".join(
                f"- {ctx['title']}: {ctx['content'][:200]}" for ctx in brain_context
            )
            user_prompt = f"Known context from brain:\n{context_text}\n\n{user_prompt}"

        research_brief = f"{SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        items.append({
            "title": f"Research brief: {request[:60]}",
            "source": "intelligence.scout",
            "summary": research_brief[:1000],
            "url": "",
            "relevance": "LLM-synthesized research for the request.",
        })

        draft = json.dumps(items, indent=2)

        logger.info(
            "scout produced %d items (filtered %d known)",
            len(items),
            len(_STUB_ITEMS) - (len(items) - 1),
        )
        return {
            "draft": draft,
            "brain_context": brain_context,
        }
