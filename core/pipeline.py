"""The 9-stage code pipeline as a LangGraph sub-graph.

    PLAN → SCAFFOLD → BUILD → TEST → DEBUG → REVIEW → AUDIT → PROD-READY → PUSH

Failure routing (bounded, max 3 debug loops then ESCALATE):
  - TEST fails        → DEBUG → BUILD
  - REVIEW fails      → DEBUG → BUILD
  - AUDIT fails       → DEBUG → BUILD
  - PROD-READY fails  → DEBUG → BUILD

The stage logic lives in ``core.pipeline_stages``; this module wires the nodes,
edges, and routing, and binds brain/tool dependencies into the stages.
"""

from __future__ import annotations

import functools

from langgraph.graph import END, START, StateGraph

from core.pipeline_stages import (
    PipelineState,
    audit_stage,
    build_stage,
    debug_stage,
    escalate_stage,
    plan_stage,
    prod_ready_stage,
    push_stage,
    review_stage,
    scaffold_stage,
    test_stage,
)
from infra.telemetry import get_logger

logger = get_logger("core.pipeline")

MAX_DEBUG_LOOPS = 3


# --------------------------------------------------------------------------- #
# Routing
# --------------------------------------------------------------------------- #

def _route(state: PipelineState, on_pass: str) -> str:
    """Shared gate routing: cap debug loops, else pass-through or DEBUG."""
    if state.get("debug_count", 0) >= MAX_DEBUG_LOOPS:
        return "escalate"
    if state.get("approved"):
        return on_pass
    return "debug"


def route_after_test(state: PipelineState) -> str:
    return _route(state, "review")


def route_after_review(state: PipelineState) -> str:
    return _route(state, "audit")


def route_after_audit(state: PipelineState) -> str:
    return _route(state, "prod_ready")


def route_after_prod_ready(state: PipelineState) -> str:
    return _route(state, "push")


def route_after_debug(state: PipelineState) -> str:
    """DEBUG re-runs the build cycle, unless the loop cap is hit."""
    if state.get("debug_count", 0) >= MAX_DEBUG_LOOPS:
        return "escalate"
    return "build"


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #

def build_pipeline_graph(
    stack_info=None,
    librarian=None,
    obsidian=None,
    tool_registry=None,
):
    """Compile the 9-stage pipeline graph.

    ``stack_info`` (a StackInfo or dict) pre-seeds detection so PLAN doesn't
    re-scan the filesystem. ``librarian``/``obsidian`` feed read-before-act in
    PLAN. ``tool_registry`` is threaded through for stages that shell out.
    """
    plan = functools.partial(
        _seed_stack(plan_stage, stack_info),
        librarian=librarian,
        obsidian=obsidian,
        tool_registry=tool_registry,
    )

    graph = StateGraph(PipelineState)

    graph.add_node("plan", plan)
    graph.add_node("scaffold", scaffold_stage)
    graph.add_node("build", build_stage)
    graph.add_node("test", test_stage)
    graph.add_node("debug", debug_stage)
    graph.add_node("review", review_stage)
    graph.add_node("audit", audit_stage)
    graph.add_node("prod_ready", prod_ready_stage)
    graph.add_node("push", push_stage)
    graph.add_node("escalate", escalate_stage)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "scaffold")
    graph.add_edge("scaffold", "build")
    graph.add_edge("build", "test")

    graph.add_conditional_edges(
        "test",
        route_after_test,
        {"review": "review", "debug": "debug", "escalate": "escalate"},
    )
    graph.add_conditional_edges(
        "debug",
        route_after_debug,
        {"build": "build", "escalate": "escalate"},
    )
    graph.add_conditional_edges(
        "review",
        route_after_review,
        {"audit": "audit", "debug": "debug", "escalate": "escalate"},
    )
    graph.add_conditional_edges(
        "audit",
        route_after_audit,
        {"prod_ready": "prod_ready", "debug": "debug", "escalate": "escalate"},
    )
    graph.add_conditional_edges(
        "prod_ready",
        route_after_prod_ready,
        {"push": "push", "debug": "debug", "escalate": "escalate"},
    )

    graph.add_edge("push", END)
    graph.add_edge("escalate", END)

    return graph.compile()


def _seed_stack(fn, stack_info):
    """Wrap PLAN so a caller-provided stack_info lands in state before PLAN runs."""
    if stack_info is None:
        return fn

    from dataclasses import asdict, is_dataclass

    seed = asdict(stack_info) if is_dataclass(stack_info) else dict(stack_info)

    @functools.wraps(fn)
    def wrapper(state: PipelineState, **kwargs):
        if not state.get("stack_info"):
            state = {**state, "stack_info": seed}
        return fn(state, **kwargs)

    return wrapper
