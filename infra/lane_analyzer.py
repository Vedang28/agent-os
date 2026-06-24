from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel

from infra.telemetry import get_logger

logger = get_logger("infra.lane_analyzer")


class LaneStats(BaseModel):
    total_requests: int = 0
    instant_count: int = 0
    fast_count: int = 0
    deep_count: int = 0
    instant_pct: float = 0.0
    fast_pct: float = 0.0
    deep_pct: float = 0.0


class LaneAnalyzer:
    def __init__(self, lane_classifier: Callable[[dict], dict] | None = None):
        self._classify = lane_classifier

    def _get_classifier(self) -> Callable[[dict], dict]:
        if self._classify is not None:
            return self._classify
        from core.dispatcher import assign_lane
        return assign_lane

    def analyze(self, requests: list[str]) -> LaneStats:
        classify = self._get_classifier()

        total = len(requests)
        if total == 0:
            return LaneStats()

        counts: dict[str, int] = {"instant": 0, "fast": 0, "deep": 0}
        for req in requests:
            result = classify({"request": req})
            lane = result["lane"]
            counts[lane] += 1

        return LaneStats(
            total_requests=total,
            instant_count=counts["instant"],
            fast_count=counts["fast"],
            deep_count=counts["deep"],
            instant_pct=round(counts["instant"] / total * 100, 2),
            fast_pct=round(counts["fast"] / total * 100, 2),
            deep_pct=round(counts["deep"] / total * 100, 2),
        )

    def suggest_threshold_changes(
        self, stats: LaneStats, target_instant_pct: float = 90.0
    ) -> list[str]:
        if stats.instant_pct >= target_instant_pct:
            return []

        suggestions: list[str] = []
        suggestions.append("Add more instant keywords to dispatcher")
        suggestions.append(
            "Consider raising the word-count threshold for deep lane (currently >15 words)"
        )
        return suggestions
