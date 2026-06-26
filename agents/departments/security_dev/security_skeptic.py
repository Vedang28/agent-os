import json

from core.state import AgentState
from infra.telemetry import get_logger
from agents.llm import call_llm
from agents.prompts import SECURITY_DEV_SKEPTIC

logger = get_logger("security_dev.skeptic")

# A finding is a likely false positive when its PoC itself admits the code
# path is already mitigated (the fix recommends safe patterns, so the fix
# field is NOT a signal — only the PoC/evidence is).
_MITIGATED_SIGNALS = (
    "already safe",
    "already mitigated",
    "not exploitable",
    "no impact",
    "n/a",
)


class SecuritySkeptic:
    """Critic: pressure-tests the security findings.

    Rejects false positives (safe patterns flagged), missed obvious
    injection points, findings without PoC or severity, and analyses that
    skip dependency CVEs, auth review, secrets, or rate limiting.
    """

    name = "security_dev.skeptic"
    role = "critic"

    SYSTEM_PROMPT = SECURITY_DEV_SKEPTIC

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
            logger.info(
                "security skeptic rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("security skeptic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty — no analysis produced"]

        try:
            analysis = json.loads(result)
        except json.JSONDecodeError:
            return ["Analysis is not valid structured output"]

        findings = analysis.get("findings", [])
        plan = self._parse_plan(draft)
        planned_vectors = set(plan.get("attack_vectors_to_test", []))
        found_vectors = {f.get("vector") for f in findings}

        missed = planned_vectors - found_vectors - {"follow_up"}
        if missed:
            issues.append(
                f"Missed vectors from threat model: {', '.join(list(missed)[:3])}"
            )

        for f in findings:
            if not f.get("severity"):
                issues.append(f"Finding '{f.get('vector')}' missing severity classification")
                break
        for f in findings:
            if f.get("vector") != "follow_up" and not f.get("poc"):
                issues.append(f"Finding '{f.get('vector')}' has no PoC for the claim")
                break
        for f in findings:
            fix = f.get("fix", "")
            if not fix or len(fix) < 15:
                issues.append(f"Finding '{f.get('vector')}' has incomplete fix recommendation")
                break

        for f in findings:
            poc = f.get("poc", "").lower()
            if any(sig in poc for sig in _MITIGATED_SIGNALS) and f.get("severity") == "critical":
                issues.append(
                    f"Possible false positive: '{f.get('vector')}' PoC shows the "
                    "code is already mitigated but it is rated critical"
                )
                break

        if not analysis.get("dependency_review", "").strip():
            issues.append("Ignoring dependency vulnerabilities — no CVE review")
        if not analysis.get("auth_review", "").strip():
            issues.append("Missing auth/access-control review")
        if not analysis.get("secrets_scan", "").strip():
            issues.append("No secrets scanning performed")
        if not analysis.get("rate_limiting_assessment", "").strip():
            issues.append("Missing rate limiting / abuse assessment")

        return issues

    def _parse_plan(self, draft: str) -> dict:
        try:
            return json.loads(draft)
        except (json.JSONDecodeError, TypeError):
            return {}
