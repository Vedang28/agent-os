import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.security_dev.security_analyst import SecurityAnalyst
from agents.departments.security_dev.security_scanner import SecurityScanner
from agents.departments.security_dev.security_skeptic import SecuritySkeptic
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("security_dev.graph")

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
    logger.warning("security_dev department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_security_dev_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    scanner = SecurityScanner(librarian=librarian, obsidian=obsidian)
    analyst = SecurityAnalyst(tool_registry=tool_registry)
    skeptic = SecuritySkeptic()

    graph = StateGraph(AgentState)
    graph.add_node("security_scanner", _make_node(scanner))
    graph.add_node("security_analyst", _make_node(analyst))
    graph.add_node("security_skeptic", _make_node(skeptic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "security_scanner")
    graph.add_edge("security_scanner", "security_analyst")
    graph.add_edge("security_analyst", "security_skeptic")
    graph.add_conditional_edges(
        "security_skeptic",
        _route_decision,
        {"end": END, "revise": "security_analyst", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
