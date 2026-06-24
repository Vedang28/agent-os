from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from infra.telemetry import get_logger

logger = get_logger("infra.cost_tracker")


class CostRecord(BaseModel):
    task_id: str
    department: str
    model: str
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    wall_clock_seconds: float = 0.0
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CostSummary(BaseModel):
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    total_records: int = 0
    by_department: dict[str, float] = {}
    by_model: dict[str, float] = {}
    burn_rate_per_hour: float = 0.0


class CostTracker:
    def __init__(self, storage_path: Path | str | None = None) -> None:
        if storage_path is None:
            self._storage_path = Path.home() / ".agent-os" / "costs.json"
        else:
            self._storage_path = Path(storage_path).resolve()
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[CostRecord] = self._load()

    def _load(self) -> list[CostRecord]:
        if not self._storage_path.exists():
            return []
        try:
            data = json.loads(self._storage_path.read_text())
            return [CostRecord(**r) for r in data]
        except Exception:
            logger.warning("failed to load cost records from %s", self._storage_path)
            return []

    def _save(self) -> None:
        self._storage_path.write_text(
            json.dumps([r.model_dump() for r in self._records], indent=2)
        )

    def record(self, rec: CostRecord) -> None:
        self._records.append(rec)
        self._save()
        logger.info(
            "cost recorded: dept=%s model=%s cost=%.4f",
            rec.department, rec.model, rec.cost_usd,
        )

    def _aggregate(self, records: list[CostRecord]) -> CostSummary:
        total_cost = sum(r.cost_usd for r in records)
        total_tokens = sum(r.tokens_input + r.tokens_output for r in records)
        by_dept: dict[str, float] = {}
        by_model: dict[str, float] = {}
        for r in records:
            by_dept[r.department] = by_dept.get(r.department, 0.0) + r.cost_usd
            by_model[r.model] = by_model.get(r.model, 0.0) + r.cost_usd
        return CostSummary(
            total_cost_usd=total_cost,
            total_tokens=total_tokens,
            total_records=len(records),
            by_department=by_dept,
            by_model=by_model,
            burn_rate_per_hour=self.get_burn_rate(),
        )

    def get_total(self) -> CostSummary:
        return self._aggregate(self._records)

    def get_by_department(self, department: str) -> CostSummary:
        filtered = [r for r in self._records if r.department == department]
        return self._aggregate(filtered)

    def get_by_model(self, model: str) -> CostSummary:
        filtered = [r for r in self._records if r.model == model]
        return self._aggregate(filtered)

    def get_burn_rate(self, window_hours: float = 24.0) -> float:
        if not self._records:
            return 0.0
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - (window_hours * 3600)
        window_cost = 0.0
        for r in self._records:
            try:
                ts = datetime.fromisoformat(r.timestamp).timestamp()
            except (ValueError, TypeError):
                continue
            if ts >= cutoff:
                window_cost += r.cost_usd
        if window_cost == 0.0:
            return 0.0
        return window_cost / window_hours

    def check_ceiling(self, ceiling_usd: float) -> bool:
        total = sum(r.cost_usd for r in self._records)
        return total >= ceiling_usd


_tracker: CostTracker | None = None


def get_cost_tracker(storage_path: Path | str | None = None) -> CostTracker:
    global _tracker
    if _tracker is None:
        _tracker = CostTracker(storage_path)
    return _tracker


def reset_cost_tracker() -> None:
    global _tracker
    _tracker = None
