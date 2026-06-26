import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.auth.access_control import AccessControlBuilder
from agents.departments.auth.architect import AuthArchitect
from agents.departments.auth.auth_critic import AuthCritic
from agents.departments.auth.token_manager import TokenManager
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("auth.graph")

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
    logger.warning("auth department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_auth_graph(librarian=None, obsidian=None, tool_registry=None):
    architect = AuthArchitect(librarian=librarian, obsidian=obsidian)
    token_manager = TokenManager(tool_registry=tool_registry)
    access_control = AccessControlBuilder(tool_registry=tool_registry)
    auth_critic = AuthCritic()

    graph = StateGraph(AgentState)
    graph.add_node("architect", _make_node(architect))
    graph.add_node("token_manager", _make_node(token_manager))
    graph.add_node("access_control", _make_node(access_control))
    graph.add_node("auth_critic", _make_node(auth_critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "architect")
    graph.add_edge("architect", "token_manager")
    graph.add_edge("token_manager", "access_control")
    graph.add_edge("access_control", "auth_critic")
    graph.add_conditional_edges(
        "auth_critic",
        _route_decision,
        {"end": END, "revise": "token_manager", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)
    return graph.compile()
