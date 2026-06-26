import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.devops.architect import CiCdArchitect
from agents.departments.devops.deploy_critic import DeployCritic
from agents.departments.devops.pipeline_builder import PipelineBuilder
from agents.departments.devops.release_manager import ReleaseManager
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("devops.graph")

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
    logger.warning("devops department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_devops_graph(librarian=None, obsidian=None, tool_registry=None):
    architect = CiCdArchitect(librarian=librarian, obsidian=obsidian)
    pipeline_builder = PipelineBuilder(tool_registry=tool_registry)
    release_manager = ReleaseManager(tool_registry=tool_registry)
    deploy_critic = DeployCritic()

    graph = StateGraph(AgentState)
    graph.add_node("architect", _make_node(architect))
    graph.add_node("pipeline_builder", _make_node(pipeline_builder))
    graph.add_node("release_manager", _make_node(release_manager))
    graph.add_node("deploy_critic", _make_node(deploy_critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "architect")
    graph.add_edge("architect", "pipeline_builder")
    graph.add_edge("pipeline_builder", "release_manager")
    graph.add_edge("release_manager", "deploy_critic")
    graph.add_conditional_edges(
        "deploy_critic",
        _route_decision,
        {"end": END, "revise": "pipeline_builder", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)
    return graph.compile()
