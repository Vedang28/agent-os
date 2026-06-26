import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.ui_testing.playwright_operator import PlaywrightOperator
from agents.departments.ui_testing.visual_regression_critic import VisualRegressionCritic
from agents.departments.ui_testing.visual_test_designer import VisualTestDesigner
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ui_testing.graph")

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
    logger.warning("ui_testing department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_ui_testing_graph(librarian=None, obsidian=None, tool_registry=None):
    designer = VisualTestDesigner(librarian=librarian, obsidian=obsidian)
    operator = PlaywrightOperator(tool_registry=tool_registry)
    critic = VisualRegressionCritic()

    graph = StateGraph(AgentState)
    graph.add_node("visual_test_designer", _make_node(designer))
    graph.add_node("playwright_operator", _make_node(operator))
    graph.add_node("visual_regression_critic", _make_node(critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "visual_test_designer")
    graph.add_edge("visual_test_designer", "playwright_operator")
    graph.add_edge("playwright_operator", "visual_regression_critic")
    graph.add_conditional_edges(
        "visual_regression_critic",
        _route_decision,
        {"end": END, "revise": "playwright_operator", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
