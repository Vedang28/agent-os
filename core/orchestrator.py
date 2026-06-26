"""CEO orchestrator — routes requests to the right department(s).

Analyzes the incoming task, identifies which departments are needed, and
can launch multiple departments in parallel when a task spans domains
(e.g., "add auth to the API" needs both auth + backend).
"""

from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("core.orchestrator")

_DEFAULT_DEPARTMENT = "engineering"


def _score_departments(request: str) -> list[tuple[str, int]]:
    """Score every department against the request. Returns (dept, score) sorted descending."""
    from core.graph import get_department_keywords

    normalized = request.lower()
    scores: list[tuple[str, int]] = []

    for dept, keywords in get_department_keywords().items():
        score = 0
        for kw in keywords:
            if kw in normalized:
                # Longer keyword matches are more specific → higher weight
                score += len(kw.split())
        if score > 0:
            scores.append((dept, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def _select_departments(request: str) -> list[str]:
    """Pick which department(s) to activate.

    Rules:
    - Always returns at least one department
    - Returns multiple when a task clearly spans domains (score > 0 for multiple)
    - Pipeline department gets priority for full-project builds
    - Caps at 4 concurrent departments to avoid sprawl
    """
    scores = _score_departments(request)

    if not scores:
        return [_DEFAULT_DEPARTMENT]

    # If pipeline matched, it handles full-project builds end-to-end
    for dept, score in scores:
        if dept == "pipeline" and score >= 2:
            return ["pipeline"]

    # Single department if only one matched or top score dominates
    if len(scores) == 1:
        return [scores[0][0]]

    top_score = scores[0][1]
    if top_score == 0:
        return [_DEFAULT_DEPARTMENT]

    # Include departments scoring at least 40% of top score (they're relevant)
    threshold = max(1, top_score * 0.4)
    selected = [dept for dept, score in scores if score >= threshold]

    return selected[:4]


def _decompose(request: str, departments: list[str]) -> list[str]:
    """Break the request into sub-tasks per department."""
    if len(departments) == 1:
        return [f"Execute: {request}"]

    return [f"[{dept}] Handle {dept}-related aspects of: {request}" for dept in departments]


def orchestrate(state: AgentState) -> dict:
    """Route the request to the appropriate department(s).

    Sets `department` for single-department tasks (backward compatible).
    Sets `departments` for multi-department parallel execution.
    """
    request = state.get("request", "")
    departments = _select_departments(request)
    plan = _decompose(request, departments)

    # Primary department (first/highest-scoring) for backward compatibility
    primary = departments[0]

    logger.info(
        "orchestrating: departments=%s (primary=%s), plan_steps=%d",
        departments, primary, len(plan),
    )
    return {
        "department": primary,
        "departments": departments,
        "plan": plan,
    }
