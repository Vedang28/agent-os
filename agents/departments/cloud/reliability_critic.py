from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import CLOUD_RELIABILITY_CRITIC

logger = get_logger("cloud.reliability_critic")


class ReliabilityCritic:
    name = "cloud.reliability_critic"
    role = "critic"

    SYSTEM_PROMPT = CLOUD_RELIABILITY_CRITIC

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info("rejected, revisions=%d, reason=%s", revisions + 1, issues[0])
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        if not result or not result.strip():
            return ["Result is empty"]

        r = result.lower()
        issues: list[str] = []

        if not any(k in r for k in ("no spof", "desired_count = 3", "multi_az", "replica", "redundan")):
            issues.append("Single point of failure — no redundancy/multi-AZ")
        if "health_check" not in r and "health check" not in r and "/health" not in r:
            issues.append("Missing health check endpoints")
        if "autoscaling" not in r and "appautoscaling" not in r and "auto-scaling" not in r and "max_capacity" not in r:
            issues.append("No auto-scaling configuration")
        if not any(k in r for k in ("backup", "snapshot", "retention_period")):
            issues.append("Missing backup/snapshot strategy")
        if not any(k in r for k in ("disaster recovery", "rto", "rpo", "cross-region snapshot")):
            issues.append("No disaster recovery plan or RTO/RPO targets")
        if not any(k in r for k in ("cloudwatch_metric_alarm", "monitoring", "alarm", "alerting")):
            issues.append("Missing monitoring and alerting")
        if not any(k in r for k in ("https", "tls", "ssl", "acm", "certificate")):
            issues.append("No SSL/TLS on public endpoints")
        if not any(k in r for k in ("rate-limit", "rate limit", "rate_based", "waf")):
            issues.append("Missing rate limiting")
        if "circuit breaker" not in r and "circuit_breaker" not in r:
            issues.append("No circuit breaker for external dependencies")
        if not any(k in r for k in ("log_group", "logging", "access_logs", "access logs")):
            issues.append("Insufficient logging for debugging")

        return issues
