import re

from agents.prompts import FINANCE_COMPLIANCE_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("finance.compliance_critic")

CURRENCY_MARKERS = ("usd", "eur", "gbp", "currency:", "$", "€", "£")
PII_PATTERNS = (
    r"\b\d{3}-\d{2}-\d{4}\b",                       # SSN
    r"\b(?:\d[ -]*?){13,16}\b",                     # card number
    r"(?i)\bacc(?:oun)?t\.?\s*#?\s*\d{6,}\b",       # account number
)


class ComplianceCritic:
    name = "finance.compliance_critic"
    role = "critic"

    SYSTEM_PROMPT = FINANCE_COMPLIANCE_CRITIC

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info(
                "compliance_critic rejected, revisions=%d, reason=%s",
                revisions + 1, issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("compliance_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty"]

        low = result.lower()

        if "source" not in low and "ledger" not in low and "citation" not in low:
            issues.append("Financial figures without source citation")

        has_numbers = bool(re.search(r"\d", result))
        if has_numbers and "=" not in result and "formula" not in low:
            issues.append("Calculations without visible formula")

        if not any(m in low for m in CURRENCY_MARKERS):
            issues.append("Missing currency specification")

        if ("project" in low or "forecast" in low or "estimate" in low) \
                and "assumption" not in low:
            issues.append("Projections without stated assumptions")

        if "risk" not in low and "disclos" not in low:
            issues.append("Missing risk disclosures")

        for pat in PII_PATTERNS:
            if re.search(pat, result):
                issues.append("PII or sensitive financial data exposed — redact it")
                break

        if "audit trail" not in low and "traceab" not in low:
            issues.append("Missing audit trail for figures/changes")

        if ("non-standard" in low or "custom treatment" in low) \
                and "justif" not in low:
            issues.append("Non-standard accounting treatment without justification")
        if "gaap" not in low and "ifrs" not in low and "accrual" not in low \
                and "cash basis" not in low:
            issues.append("Missing regulatory/accounting compliance notes (GAAP/IFRS)")

        if "disclaimer" not in low:
            issues.append("Missing regulatory disclaimer")

        if not self._has_period(result):
            issues.append("Report period not clearly stated")

        return issues

    def _has_period(self, result: str) -> bool:
        low = result.lower()
        if "report period:" in low:
            field = low.split("report period:", 1)[1].splitlines()[0]
            if "[specify" in field or "[" in field:
                return False
        if re.search(r"q[1-4]\s*\d{4}", low):
            return True
        if re.search(r"(fy|h[12])\s*\d{4}", low):
            return True
        months = ("january", "february", "march", "april", "may", "june",
                  "july", "august", "september", "october", "november", "december")
        if any(mn in low for mn in months) and re.search(r"\d{4}", low):
            return True
        return "report period:" in low and "[specify" not in low
