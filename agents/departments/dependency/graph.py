import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.dependency.dep_scanner import DepScanner
from agents.departments.dependency.dep_upgrader import DepUpgrader
from agents.departments.dependency.dep_validator import DepValidator
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("dependency.graph")

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
    logger.warning("dependency department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_dependency_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    scanner = DepScanner(librarian=librarian, obsidian=obsidian)
    upgrader = DepUpgrader(tool_registry=tool_registry)
    validator = DepValidator()

    graph = StateGraph(AgentState)
    graph.add_node("dep_scanner", _make_node(scanner))
    graph.add_node("dep_upgrader", _make_node(upgrader))
    graph.add_node("dep_validator", _make_node(validator))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "dep_scanner")
    graph.add_edge("dep_scanner", "dep_upgrader")
    graph.add_edge("dep_upgrader", "dep_validator")
    graph.add_conditional_edges(
        "dep_validator",
        _route_decision,
        {"end": END, "revise": "dep_upgrader", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
