import html
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

from brain.obsidian import ObsidianVault
from brain.schema import Note
from infra.telemetry import get_logger

logger = get_logger("brain.outcome")


class Outcome(BaseModel):
    task_id: str
    department: str
    success: bool
    revisions: int = 0
    critic_verdict: str = "approved"
    user_feedback: str | None = None
    tool_errors: list[str] = Field(default_factory=list)
    tokens_used: int = 0
    wall_clock_seconds: float = 0.0
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @field_validator("tokens_used")
    @classmethod
    def tokens_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("tokens_used must be non-negative")
        return v

    @field_validator("wall_clock_seconds")
    @classmethod
    def wall_clock_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("wall_clock_seconds must be non-negative")
        return v

    @field_validator("tool_errors")
    @classmethod
    def sanitize_tool_errors(cls, v: list[str]) -> list[str]:
        sanitized = []
        for err in v:
            clean = str(err)[:500]
            clean = clean.replace("\x00", "")
            clean = html.escape(clean)
            sanitized.append(clean)
        return sanitized


class OutcomeStore:
    TAG = "outcome"

    def __init__(self, obsidian: ObsidianVault):
        self._obsidian = obsidian

    def record(self, outcome: Outcome) -> None:
        note = Note(
            title=f"Outcome: {outcome.task_id}",
            content=outcome.model_dump_json(indent=2),
            tags=[self.TAG, f"dept/{outcome.department}"],
        )
        self._obsidian.write_note(note)
        logger.info(
            "recorded outcome task_id=%s dept=%s success=%s",
            outcome.task_id,
            outcome.department,
            outcome.success,
        )

    def query_recent(self, n: int = 20) -> list[Outcome]:
        return self._load_outcomes()[:n]

    def query_by_department(self, department: str) -> list[Outcome]:
        return [o for o in self._load_outcomes() if o.department == department]

    def query_failures(self) -> list[Outcome]:
        return [o for o in self._load_outcomes() if not o.success]

    def _load_outcomes(self) -> list[Outcome]:
        outcomes: list[Outcome] = []
        for title in self._obsidian.list_notes():
            if not title.startswith("Outcome_"):
                continue
            try:
                note = self._obsidian.read_note(title)
                if self.TAG in note.tags:
                    outcomes.append(Outcome.model_validate_json(note.content))
            except Exception:
                logger.warning("skipping malformed outcome note: %s", title)
        outcomes.sort(key=lambda o: o.timestamp, reverse=True)
        return outcomes
