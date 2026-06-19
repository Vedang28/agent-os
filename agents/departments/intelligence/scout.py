import json

from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("intelligence.scout")

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

    def __init__(self, librarian=None):
        self._librarian = librarian

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

        draft = json.dumps(items, indent=2)

        logger.info(
            "scout produced %d items (filtered %d known)",
            len(items),
            len(_STUB_ITEMS) - len(items),
        )
        return {
            "draft": draft,
            "brain_context": brain_context,
        }
