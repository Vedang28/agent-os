import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.documentation.doc_detector import DocDetector
from agents.departments.documentation.doc_reviewer import DocReviewer
from agents.departments.documentation.doc_writer import DocWriter
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("documentation.graph")

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
    logger.warning("documentation department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_documentation_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    doc_detector = DocDetector(librarian=librarian, obsidian=obsidian)
    doc_writer = DocWriter(tool_registry=tool_registry)
    doc_reviewer = DocReviewer()

    graph = StateGraph(AgentState)

    graph.add_node("doc_detector", _make_node(doc_detector))
    graph.add_node("doc_writer", _make_node(doc_writer))
    graph.add_node("doc_reviewer", _make_node(doc_reviewer))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "doc_detector")
    graph.add_edge("doc_detector", "doc_writer")
    graph.add_edge("doc_writer", "doc_reviewer")
    graph.add_conditional_edges(
        "doc_reviewer",
        _route_decision,
        {"end": END, "revise": "doc_writer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
