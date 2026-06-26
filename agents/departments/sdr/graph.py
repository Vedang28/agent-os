import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.sdr.message_writer import MessageWriter
from agents.departments.sdr.outreach_planner import OutreachPlanner
from agents.departments.sdr.reply_handler import ReplyHandler
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("sdr.graph")

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
    logger.warning("sdr department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_sdr_graph(librarian=None, obsidian=None, tool_registry=None):
    planner = OutreachPlanner(librarian=librarian, obsidian=obsidian)
    writer = MessageWriter(tool_registry=tool_registry)
    handler = ReplyHandler()

    graph = StateGraph(AgentState)

    graph.add_node("outreach_planner", _make_node(planner))
    graph.add_node("message_writer", _make_node(writer))
    graph.add_node("reply_handler", _make_node(handler))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "outreach_planner")
    graph.add_edge("outreach_planner", "message_writer")
    graph.add_edge("message_writer", "reply_handler")
    graph.add_conditional_edges(
        "reply_handler",
        _route_decision,
        {"end": END, "revise": "message_writer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
