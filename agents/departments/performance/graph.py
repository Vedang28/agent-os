import asyncio

from langgraph.graph import END, START, StateGraph

from agents.departments.performance.perf_optimizer import PerfOptimizer
from agents.departments.performance.perf_profiler import PerfProfiler
from agents.departments.performance.perf_validator import PerfValidator
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("performance.graph")

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
    logger.warning("performance department escalating after %d revisions", revisions)
    return {
        "result": f"ESCALATION: max revisions ({revisions}) reached. Requires human review.",
        "approved": False,
    }


def build_performance_graph(librarian=None, obsidian=None, tool_registry=None) -> StateGraph:
    perf_profiler = PerfProfiler(librarian=librarian, obsidian=obsidian)
    perf_optimizer = PerfOptimizer(tool_registry=tool_registry)
    perf_validator = PerfValidator()

    graph = StateGraph(AgentState)

    graph.add_node("perf_profiler", _make_node(perf_profiler))
    graph.add_node("perf_optimizer", _make_node(perf_optimizer))
    graph.add_node("perf_validator", _make_node(perf_validator))
    graph.add_node("escalate", _escalate)

    graph.add_edge(START, "perf_profiler")
    graph.add_edge("perf_profiler", "perf_optimizer")
    graph.add_edge("perf_optimizer", "perf_validator")
    graph.add_conditional_edges(
        "perf_validator",
        _route_decision,
        {"end": END, "revise": "perf_optimizer", "escalate": "escalate"},
    )
    graph.add_edge("escalate", END)

    return graph.compile()
