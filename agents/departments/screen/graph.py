import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.screen.frame_critic import FrameCritic
from agents.departments.screen.screen_watcher import ScreenWatcher
from agents.departments.screen.vision_reader import VisionReader
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("screen.graph")

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
    logger.warning("screen department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_screen_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    vision_reader = VisionReader(librarian=librarian, obsidian=obsidian)
    screen_watcher = ScreenWatcher(tool_registry=tool_registry)
    frame_critic = FrameCritic()

    graph = StateGraph(AgentState)

    graph.add_node("vision_reader", _make_node(vision_reader))
    graph.add_node("screen_watcher", _make_node(screen_watcher))
    graph.add_node("frame_critic", _make_node(frame_critic))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "vision_reader")
    graph.add_edge("vision_reader", "screen_watcher")
    graph.add_edge("screen_watcher", "frame_critic")
    graph.add_conditional_edges(
        "frame_critic",
        _route_decision,
        {"end": END, "revise": "screen_watcher", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
