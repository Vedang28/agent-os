from agents.prompts import OBSERVABILITY_INCIDENT_RESPONDER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("observability.incident_responder")

_CRITICAL_SIGNALS = ("5xx", "error_rate", "error rate", "latency", "p99", "disk", "oom", "saturation")


class IncidentResponder:
    name = "observability.incident_responder"
    role = "critic"

    SYSTEM_PROMPT = OBSERVABILITY_INCIDENT_RESPONDER

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info("incident_responder rejected, revisions=%d, reason=%s", revisions + 1, issues[0])
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("incident_responder approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        if not result or not result.strip():
            return ["Result is empty"]

        r = result.lower()
        issues: list[str] = []

        present = [s for s in _CRITICAL_SIGNALS if s in r]
        if len(set(present)) < 3:
            issues.append("Missing alerts for critical scenarios (error rate, latency, saturation)")
        if not any(k in r for k in ("severity", "sev1", "sev2", "sev3", "priority")):
            issues.append("Alert fatigue risk — no severity tiering / paging discipline")
        if "runbook" not in r:
            issues.append("Missing runbooks for alerts")
        if "escalation" not in r:
            issues.append("No escalation path defined")
        if not any(k in r for k in ("slo", "sli", "error budget", "error-budget")):
            issues.append("Missing SLO/SLI definitions")
        if not any(k in r for k in ("traceparent", "context propagat", "propagates context", "trace context")):
            issues.append("Gaps in distributed trace context propagation")
        if "correlation_id" not in r and "correlation id" not in r:
            issues.append("No correlation ID in logs")
        if "dashboard" not in r:
            issues.append("Missing dashboards for key business metrics")
        if "retention" not in r:
            issues.append("No log retention policy")

        return issues
