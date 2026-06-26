import json
import re

from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import MEMORY_LOG_AUDITOR

logger = get_logger("memory.log_auditor")

_VAGUE_TERMS = (
    "did stuff",
    "stuff",
    "things",
    "various changes",
    "misc",
    "miscellaneous",
    "some changes",
    "work",
    "updated code",
)
_BLOCKER_CUES = ("blocked", "blocker", "stuck", "cannot", "couldn't", "failing", "broken")
_DONE_CUES = ("completed", "finished", "done", "shipped", "merged", "resolved")
_REF_PATTERN = re.compile(r"[\w./-]+\.\w{1,5}|\b[0-9a-f]{7,40}\b")


class LogAuditor:
    """Critic: audits session logs and ADRs for quality and consistency."""

    name = "memory.log_auditor"
    role = "critic"

    SYSTEM_PROMPT = MEMORY_LOG_AUDITOR

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft, state.get("brain_context", []))


        if issues:
            logger.info(
                "log_auditor rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("log_auditor approved after %d revisions", revisions)
        return {"approved": True}

    def _review(
        self, result: str, draft: str, brain_context: list[dict] | None = None
    ) -> list[str]:
        brain_context = brain_context or []
        try:
            parsed = json.loads(result) if result else {}
        except json.JSONDecodeError:
            return ["Result is not valid JSON; log format is unparseable"]

        session = parsed.get("session_log", parsed)
        adrs = parsed.get("adrs", [])
        issues: list[str] = []

        # --- Session-log checks ---
        if not session.get("timestamp") and not session.get("date"):
            issues.append("Session log is missing a timestamp/date")

        if session.get("format") != "session-log-v1":
            issues.append("Inconsistent log format (expected 'session-log-v1')")

        summary = (session.get("summary") or "").strip()
        if not summary:
            issues.append("Session log is missing a summary")
        elif any(term in summary.lower() for term in _VAGUE_TERMS):
            issues.append(f"Vague summary without specifics: {summary!r}")

        changes = session.get("changes", []) or []
        for change in changes:
            if any(term in str(change).lower() for term in _VAGUE_TERMS):
                issues.append(f"Vague change description: {change!r}")
        if changes and not any(_REF_PATTERN.search(str(c)) for c in changes):
            issues.append("No change references a specific file or commit")

        if "next_steps" not in session or not session.get("next_steps"):
            issues.append("Missing 'next steps' / what's-next section")

        # Blockers implied in the summary but not captured in the blockers list.
        blockers = session.get("blockers", []) or []
        if any(cue in summary.lower() for cue in _BLOCKER_CUES) and not blockers:
            issues.append("Summary mentions a blocker that is not flagged in blockers")

        # Contradiction: claims completion while also reporting it as blocked.
        if (
            any(cue in summary.lower() for cue in _DONE_CUES)
            and blockers
            and any(cue in summary.lower() for cue in _BLOCKER_CUES)
        ):
            issues.append("Session claims completion but also reports a blocker")

        # --- ADR / decision checks ---
        known_titles = {
            self._norm(ctx.get("title", "")) for ctx in brain_context
        }
        seen: set[str] = set()
        for adr in adrs:
            title = adr.get("title", "untitled")
            if not adr.get("context"):
                issues.append(f"Decision recorded without rationale/context: {title}")
            if not adr.get("consequences"):
                issues.append(f"Decision missing consequences/trade-offs: {title}")

            key = self._norm(title)
            if key and key in seen:
                issues.append(f"Duplicate decision recorded: {title}")
            seen.add(key)
            if key and key in known_titles:
                issues.append(f"Decision duplicates one already in the brain: {title}")

        # A session that logged decisions but produced no ADRs lost them.
        if session.get("decisions") and not adrs:
            issues.append("Session logged decisions but no ADRs were recorded")

        return issues

    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
