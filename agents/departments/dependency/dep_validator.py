import json

from core.state import AgentState
from infra.telemetry import get_logger
from agents.llm import call_llm
from agents.prompts import DEPENDENCY_VALIDATOR

logger = get_logger("dependency.validator")


class DepValidator:
    """Critic: validates the upgrade plan for safety.

    Rejects major bumps with no migration plan, unaddressed breaking
    changes, missing peer/transitive updates, unflagged license changes,
    missing rollback plan, and CVE fixes left out of the upgrade.
    """

    name = "dependency.validator"
    role = "critic"

    SYSTEM_PROMPT = DEPENDENCY_VALIDATOR

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
                "dep validator rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("dep validator approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty — no upgrade plan produced"]

        try:
            plan = json.loads(result)
        except json.JSONDecodeError:
            return ["Upgrade plan is not valid structured output"]

        audit = self._parse_audit(draft)
        outdated = audit.get("outdated", [])
        major_bumps = [o for o in outdated if o.get("lag") == "major"]
        migrations = plan.get("migration_guides", [])
        migrated = {m.get("package") for m in migrations}

        for o in major_bumps:
            if o.get("name") not in migrated:
                issues.append(
                    f"Major version bump of {o.get('name')} without a migration plan"
                )
                break

        for m in migrations:
            if m.get("breaking_changes") and not m.get("migration_steps"):
                issues.append(
                    f"Breaking changes in {m.get('package')} not addressed with steps"
                )
                break

        if major_bumps and not plan.get("peer_dependency_updates"):
            issues.append("Missing peer dependency updates for major bumps")

        audit_licenses = audit.get("license_issues", [])
        if audit_licenses and not plan.get("license_changes_flagged"):
            issues.append("License change not flagged in the upgrade plan")

        if major_bumps and not plan.get("deprecated_replacements"):
            issues.append("Deprecated package without a suggested replacement")

        if not plan.get("rollback_plan", "").strip():
            issues.append("No rollback plan")

        if not plan.get("test_plan"):
            issues.append("Missing test coverage plan for upgraded packages")

        audit_cves = {c.get("package") for c in audit.get("cve_list", [])}
        fixed = set(plan.get("cve_fixes_included", []))
        missing_cves = audit_cves - fixed
        if missing_cves:
            issues.append(
                f"CVE fix not included in upgrade: {', '.join(list(missing_cves)[:3])}"
            )

        if audit.get("version_conflicts") and "conflict" not in result.lower():
            issues.append("Transitive dependency conflicts from audit not resolved")

        return issues

    def _parse_audit(self, draft: str) -> dict:
        try:
            return json.loads(draft)
        except (json.JSONDecodeError, TypeError):
            return {}
