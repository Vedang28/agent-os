import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.seo.content_optimizer import ContentOptimizer
from agents.departments.seo.keyword_scout import KeywordScout
from agents.departments.seo.seo_auditor import SeoAuditor
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("seo.graph")

MAX_REVISIONS = 3


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _make_node(agent_instance):
    def node(state: AgentState) -> dict:
        return _run_async(agent_instance.run(state))

    node.__name__ = agent_instance.name.replace(".", "_")
    return node


def _route_decision(state: AgentState) -> str:
    if state.get("approved"):
        return "end"
    if state.get("revisions", 0) >= MAX_REVISIONS:
        return "escalate"
    return "revise"


def _escalate(state: AgentState) -> dict:
    revisions = state.get("revisions", 0)
    logger.warning("seo department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_seo_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    scout = KeywordScout(librarian=librarian, obsidian=obsidian)
    optimizer = ContentOptimizer(tool_registry=tool_registry)
    auditor = SeoAuditor()

    graph = StateGraph(AgentState)
    graph.add_node("keyword_scout", _make_node(scout))
    graph.add_node("content_optimizer", _make_node(optimizer))
    graph.add_node("auditor", _make_node(auditor))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "keyword_scout")
    graph.add_edge("keyword_scout", "content_optimizer")
    graph.add_edge("content_optimizer", "auditor")
    graph.add_conditional_edges(
        "auditor",
        _route_decision,
        {"end": END, "revise": "content_optimizer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
