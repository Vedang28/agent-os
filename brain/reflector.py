from collections import Counter

from brain.obsidian import ObsidianVault
from brain.outcome import Outcome, OutcomeStore
from brain.playbook import PLAYBOOK_TAG
from brain.schema import Note
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("brain.reflector")


class Reflector:
    name = "core.reflector"
    role = "learning"

    MIN_OUTCOMES_TO_REFLECT: int = 5

    def __init__(self, obsidian: ObsidianVault, outcome_store: OutcomeStore):
        self._obsidian = obsidian
        self._outcome_store = outcome_store

    async def run(self, state: AgentState) -> AgentState:
        outcomes = self._outcome_store.query_recent(n=20)

        if len(outcomes) < self.MIN_OUTCOMES_TO_REFLECT:
            logger.info(
                "reflector: only %d outcomes, need %d — skipping",
                len(outcomes),
                self.MIN_OUTCOMES_TO_REFLECT,
            )
            return {
                "result": f"Skipped reflection: only {len(outcomes)} outcomes "
                f"(need {self.MIN_OUTCOMES_TO_REFLECT})",
                "approved": True,
            }

        playbooks_written: list[str] = []

        failure_patterns = self._detect_failure_patterns(outcomes)
        for dept, count in failure_patterns.items():
            title = f"Playbook: {dept} failure pattern"
            content = (
                f"Pattern: {count} recent failures in {dept}.\n"
                f"Recommended action: Review {dept} prompts and constraints.\n"
                f"Evidence: {count} of {len(outcomes)} recent outcomes failed."
            )
            self._write_playbook(title, content, dept)
            playbooks_written.append(title)

        high_revision_depts = self._detect_high_revisions(outcomes)
        for dept, avg_rev in high_revision_depts.items():
            title = f"Playbook: {dept} high revisions"
            content = (
                f"Pattern: Average {avg_rev:.1f} revisions in {dept}.\n"
                f"Recommended action: Improve first-draft quality in {dept} proposer.\n"
                f"Evidence: High revision count across recent outcomes."
            )
            self._write_playbook(title, content, dept)
            playbooks_written.append(title)

        tool_error_depts = self._detect_tool_errors(outcomes)
        for dept, errors in tool_error_depts.items():
            title = f"Playbook: {dept} tool errors"
            content = (
                f"Pattern: Recurring tool errors in {dept}.\n"
                f"Common errors: {', '.join(errors[:3])}.\n"
                f"Recommended action: Validate tool inputs before calling.\n"
                f"Evidence: {len(errors)} tool errors in recent outcomes."
            )
            self._write_playbook(title, content, dept)
            playbooks_written.append(title)

        successful_depts = self._detect_successful_strategies(outcomes)
        for dept, count in successful_depts.items():
            title = f"Playbook: {dept} successful strategy"
            content = (
                f"Pattern: {count} recent successes in {dept} with 0 revisions.\n"
                f"Recommended action: Maintain current approach in {dept}.\n"
                f"Evidence: {count} zero-revision successes."
            )
            self._write_playbook(title, content, dept)
            playbooks_written.append(title)

        cost_outliers = self._detect_cost_outliers(outcomes)
        for dept, avg_tokens in cost_outliers.items():
            title = f"Playbook: {dept} cost outlier"
            content = (
                f"Pattern: High average token usage ({avg_tokens:.0f}) in {dept}.\n"
                f"Recommended action: Use budget-conscious approaches.\n"
                f"Evidence: Token usage significantly above median."
            )
            self._write_playbook(title, content, dept)
            playbooks_written.append(title)

        summary = (
            f"Reflected on {len(outcomes)} outcomes. "
            f"Wrote {len(playbooks_written)} playbook notes."
        )
        logger.info("reflector: %s", summary)

        return {
            "result": summary,
            "approved": True,
        }

    def _write_playbook(self, title: str, content: str, department: str) -> None:
        note = Note(
            title=title,
            content=content,
            tags=[PLAYBOOK_TAG, f"{PLAYBOOK_TAG}/{department}"],
        )
        self._obsidian.write_note(note)

    def _detect_failure_patterns(
        self, outcomes: list[Outcome]
    ) -> dict[str, int]:
        dept_failures: Counter[str] = Counter()
        for o in outcomes:
            if not o.success:
                dept_failures[o.department] += 1
        return {dept: count for dept, count in dept_failures.items() if count >= 2}

    def _detect_high_revisions(
        self, outcomes: list[Outcome]
    ) -> dict[str, float]:
        dept_revisions: dict[str, list[int]] = {}
        for o in outcomes:
            dept_revisions.setdefault(o.department, []).append(o.revisions)
        return {
            dept: sum(revs) / len(revs)
            for dept, revs in dept_revisions.items()
            if sum(revs) / len(revs) >= 2.0
        }

    def _detect_tool_errors(
        self, outcomes: list[Outcome]
    ) -> dict[str, list[str]]:
        dept_errors: dict[str, list[str]] = {}
        for o in outcomes:
            if o.tool_errors:
                dept_errors.setdefault(o.department, []).extend(o.tool_errors)
        return {dept: errs for dept, errs in dept_errors.items() if len(errs) >= 2}

    def _detect_successful_strategies(
        self, outcomes: list[Outcome]
    ) -> dict[str, int]:
        dept_successes: Counter[str] = Counter()
        for o in outcomes:
            if o.success and o.revisions == 0:
                dept_successes[o.department] += 1
        return {dept: count for dept, count in dept_successes.items() if count >= 2}

    def _detect_cost_outliers(
        self, outcomes: list[Outcome]
    ) -> dict[str, float]:
        all_tokens = [o.tokens_used for o in outcomes if o.tokens_used > 0]
        if not all_tokens:
            return {}
        median = sorted(all_tokens)[len(all_tokens) // 2]
        threshold = median * 2.0

        dept_tokens: dict[str, list[int]] = {}
        for o in outcomes:
            if o.tokens_used > 0:
                dept_tokens.setdefault(o.department, []).append(o.tokens_used)

        return {
            dept: sum(tokens) / len(tokens)
            for dept, tokens in dept_tokens.items()
            if sum(tokens) / len(tokens) > threshold
        }
