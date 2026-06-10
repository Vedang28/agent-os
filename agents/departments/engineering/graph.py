import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.engineering.architect import Architect
from agents.departments.engineering.code_doctor import CodeDoctor
from agents.departments.engineering.scaffolder import Scaffolder
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("engineering.graph")

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
    logger.warning(
        "engineering department escalating after %d revisions", revisions
    )
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_engineering_graph(librarian=None) -> StateGraph:
    architect = Architect(librarian=librarian)
    scaffolder = Scaffolder()
    code_doctor = CodeDoctor()

    graph = StateGraph(AgentState)

    graph.add_node("architect", _make_node(architect))
    graph.add_node("scaffolder", _make_node(scaffolder))
    graph.add_node("code_doctor", _make_node(code_doctor))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "architect")
    graph.add_edge("architect", "scaffolder")
    graph.add_edge("scaffolder", "code_doctor")
    graph.add_conditional_edges(
        "code_doctor",
        _route_decision,
        {"end": END, "revise": "scaffolder", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
