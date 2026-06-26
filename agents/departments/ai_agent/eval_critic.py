from agents.prompts import AI_AGENT_EVAL_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ai_agent.eval_critic")


class EvalCritic:
    name = "ai_agent.eval_critic"
    role = "critic"

    SYSTEM_PROMPT = AI_AGENT_EVAL_CRITIC

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info("eval_critic rejected, revisions=%d, reason=%s", revisions + 1, issues[0])
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }
        logger.info("eval_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        if not result or not result.strip():
            return ["AI implementation result is empty"]

        # The critic judges the whole AI feature: prompt architecture (draft) +
        # tool schemas + routing (result). Both carry security-relevant signal.
        text = (result + "\n" + draft).lower()
        issues: list[str] = []

        injection_safe = any(
            k in text for k in ("sanitiz", "untrusted", "delimit", "never concatenated")
        )
        if not injection_safe:
            issues.append(
                "Prompt-injection risk: user input may be concatenated into the system prompt "
                "without sanitization/delimiting"
            )

        if not any(k in text for k in ("validation", "validate", "parse", "schema")):
            issues.append("Missing output validation / response parsing for model output")

        if not any(k in text for k in ("fallback", "retry")):
            issues.append("No fallback or retry when the model/provider errors or times out")

        if not any(k in text for k in ("token budget", "max_tokens", "token_budget")):
            issues.append("No token budget defined — unbounded token usage")

        if "rate limit" not in text and "rate_limit" not in text:
            issues.append("Missing rate limiting on provider API calls")

        if not any(k in text for k in ("eval", "benchmark", "test case", "golden")):
            issues.append("No evaluation benchmark / eval cases defined")

        if not any(k in text for k in ("content filter", "moderation", "safety")):
            issues.append("Missing content / safety filtering on inputs and outputs")

        if "cost" not in text:
            issues.append("No cost tracking or budget enforcement")

        if "tool" in text and not any(k in text for k in ("parameter", "additionalproperties", "required")):
            issues.append("Tool definitions missing parameter validation")

        grounded = any(k in text for k in ("rag", "retrieval", "grounded", "grounding"))
        if grounded and not any(k in text for k in ("citation", "source")):
            issues.append("Grounded task without source citation mechanism (hallucination risk)")

        return issues
