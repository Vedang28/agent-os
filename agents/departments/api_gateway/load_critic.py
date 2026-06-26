from agents.llm import call_llm
from agents.prompts import API_GATEWAY_LOAD_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("api_gateway.load_critic")


class LoadCritic:
    name = "api_gateway.load_critic"
    role = "critic"

    SYSTEM_PROMPT = API_GATEWAY_LOAD_CRITIC

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
            logger.info("load_critic rejected, revisions=%d, reason=%s", revisions + 1, issues[0])
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }
        logger.info("load_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty"]
        low = result.lower()

        if "limit" not in low and "rate" not in low:
            issues.append("Missing rate limits on expensive endpoints")
        if "single_flight" not in low and "stampede" not in low and "single-flight" not in low:
            issues.append("No cache stampede / thundering-herd protection")
        if "tenant" not in low and "namespace" not in low and "v1:" not in low:
            issues.append("Cache keys may collide — namespace/scope them")
        if "backpressure" not in low and "429" not in low and "retry_after" not in low:
            issues.append("No backpressure mechanism when saturated")
        if "jitter" not in low and "ttl" in low and "expir" in low:
            issues.append("Synchronized TTLs risk thundering herd on expiry — add jitter")
        return issues
