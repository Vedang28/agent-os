import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.api_gateway.architect import GatewayArchitect
from agents.departments.api_gateway.cache_strategist import CacheStrategist
from agents.departments.api_gateway.load_critic import LoadCritic
from agents.departments.api_gateway.rate_limiter import RateLimitEngineer
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("api_gateway.graph")

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
    logger.warning("api_gateway department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_api_gateway_graph(librarian=None, obsidian=None, tool_registry=None):
    architect = GatewayArchitect(librarian=librarian, obsidian=obsidian)
    rate_limiter = RateLimitEngineer(tool_registry=tool_registry)
    cache_strategist = CacheStrategist(tool_registry=tool_registry)
    load_critic = LoadCritic()

    graph = StateGraph(AgentState)
    graph.add_node("architect", _make_node(architect))
    graph.add_node("rate_limiter", _make_node(rate_limiter))
    graph.add_node("cache_strategist", _make_node(cache_strategist))
    graph.add_node("load_critic", _make_node(load_critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "architect")
    graph.add_edge("architect", "rate_limiter")
    graph.add_edge("rate_limiter", "cache_strategist")
    graph.add_edge("cache_strategist", "load_critic")
    graph.add_conditional_edges(
        "load_critic",
        _route_decision,
        {"end": END, "revise": "rate_limiter", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)
    return graph.compile()
