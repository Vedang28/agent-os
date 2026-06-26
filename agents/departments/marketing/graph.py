import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.marketing.copywriter import Copywriter
from agents.departments.marketing.marketing_critic import MarketingCritic
from agents.departments.marketing.strategist import MarketingStrategist
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("marketing.graph")

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
    logger.warning("marketing department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_marketing_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    strategist = MarketingStrategist(librarian=librarian, obsidian=obsidian)
    copywriter = Copywriter(tool_registry=tool_registry)
    critic = MarketingCritic()

    graph = StateGraph(AgentState)
    graph.add_node("strategist", _make_node(strategist))
    graph.add_node("copywriter", _make_node(copywriter))
    graph.add_node("critic", _make_node(critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "strategist")
    graph.add_edge("strategist", "copywriter")
    graph.add_edge("copywriter", "critic")
    graph.add_conditional_edges(
        "critic",
        _route_decision,
        {"end": END, "revise": "copywriter", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
