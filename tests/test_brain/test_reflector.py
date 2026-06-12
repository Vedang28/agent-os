import pytest

from brain.obsidian import ObsidianVault
from brain.outcome import Outcome, OutcomeStore
from brain.playbook import PLAYBOOK_TAG, get_playbooks
from brain.reflector import Reflector


@pytest.fixture()
def vault(tmp_path):
    return ObsidianVault(tmp_path / "vault")


@pytest.fixture()
def outcome_store(vault):
    return OutcomeStore(vault)


@pytest.fixture()
def reflector(vault, outcome_store):
    return Reflector(obsidian=vault, outcome_store=outcome_store)


def _record_outcomes(store, n=6, department="engineering", success=True, revisions=0, tool_errors=None, tokens_used=100):
    for i in range(n):
        store.record(
            Outcome(
                task_id=f"task-{i}",
                department=department,
                success=success,
                revisions=revisions,
                tool_errors=tool_errors or [],
                tokens_used=tokens_used,
                timestamp=f"2026-01-01T{i:02d}:00:00+00:00",
            )
        )


class TestReflector:
    @pytest.mark.asyncio
    async def test_skips_when_too_few_outcomes(self, reflector, outcome_store):
        outcome_store.record(
            Outcome(task_id="only-one", department="eng", success=True)
        )
        result = await reflector.run({})
        assert "Skipped" in result["result"]
        assert result["approved"] is True

    @pytest.mark.asyncio
    async def test_detects_failure_pattern(self, reflector, outcome_store, vault):
        _record_outcomes(outcome_store, n=5, department="engineering", success=False)
        await reflector.run({})
        playbooks = get_playbooks("engineering", vault)
        assert len(playbooks) >= 1
        assert any("failure_pattern" in pb.title for pb in playbooks)

    @pytest.mark.asyncio
    async def test_detects_successful_strategy(self, reflector, outcome_store, vault):
        _record_outcomes(
            outcome_store, n=5, department="engineering", success=True, revisions=0
        )
        await reflector.run({})
        playbooks = get_playbooks("engineering", vault)
        assert any("successful_strategy" in pb.title for pb in playbooks)

    @pytest.mark.asyncio
    async def test_detects_high_revisions(self, reflector, outcome_store, vault):
        _record_outcomes(
            outcome_store, n=5, department="engineering", success=True, revisions=3
        )
        await reflector.run({})
        playbooks = get_playbooks("engineering", vault)
        assert any("high_revisions" in pb.title for pb in playbooks)

    @pytest.mark.asyncio
    async def test_detects_tool_errors(self, reflector, outcome_store, vault):
        _record_outcomes(
            outcome_store,
            n=5,
            department="engineering",
            success=False,
            tool_errors=["timeout", "connection refused"],
        )
        await reflector.run({})
        playbooks = get_playbooks("engineering", vault)
        assert any("tool_errors" in pb.title for pb in playbooks)

    @pytest.mark.asyncio
    async def test_playbook_tagged_correctly(self, reflector, outcome_store, vault):
        _record_outcomes(outcome_store, n=5, department="engineering", success=False)
        await reflector.run({})
        playbooks = get_playbooks("engineering", vault)
        for pb in playbooks:
            assert PLAYBOOK_TAG in pb.tags
            assert f"{PLAYBOOK_TAG}/engineering" in pb.tags

    @pytest.mark.asyncio
    async def test_playbook_contains_evidence(self, reflector, outcome_store, vault):
        _record_outcomes(outcome_store, n=5, department="engineering", success=False)
        await reflector.run({})
        playbooks = get_playbooks("engineering", vault)
        assert len(playbooks) >= 1
        assert "Evidence:" in playbooks[0].content

    @pytest.mark.asyncio
    async def test_returns_summary(self, reflector, outcome_store):
        _record_outcomes(outcome_store, n=5, department="engineering", success=False)
        result = await reflector.run({})
        assert "Reflected on" in result["result"]
        assert "playbook notes" in result["result"]
