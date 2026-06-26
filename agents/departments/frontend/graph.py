import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.frontend.architect import FrontendArchitect
from agents.departments.frontend.component_builder import ComponentBuilder
from agents.departments.frontend.reviewer import FrontendReviewer
from agents.departments.frontend.state_wirer import StateWirer
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("frontend.graph")

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
    logger.warning("frontend department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_frontend_graph(librarian=None, obsidian=None, tool_registry=None):
    architect = FrontendArchitect(librarian=librarian, obsidian=obsidian)
    component_builder = ComponentBuilder(tool_registry=tool_registry)
    state_wirer = StateWirer(tool_registry=tool_registry)
    reviewer = FrontendReviewer()

    graph = StateGraph(AgentState)

    graph.add_node("architect", _make_node(architect))
    graph.add_node("component_builder", _make_node(component_builder))
    graph.add_node("state_wirer", _make_node(state_wirer))
    graph.add_node("reviewer", _make_node(reviewer))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "architect")
    graph.add_edge("architect", "component_builder")
    graph.add_edge("component_builder", "state_wirer")
    graph.add_edge("state_wirer", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        _route_decision,
        {"end": END, "revise": "component_builder", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
