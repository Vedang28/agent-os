import pytest

from infra.lane_analyzer import LaneStats, LaneAnalyzer


class TestLaneStats:
    def test_defaults(self):
        stats = LaneStats()
        assert stats.total_requests == 0
        assert stats.instant_count == 0
        assert stats.fast_count == 0
        assert stats.deep_count == 0
        assert stats.instant_pct == 0.0
        assert stats.fast_pct == 0.0
        assert stats.deep_pct == 0.0

    def test_model_validation(self):
        stats = LaneStats(total_requests=10, instant_count=5, instant_pct=50.0)
        assert stats.total_requests == 10
        assert stats.instant_count == 5
        assert stats.instant_pct == 50.0


class TestLaneAnalyzer:
    def setup_method(self):
        self.analyzer = LaneAnalyzer()

    def test_analyze_all_instant(self):
        stats = self.analyzer.analyze(["hello", "hi", "ping"])
        assert stats.total_requests == 3
        assert stats.instant_count == 3
        assert stats.instant_pct == 100.0
        assert stats.fast_count == 0
        assert stats.deep_count == 0

    def test_analyze_all_deep(self):
        stats = self.analyzer.analyze(["build a REST API", "create a microservice"])
        assert stats.total_requests == 2
        assert stats.deep_count == 2
        assert stats.deep_pct == 100.0
        assert stats.instant_count == 0

    def test_analyze_mixed(self):
        stats = self.analyzer.analyze(["hello", "build a REST API", "summarize this"])
        assert stats.total_requests == 3
        assert stats.instant_count == 1
        assert stats.deep_count == 1
        assert stats.fast_count == 1
        assert abs(stats.instant_pct - 33.33) < 0.1
        assert abs(stats.fast_pct - 33.33) < 0.1
        assert abs(stats.deep_pct - 33.33) < 0.1

    def test_analyze_empty(self):
        stats = self.analyzer.analyze([])
        assert stats.total_requests == 0
        assert stats.instant_count == 0
        assert stats.fast_count == 0
        assert stats.deep_count == 0
        assert stats.instant_pct == 0.0
        assert stats.fast_pct == 0.0
        assert stats.deep_pct == 0.0

    def test_suggest_no_changes_above_target(self):
        stats = LaneStats(
            total_requests=100, instant_count=95, instant_pct=95.0,
            fast_count=3, fast_pct=3.0, deep_count=2, deep_pct=2.0,
        )
        suggestions = self.analyzer.suggest_threshold_changes(stats)
        assert suggestions == []

    def test_suggest_changes_below_target(self):
        stats = LaneStats(
            total_requests=100, instant_count=50, instant_pct=50.0,
            fast_count=30, fast_pct=30.0, deep_count=20, deep_pct=20.0,
        )
        suggestions = self.analyzer.suggest_threshold_changes(stats)
        assert len(suggestions) > 0
        assert any("instant keywords" in s for s in suggestions)

    def test_percentages_sum(self):
        stats = self.analyzer.analyze(["hello", "build an app", "summarize this", "ping", "hey"])
        total_pct = stats.instant_pct + stats.fast_pct + stats.deep_pct
        assert abs(total_pct - 100.0) < 0.1
