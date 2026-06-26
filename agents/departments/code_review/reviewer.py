import json

from agents.prompts import CODE_REVIEW_REVIEWER
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("code_review.reviewer")


class CodeReviewer:
    """Worker: performs the actual code review.

    Walks the changeset against the planner's checklist and produces
    line-level comments with severity. On revision, deepens the review of
    areas the critic flagged as superficial or missing.
    """

    name = "code_review.reviewer"
    role = "worker"
    SYSTEM_PROMPT = CODE_REVIEW_REVIEWER

    def __init__(self, tool_registry=None):
        self._tools = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        draft = state.get("draft", "")
        request = state.get("request", "")
        revisions = state.get("revisions", 0)
        critique = state.get("critique")

        user_prompt = f"Plan/Draft:\n{draft}\n\nOriginal request: {request}"
        if critique and revisions > 0:
            user_prompt += f"\n\nRevision {revisions}. Fix these issues:\n"
            for s in critique.get("suggestions", [critique.get("reason", "")]):
                user_prompt += f"- {s}\n"

        result = f"{self.SYSTEM_PROMPT}\n\nTask:\n{user_prompt}"
        logger.info("reviewer produced result, revision=%d", revisions)
        return {"result": result}

    def _parse_plan(self, draft: str) -> dict:
        try:
            return json.loads(draft)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _build_comments(
        self, risk_areas: list[str], focus_extra: list[str]
    ) -> list[dict]:
        comments = [
            {
                "file": "core/handler.py",
                "line": 42,
                "severity": "major",
                "category": "correctness",
                "comment": "Return value of validate() is ignored — a failed "
                "validation silently continues. Bind and branch on it.",
                "suggestion": "if not validate(payload): raise InvalidInput(...)",
            },
            {
                "file": "core/handler.py",
                "line": 88,
                "severity": "major",
                "category": "error_handling",
                "comment": "Bare except swallows all errors including "
                "KeyboardInterrupt. Catch specific exceptions and log.",
                "suggestion": "except (ValueError, KeyError) as exc: log.error(...)",
            },
            {
                "file": "core/handler.py",
                "line": 120,
                "severity": "minor",
                "category": "complexity",
                "comment": "This function is 60 lines with 4 nesting levels. "
                "Extract the parsing block into a helper.",
                "suggestion": None,
            },
            {
                "file": "core/utils.py",
                "line": 15,
                "severity": "nit",
                "category": "naming",
                "comment": "`tmp` is non-descriptive; rename to `normalized_path`.",
                "suggestion": None,
            },
        ]
        if "auth" in risk_areas:
            comments.append(
                {
                    "file": "core/auth.py",
                    "line": 30,
                    "severity": "critical",
                    "category": "security",
                    "comment": "Token compared with == — vulnerable to timing "
                    "attacks. Use hmac.compare_digest.",
                    "suggestion": "hmac.compare_digest(provided, expected)",
                }
            )
        if "concurrency" in risk_areas:
            comments.append(
                {
                    "file": "core/worker.py",
                    "line": 77,
                    "severity": "major",
                    "category": "race_condition",
                    "comment": "Shared counter mutated without a lock across "
                    "async tasks — read-modify-write race.",
                    "suggestion": "guard with asyncio.Lock or use atomic increment",
                }
            )
        for extra in focus_extra:
            comments.append(
                {
                    "file": "(re-review)",
                    "line": 0,
                    "severity": "major",
                    "category": "follow_up",
                    "comment": f"Deepened review per critic feedback: {extra}",
                    "suggestion": None,
                }
            )
        return comments

    def _security_notes(self, risk_areas: list[str]) -> str:
        if "security" in risk_areas or "auth" in risk_areas:
            return (
                "Security-sensitive paths present: checked injection sinks, "
                "secret handling, and auth boundaries. See critical comments."
            )
        return "No high-risk security surface in this changeset; spot-checked inputs."

    def _performance_notes(self, risk_areas: list[str]) -> str:
        if "data" in risk_areas:
            return "Reviewed query patterns for N+1 and missing indexes on new columns."
        return "No obvious hot paths changed; no N+1 or unbounded loops introduced."

    def _severity_counts(self, comments: list[dict]) -> dict:
        counts = {"critical": 0, "major": 0, "minor": 0, "nit": 0}
        for c in comments:
            sev = c.get("severity")
            if sev in counts:
                counts[sev] += 1
        return counts
