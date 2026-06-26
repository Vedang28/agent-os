from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import DEVOPS_DEPLOY_CRITIC

logger = get_logger("devops.deploy_critic")


class DeployCritic:
    name = "devops.deploy_critic"
    role = "critic"

    SYSTEM_PROMPT = DEVOPS_DEPLOY_CRITIC

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info("deploy_critic rejected, revisions=%d, reason=%s", revisions + 1, issues[0])
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("deploy_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty"]

        r = result.lower()

        if not any(k in r for k in ("test:unit", "pytest", "test stage", "unit tests", "build-test")):
            issues.append("No test stage before deployment")
        if not any(k in r for k in ("rollback", "roll back", "auto-rollback")):
            issues.append("Missing rollback mechanism")
        if any(k in r for k in ("password:", "api_key=", "aws_secret", "secret_key=")) and "secrets manager" not in r and "oidc" not in r:
            issues.append("Secrets/credentials hardcoded in pipeline config")
        if "cache" not in r:
            issues.append("No dependency caching (slow builds)")
        if "smoke" not in r:
            issues.append("Missing smoke test after deployment")
        if "staging" not in r:
            issues.append("Deployment to production without a staging gate")
        if not any(k in r for k in ("version", "semver", "tag")):
            issues.append("No build artifact versioning")
        if not any(k in r for k in ("notify", "notification", "slack", "pagerduty")):
            issues.append("Missing failure notifications")
        if "timeout" not in r:
            issues.append("No timeout on build/deploy stages")
        if not any(k in r for k in ("retention", "gc ", "cleanup", "keep last")):
            issues.append("Missing cleanup of old artifacts/images")

        return issues
