import json

from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import BUG_TRIAGE_VALIDATOR

logger = get_logger("bug_triage.validator")

_CORRELATION_WORDS = ("seems", "probably", "might be", "likely", "could be")


class BugValidator:
    """Critic: validates the bug analysis for rigor.

    Rejects unproven root causes (correlation dressed as causation),
    incomplete repro steps, missing regression test, missing related-bug
    check, risky fixes, and under/over-estimated severity.
    """

    name = "bug_triage.validator"
    role = "critic"

    SYSTEM_PROMPT = BUG_TRIAGE_VALIDATOR

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)

        if issues:
            logger.info(
                "bug validator rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("bug validator approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty — no diagnosis produced"]

        try:
            diag = json.loads(result)
        except json.JSONDecodeError:
            return ["Diagnosis is not valid structured output"]

        steps = diag.get("reproduction_steps", [])
        if len(steps) < 3:
            issues.append("Reproduction steps incomplete (cannot independently repro)")

        if not diag.get("root_cause", "").strip():
            issues.append("No root cause identified")

        evidence = diag.get("root_cause_evidence", "").lower()
        if not evidence or any(w in evidence for w in _CORRELATION_WORDS):
            issues.append(
                "Root cause not proven — reads as correlation, not causation "
                "(no isolate-and-restore evidence)"
            )

        if not diag.get("regression_test", "").strip():
            issues.append("Missing regression test for the bug")

        if "related_bugs_checked" not in diag:
            issues.append("No check for related/duplicate bugs")

        fix = diag.get("fix_approach", "").lower()
        if not fix:
            issues.append("No fix approach suggested")
        elif "test" not in fix and "regression" not in (diag.get("regression_test", "").lower()):
            issues.append("Fix suggested without an accompanying test — may regress")

        triage = self._parse_triage(draft)
        repro = triage.get("reproducibility", "")
        if repro == "intermittent" and "alternative" not in result.lower():
            issues.append(
                "Intermittent bug but no alternative reproduction path attempted"
            )

        if self._severity_mismatch(triage, diag):
            issues.append(
                "Severity looks mis-estimated for the diagnosed impact "
                "(data-loss/security root cause rated low, or trivial rated P0)"
            )

        if not diag.get("confirmed_version", "").strip():
            issues.append("Missing affected version info (not confirmed during repro)")

        return issues

    def _parse_triage(self, draft: str) -> dict:
        try:
            return json.loads(draft)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _severity_mismatch(self, triage: dict, diag: dict) -> bool:
        severity = triage.get("severity", "P3")
        root = diag.get("root_cause", "").lower()
        high_impact = any(w in root for w in ("data", "transaction", "authorization", "leak"))
        if high_impact and severity in ("P2", "P3"):
            return True
        return False
