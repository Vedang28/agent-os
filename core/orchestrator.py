from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("core.orchestrator")

_DEFAULT_DEPARTMENT = "engineering"


def _select_department(request: str) -> str:
    from core.graph import get_department_keywords

    normalized = request.lower()
    for dept, keywords in get_department_keywords().items():
        for kw in keywords:
            if kw in normalized:
                return dept
    return _DEFAULT_DEPARTMENT


def _decompose(request: str) -> list[str]:
    return [f"Execute: {request}"]


def orchestrate(state: AgentState) -> dict:
    request = state.get("request", "")
    department = _select_department(request)
    plan = _decompose(request)

    logger.info(
        "orchestrating: department=%s, plan_steps=%d", department, len(plan)
    )
    return {"department": department, "plan": plan}
