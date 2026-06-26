from agents.llm import call_llm
from agents.prompts import AUTH_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("auth.auth_critic")

_SECRET_HINTS = ("password =", "secret =", "api_key =", "apikey =", "signing_key = '", 'signing_key = "')


class AuthCritic:
    name = "auth.auth_critic"
    role = "critic"

    SYSTEM_PROMPT = AUTH_CRITIC

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)

        llm_review = await call_llm(
            task_type="code",
            system=self.SYSTEM_PROMPT,
            user=f"Draft/Plan:\n{draft}\n\nImplementation to review:\n{result}",
        )
        if "APPROVED" not in llm_review.upper() and llm_review.strip():
            for line in llm_review.strip().split("\n"):
                line = line.strip().lstrip("-•*123456789. ")
                if line and line not in issues:
                    issues.append(line)

        if issues:
            logger.info("auth_critic rejected, revisions=%d, reason=%s", revisions + 1, issues[0])
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }
        logger.info("auth_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty"]
        low = result.lower()

        if any(h in low for h in _SECRET_HINTS) and "os.environ" not in low and "getenv" not in low:
            issues.append("Hardcoded secret or signing key — load from env/secret store")
        if "localstorage" in low:
            issues.append("Tokens stored in localStorage (XSS risk) — use HttpOnly cookies")
        if "exp" not in low and "ttl" not in low and "expir" not in low:
            issues.append("No token expiry — access tokens must be short-lived")
        if "csrf" not in low:
            issues.append("Missing CSRF protection on state-changing routes")
        if "owner_id" not in low and "default deny" not in low and "403" not in low:
            issues.append("Possible privilege escalation — no ownership/deny check on writes")
        return issues
