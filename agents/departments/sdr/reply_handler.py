import re

from agents.llm import call_llm
from agents.prompts import SDR_REPLY_HANDLER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("sdr.reply_handler")

GENERIC_PHRASES = (
    "to whom it may concern",
    "dear sir or madam",
    "i hope this email finds you well",
    "i wanted to reach out",
    "we are a leading provider",
    "revolutionary",
    "best-in-class",
    "synergy",
)
PUSHY_PHRASES = (
    "act now", "limited time", "don't miss", "last chance", "buy now",
    "guaranteed", "100%", "you must", "asap", "urgent",
)
COMMON_TYPOS = ("teh ", "recieve", "alot", "definately", "occured", "seperate")


class ReplyHandler:
    name = "sdr.reply_handler"
    role = "critic"

    SYSTEM_PROMPT = SDR_REPLY_HANDLER

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)

        llm_review = await call_llm(
            task_type="long_docs",
            system=self.SYSTEM_PROMPT,
            user=f"Draft/Plan:\n{draft}\n\nOutput to review:\n{result}",
        )
        if "APPROVED" not in llm_review.upper() and llm_review.strip():
            for line in llm_review.strip().split("\n"):
                line = line.strip().lstrip("-•*123456789. ")
                if line and line not in issues:
                    issues.append(line)

        if issues:
            logger.info(
                "reply_handler rejected, revisions=%d, reason=%s",
                revisions + 1, issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("reply_handler approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty"]

        text = result
        low = text.lower()

        for phrase in GENERIC_PHRASES:
            if phrase in low:
                issues.append(
                    f"Generic template language detected: '{phrase}' — personalize it"
                )
                break

        pushy_hits = [p for p in PUSHY_PHRASES if p in low]
        if pushy_hits:
            issues.append(
                f"Too salesy/pushy tone: {', '.join(pushy_hits[:3])}"
            )

        if "{{company}}" not in text and "{{first_name}}" not in text:
            mentions_company = bool(
                re.search(r"\bat [A-Z][\w&-]+", text)
            ) or "company" in low
            if not mentions_company:
                issues.append(
                    "No mention of prospect's specific company or role — add personalization"
                )

        cta_markers = ("call", "chat", "15-min", "15 min", "worth a", "?", "demo", "meet")
        if not any(m in low for m in cta_markers):
            issues.append("Missing clear call-to-action")

        body = self._cold_email_body(text)
        if body and len(body.split()) > 150:
            issues.append(
                f"Cold email too long ({len(body.split())} words > 150)"
            )

        if "unsubscribe" not in low and "opt out" not in low and "opt-out" not in low:
            issues.append("Missing opt-out/unsubscribe option")

        if "follow-up" not in low and "follow up" not in low and "day 4" not in low:
            issues.append("No follow-up cadence defined")

        typo_hits = [t.strip() for t in COMMON_TYPOS if t in low]
        if typo_hits:
            issues.append(f"Spelling/grammar errors detected: {', '.join(typo_hits)}")

        proof_markers = ("case study", "helped", "similar team", "30%", "customers", "results")
        if not any(m in low for m in proof_markers):
            issues.append("No social proof or credibility signal")

        if "subject:" not in low and "subject line" not in low:
            issues.append("Subject line missing or generic")
        else:
            m = re.search(r"subject:\s*([^\n)]+)", low)
            if m and len(m.group(1).strip()) < 6:
                issues.append("Subject line missing or generic")

        return issues

    def _cold_email_body(self, text: str) -> str:
        lines = text.splitlines()
        capturing = False
        body: list[str] = []
        for line in lines:
            if line.strip().startswith("--- COLD EMAIL"):
                capturing = True
                continue
            if capturing and line.strip().startswith("---"):
                break
            if capturing:
                body.append(line)
        return "\n".join(body)
