from agents.prompts import SUPPORT_ESCALATION_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("support.escalation_critic")

JARGON_TERMS = ("idempotent", "mutex", "race condition", "stack trace",
                "null pointer", "segfault", "regex", "deadlock", "heap",
                "kubernetes", "kafka", "orm", "tcp handshake")
EMPATHY_MARKERS = ("sorry", "understand", "apologize", "thanks for", "i'll help",
                   "appreciate", "frustrat")


class EscalationCritic:
    name = "support.escalation_critic"
    role = "critic"

    SYSTEM_PROMPT = SUPPORT_ESCALATION_CRITIC

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info(
                "escalation_critic rejected, revisions=%d, reason=%s",
                revisions + 1, issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("escalation_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty"]

        low = result.lower()
        draft_low = draft.lower()

        priority = self._extract_priority(draft_low)
        if priority and priority in ("p0", "p1"):
            if "escalat" not in low and "on-call" not in low and "on call" not in low:
                issues.append(
                    f"Priority {priority.upper()} but no escalation/on-call action in response"
                )
        if priority == "p3" and ("page on-call" in low or "incident channel" in low):
            issues.append("Priority seems wrong: P3 ticket triggering incident escalation")

        if "reproduc" not in low and "steps to reproduce" not in low:
            issues.append("Missing reproduction steps")

        if "troubleshoot" not in low and "checked" not in low and "confirmed" not in low:
            issues.append("Incomplete troubleshooting (obvious diagnostic steps skipped)")

        if "[customer" in low or "{{" in result or "<insert" in low or "[name]" in low:
            issues.append("Copy-paste response not customized (placeholder left in)")

        if not any(m in low for m in EMPATHY_MARKERS):
            issues.append("Missing empathy/acknowledgment of the user's frustration")

        if ("timeline" not in low and "follow up" not in low and "follow-up" not in low
                and "update you" not in low and "check back" not in low):
            issues.append("No follow-up timeline promised")

        jargon_hits = [j for j in JARGON_TERMS if j in low]
        if jargon_hits and "non-technical" in draft_low:
            issues.append(
                f"Too much jargon for a non-technical user: {', '.join(jargon_hits[:3])}"
            )

        if ("doc" not in low and "kb" not in low and "article" not in low
                and "http" not in low):
            issues.append("Missing links to relevant docs/KB")

        if "root cause" not in low and "underlying" not in low:
            issues.append("Root cause not addressed (only the symptom treated)")

        return issues

    def _extract_priority(self, draft_low: str) -> str | None:
        for p in ("p0", "p1", "p2", "p3"):
            if f"priority: {p}" in draft_low:
                return p
        return None
