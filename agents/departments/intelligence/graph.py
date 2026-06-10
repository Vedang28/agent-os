import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.intelligence.analyst import Analyst
from agents.departments.intelligence.scout import Scout
from agents.departments.intelligence.skeptic import Skeptic
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("intelligence.graph")

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
    logger.warning(
        "intelligence department escalating after %d revisions", revisions
    )
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_intelligence_graph(librarian=None, obsidian=None) -> StateGraph:
    scout = Scout(librarian=librarian)
    analyst = Analyst(obsidian=obsidian)
    skeptic = Skeptic()

    graph = StateGraph(AgentState)

    graph.add_node("scout", _make_node(scout))
    graph.add_node("analyst", _make_node(analyst))
    graph.add_node("skeptic", _make_node(skeptic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "scout")
    graph.add_edge("scout", "analyst")
    graph.add_edge("analyst", "skeptic")
    graph.add_conditional_edges(
        "skeptic",
        _route_decision,
        {"end": END, "revise": "analyst", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
