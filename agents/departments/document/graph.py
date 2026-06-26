import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.document.doc_critic import DocCritic
from agents.departments.document.doc_extractor import DocExtractor
from agents.departments.document.doc_ingester import DocIngester
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("document.graph")

MAX_REVISIONS = 3


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
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
    logger.warning("document department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_document_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    doc_extractor = DocExtractor(librarian=librarian, obsidian=obsidian)
    doc_ingester = DocIngester(tool_registry=tool_registry)
    doc_critic = DocCritic()

    graph = StateGraph(AgentState)

    graph.add_node("doc_extractor", _make_node(doc_extractor))
    graph.add_node("doc_ingester", _make_node(doc_ingester))
    graph.add_node("doc_critic", _make_node(doc_critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "doc_extractor")
    graph.add_edge("doc_extractor", "doc_ingester")
    graph.add_edge("doc_ingester", "doc_critic")
    graph.add_conditional_edges(
        "doc_critic",
        _route_decision,
        {"end": END, "revise": "doc_ingester", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
