import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.cloud.architect import CloudArchitect
from agents.departments.cloud.cost_watcher import CostWatcher
from agents.departments.cloud.provisioner import Provisioner
from agents.departments.cloud.reliability_critic import ReliabilityCritic
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("cloud.graph")

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
    logger.warning("cloud department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_cloud_graph(librarian=None, obsidian=None, tool_registry=None):
    architect = CloudArchitect(librarian=librarian, obsidian=obsidian)
    provisioner = Provisioner(tool_registry=tool_registry)
    cost_watcher = CostWatcher(tool_registry=tool_registry)
    reliability_critic = ReliabilityCritic()

    graph = StateGraph(AgentState)
    graph.add_node("architect", _make_node(architect))
    graph.add_node("provisioner", _make_node(provisioner))
    graph.add_node("cost_watcher", _make_node(cost_watcher))
    graph.add_node("reliability_critic", _make_node(reliability_critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "architect")
    graph.add_edge("architect", "provisioner")
    graph.add_edge("provisioner", "cost_watcher")
    graph.add_edge("cost_watcher", "reliability_critic")
    graph.add_conditional_edges(
        "reliability_critic",
        _route_decision,
        {"end": END, "revise": "provisioner", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)
    return graph.compile()
