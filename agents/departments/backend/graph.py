import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.backend.api_builder import ApiBuilder
from agents.departments.backend.architect import BackendArchitect
from agents.departments.backend.reviewer import BackendReviewer
from agents.departments.backend.schema_designer import SchemaDesigner
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("backend.graph")

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
    logger.warning("backend department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_backend_graph(librarian=None, obsidian=None, tool_registry=None):
    architect = BackendArchitect(librarian=librarian, obsidian=obsidian)
    api_builder = ApiBuilder(tool_registry=tool_registry)
    schema_designer = SchemaDesigner(tool_registry=tool_registry)
    reviewer = BackendReviewer()

    graph = StateGraph(AgentState)
    graph.add_node("architect", _make_node(architect))
    graph.add_node("api_builder", _make_node(api_builder))
    graph.add_node("schema_designer", _make_node(schema_designer))
    graph.add_node("reviewer", _make_node(reviewer))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "architect")
    graph.add_edge("architect", "api_builder")
    graph.add_edge("api_builder", "schema_designer")
    graph.add_edge("schema_designer", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        _route_decision,
        {"end": END, "revise": "api_builder", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)
    return graph.compile()
