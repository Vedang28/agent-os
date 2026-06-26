import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.dev_testing.test_critic import DevTestCritic
from agents.departments.dev_testing.test_planner import TestPlanner
from agents.departments.dev_testing.test_writer_dev import DevTestWriter
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("dev_testing.graph")

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
    logger.warning("dev_testing department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_dev_testing_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    planner = TestPlanner(librarian=librarian, obsidian=obsidian)
    writer = DevTestWriter(tool_registry=tool_registry)
    critic = DevTestCritic()

    graph = StateGraph(AgentState)
    graph.add_node("test_planner", _make_node(planner))
    graph.add_node("test_writer", _make_node(writer))
    graph.add_node("test_critic", _make_node(critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "test_planner")
    graph.add_edge("test_planner", "test_writer")
    graph.add_edge("test_writer", "test_critic")
    graph.add_conditional_edges(
        "test_critic",
        _route_decision,
        {"end": END, "revise": "test_writer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
