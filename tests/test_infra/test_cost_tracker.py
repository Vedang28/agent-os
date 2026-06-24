import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from infra.cost_tracker import (
    CostRecord,
    CostSummary,
    CostTracker,
    get_cost_tracker,
    reset_cost_tracker,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_cost_tracker()
    yield
    reset_cost_tracker()


class TestCostRecord:
    def test_defaults(self):
        rec = CostRecord(task_id="t1", department="engineering", model="claude")
        assert rec.tokens_input == 0
        assert rec.tokens_output == 0
        assert rec.cost_usd == 0.0
        assert rec.wall_clock_seconds == 0.0

    def test_timestamp_auto(self):
        rec = CostRecord(task_id="t1", department="eng", model="claude")
        ts = datetime.fromisoformat(rec.timestamp)
        assert ts.tzinfo is not None
        assert (datetime.now(timezone.utc) - ts).total_seconds() < 5


class TestCostTracker:
    def test_record_and_get_total(self, tmp_path: Path):
        tracker = CostTracker(tmp_path / "costs.json")
        for i in range(3):
            tracker.record(CostRecord(
                task_id=f"t{i}",
                department="engineering",
                model="claude",
                cost_usd=1.5,
                tokens_input=100,
                tokens_output=50,
            ))
        summary = tracker.get_total()
        assert summary.total_cost_usd == pytest.approx(4.5)
        assert summary.total_tokens == 450
        assert summary.total_records == 3

    def test_get_by_department(self, tmp_path: Path):
        tracker = CostTracker(tmp_path / "costs.json")
        tracker.record(CostRecord(
            task_id="t1", department="engineering", model="claude", cost_usd=2.0,
        ))
        tracker.record(CostRecord(
            task_id="t2", department="intelligence", model="claude", cost_usd=3.0,
        ))
        eng = tracker.get_by_department("engineering")
        assert eng.total_cost_usd == pytest.approx(2.0)
        assert eng.total_records == 1
        intel = tracker.get_by_department("intelligence")
        assert intel.total_cost_usd == pytest.approx(3.0)

    def test_get_by_model(self, tmp_path: Path):
        tracker = CostTracker(tmp_path / "costs.json")
        tracker.record(CostRecord(
            task_id="t1", department="eng", model="claude", cost_usd=2.0,
        ))
        tracker.record(CostRecord(
            task_id="t2", department="eng", model="gemini", cost_usd=1.0,
        ))
        claude = tracker.get_by_model("claude")
        assert claude.total_cost_usd == pytest.approx(2.0)
        gemini = tracker.get_by_model("gemini")
        assert gemini.total_cost_usd == pytest.approx(1.0)

    def test_get_burn_rate(self, tmp_path: Path):
        tracker = CostTracker(tmp_path / "costs.json")
        now = datetime.now(timezone.utc)
        tracker.record(CostRecord(
            task_id="t1", department="eng", model="claude",
            cost_usd=24.0,
            timestamp=now.isoformat(),
        ))
        rate = tracker.get_burn_rate(window_hours=24.0)
        assert rate > 0.0
        assert rate == pytest.approx(1.0)

    def test_burn_rate_empty(self, tmp_path: Path):
        tracker = CostTracker(tmp_path / "costs.json")
        assert tracker.get_burn_rate() == 0.0

    def test_check_ceiling_below(self, tmp_path: Path):
        tracker = CostTracker(tmp_path / "costs.json")
        tracker.record(CostRecord(
            task_id="t1", department="eng", model="claude", cost_usd=5.0,
        ))
        assert tracker.check_ceiling(10.0) is False

    def test_check_ceiling_above(self, tmp_path: Path):
        tracker = CostTracker(tmp_path / "costs.json")
        tracker.record(CostRecord(
            task_id="t1", department="eng", model="claude", cost_usd=15.0,
        ))
        assert tracker.check_ceiling(10.0) is True

    def test_persistence(self, tmp_path: Path):
        path = tmp_path / "costs.json"
        tracker1 = CostTracker(path)
        tracker1.record(CostRecord(
            task_id="t1", department="eng", model="claude", cost_usd=5.0,
        ))
        tracker2 = CostTracker(path)
        assert tracker2.get_total().total_records == 1
        assert tracker2.get_total().total_cost_usd == pytest.approx(5.0)

    def test_empty_tracker(self, tmp_path: Path):
        tracker = CostTracker(tmp_path / "costs.json")
        summary = tracker.get_total()
        assert summary.total_cost_usd == 0.0
        assert summary.total_tokens == 0
        assert summary.total_records == 0
        assert summary.by_department == {}
        assert summary.by_model == {}

    def test_singleton(self, tmp_path: Path):
        path = tmp_path / "costs.json"
        a = get_cost_tracker(path)
        b = get_cost_tracker(path)
        assert a is b

    def test_by_department_aggregation(self, tmp_path: Path):
        tracker = CostTracker(tmp_path / "costs.json")
        tracker.record(CostRecord(
            task_id="t1", department="engineering", model="claude", cost_usd=2.0,
        ))
        tracker.record(CostRecord(
            task_id="t2", department="engineering", model="gemini", cost_usd=3.0,
        ))
        tracker.record(CostRecord(
            task_id="t3", department="intelligence", model="claude", cost_usd=1.0,
        ))
        summary = tracker.get_total()
        assert summary.by_department["engineering"] == pytest.approx(5.0)
        assert summary.by_department["intelligence"] == pytest.approx(1.0)
        assert summary.by_model["claude"] == pytest.approx(3.0)
        assert summary.by_model["gemini"] == pytest.approx(3.0)
