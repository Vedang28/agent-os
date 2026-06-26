import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.code_review.review_critic import ReviewCritic
from agents.departments.code_review.review_planner import ReviewPlanner
from agents.departments.code_review.reviewer import CodeReviewer
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("code_review.graph")

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
    logger.warning("code_review department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_code_review_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    planner = ReviewPlanner(librarian=librarian, obsidian=obsidian)
    reviewer = CodeReviewer(tool_registry=tool_registry)
    critic = ReviewCritic()

    graph = StateGraph(AgentState)
    graph.add_node("review_planner", _make_node(planner))
    graph.add_node("reviewer", _make_node(reviewer))
    graph.add_node("review_critic", _make_node(critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "review_planner")
    graph.add_edge("review_planner", "reviewer")
    graph.add_edge("reviewer", "review_critic")
    graph.add_conditional_edges(
        "review_critic",
        _route_decision,
        {"end": END, "revise": "reviewer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
