import pytest

from brain.outcome import Outcome, OutcomeStore
from brain.obsidian import ObsidianVault


@pytest.fixture()
def vault(tmp_path):
    return ObsidianVault(tmp_path / "vault")


@pytest.fixture()
def store(vault):
    return OutcomeStore(vault)


class TestOutcomeModel:
    def test_valid_outcome(self):
        o = Outcome(
            task_id="t1",
            department="engineering",
            success=True,
            revisions=1,
            tokens_used=500,
            wall_clock_seconds=10.0,
        )
        assert o.task_id == "t1"
        assert o.success is True

    def test_defaults(self):
        o = Outcome(task_id="t2", department="intelligence", success=False)
        assert o.revisions == 0
        assert o.critic_verdict == "approved"
        assert o.user_feedback is None
        assert o.tool_errors == []
        assert o.tokens_used == 0

    def test_rejects_negative_tokens(self):
        with pytest.raises(ValueError, match="non-negative"):
            Outcome(task_id="t3", department="eng", success=True, tokens_used=-1)

    def test_rejects_negative_wall_clock(self):
        with pytest.raises(ValueError, match="non-negative"):
            Outcome(
                task_id="t4", department="eng", success=True, wall_clock_seconds=-1.0
            )

    def test_sanitizes_tool_errors(self):
        long_err = "x" * 1000
        o = Outcome(
            task_id="t5",
            department="eng",
            success=False,
            tool_errors=[long_err, "short"],
        )
        assert len(o.tool_errors[0]) == 500
        assert o.tool_errors[1] == "short"

    def test_sanitizes_null_bytes(self):
        o = Outcome(
            task_id="t6",
            department="eng",
            success=False,
            tool_errors=["hello\x00world"],
        )
        assert "\x00" not in o.tool_errors[0]

    def test_sanitizes_html(self):
        o = Outcome(
            task_id="t7",
            department="eng",
            success=False,
            tool_errors=["<script>alert(1)</script>"],
        )
        assert "<script>" not in o.tool_errors[0]
        assert "&lt;script&gt;" in o.tool_errors[0]


class TestOutcomeStore:
    def test_record_writes_note(self, store, vault):
        o = Outcome(task_id="task-1", department="engineering", success=True)
        store.record(o)
        notes = vault.list_notes()
        assert any("task-1" in t for t in notes)

    def test_record_tags_with_outcome(self, store, vault):
        o = Outcome(task_id="task-2", department="intelligence", success=False)
        store.record(o)
        note = vault.read_note("Outcome_ task-2")
        assert "outcome" in note.tags

    def test_query_recent_returns_outcomes(self, store):
        for i in range(7):
            store.record(
                Outcome(
                    task_id=f"t-{i}",
                    department="eng",
                    success=True,
                    timestamp=f"2026-01-01T0{i}:00:00+00:00",
                )
            )
        recent = store.query_recent(n=5)
        assert len(recent) == 5
        assert recent[0].timestamp > recent[1].timestamp

    def test_query_by_department(self, store):
        store.record(Outcome(task_id="a", department="eng", success=True))
        store.record(Outcome(task_id="b", department="intel", success=True))
        store.record(Outcome(task_id="c", department="eng", success=False))
        eng = store.query_by_department("eng")
        assert len(eng) == 2
        assert all(o.department == "eng" for o in eng)

    def test_query_failures(self, store):
        store.record(Outcome(task_id="ok", department="eng", success=True))
        store.record(Outcome(task_id="fail1", department="eng", success=False))
        store.record(Outcome(task_id="fail2", department="intel", success=False))
        failures = store.query_failures()
        assert len(failures) == 2
        assert all(not o.success for o in failures)
