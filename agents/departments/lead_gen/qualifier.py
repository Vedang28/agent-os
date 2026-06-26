import json
import re

from agents.prompts import LEAD_GEN_QUALIFIER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("lead_gen.qualifier")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Qualifier:
    """Critic: scores and qualifies enriched leads against the ICP.

    Rejects leads with missing/invalid contact data, no budget or timeline
    signal, no decision-maker, competitor customers, duplicates, or a lead
    score below the qualify threshold.
    """

    name = "lead_gen.qualifier"
    role = "critic"

    SYSTEM_PROMPT = LEAD_GEN_QUALIFIER

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info(
                "qualifier rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("qualifier approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty — no leads to qualify"]

        try:
            payload = json.loads(result)
        except json.JSONDecodeError:
            return ["Result is not valid JSON; cannot qualify leads"]

        leads = payload.get("leads", [])
        threshold = payload.get("qualify_threshold", 60)
        if not leads:
            return ["No leads present in enrichment output"]

        for lead in leads:
            issues.extend(self._review_lead(lead, threshold))
        return issues

    def _review_lead(self, lead: dict, threshold: int) -> list[str]:
        issues: list[str] = []
        company = lead.get("company", "unknown")
        contact = lead.get("contact", {})
        firmo = lead.get("firmographics", {})

        email = contact.get("email", "")
        if not _EMAIL_RE.match(email):
            issues.append(f"[{company}] Missing or invalid email address")
        elif not contact.get("email_verified"):
            issues.append(f"[{company}] Email not verified")

        if not contact.get("title"):
            issues.append(f"[{company}] No decision-maker / title identified")

        employees = firmo.get("employees")
        revenue = firmo.get("revenue_arr_usd")
        if employees is None and revenue is None:
            issues.append(f"[{company}] Missing company size / revenue data")
        elif employees is not None and (employees < 50 or employees > 5000):
            issues.append(f"[{company}] Company size outside ICP ({employees} employees)")

        if not lead.get("budget_signal"):
            issues.append(f"[{company}] No budget qualification signal")
        if not lead.get("timeline"):
            issues.append(f"[{company}] No timeline / urgency indicator")
        if lead.get("is_known_competitor_customer"):
            issues.append(f"[{company}] Lead is a known competitor's customer")
        if lead.get("duplicate"):
            issues.append(f"[{company}] Duplicate of existing lead in pipeline")
        if not lead.get("engagement_history"):
            issues.append(f"[{company}] Cold lead with no engagement history")

        score = lead.get("lead_score", 0)
        if score < threshold:
            issues.append(f"[{company}] Lead score {score} below threshold {threshold}")

        return issues
