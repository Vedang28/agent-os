import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.devops_ci.ci_fixer import CiFixer
from agents.departments.devops_ci.ci_monitor import CiMonitor
from agents.departments.devops_ci.ci_validator import CiValidator
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("devops_ci.graph")

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
    logger.warning("devops_ci department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_devops_ci_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    ci_monitor = CiMonitor(librarian=librarian, obsidian=obsidian)
    ci_fixer = CiFixer(tool_registry=tool_registry)
    ci_validator = CiValidator()

    graph = StateGraph(AgentState)

    graph.add_node("ci_monitor", _make_node(ci_monitor))
    graph.add_node("ci_fixer", _make_node(ci_fixer))
    graph.add_node("ci_validator", _make_node(ci_validator))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "ci_monitor")
    graph.add_edge("ci_monitor", "ci_fixer")
    graph.add_edge("ci_fixer", "ci_validator")
    graph.add_conditional_edges(
        "ci_validator",
        _route_decision,
        {"end": END, "revise": "ci_fixer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
