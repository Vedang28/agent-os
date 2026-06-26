import pytest

from agents.departments.engineering.architect import Architect
from agents.guardian import (
    Guardian,
    KillSwitchError,
    _reset_approval_callback_for_testing,
    guardian_permission_checker,
    is_killed,
    set_approval_callback,
)
from brain.obsidian import ObsidianVault
from brain.outcome import Outcome, OutcomeStore
from brain.playbook import get_playbooks
from brain.reflector import Reflector
from tools.base import Permission, Tool, set_permission_checker


class FakeShellTool(Tool):
    name = "test_shell"
    permission = Permission.SHELL

    async def _run(self, **kwargs) -> str:
        return "executed"


class FakeDestructiveTool(Tool):
    name = "test_destructive"
    permission = Permission.DESTRUCTIVE

    async def _run(self, **kwargs) -> str:
        return "destroyed"


@pytest.fixture(autouse=True)
def cleanup():
    _reset_approval_callback_for_testing()
    set_approval_callback(lambda a, d: True)
    Guardian(timeout=1.0).reset_kill_switch()
    _reset_approval_callback_for_testing()
    set_permission_checker(None)
    yield
    _reset_approval_callback_for_testing()
    set_approval_callback(lambda a, d: True)
    Guardian(timeout=1.0).reset_kill_switch()
    _reset_approval_callback_for_testing()
    set_permission_checker(None)


@pytest.fixture()
def vault(tmp_path):
    return ObsidianVault(tmp_path / "vault")


@pytest.fixture()
def outcome_store(vault):
    return OutcomeStore(vault)


@pytest.fixture()
def reflector(vault, outcome_store):
    return Reflector(obsidian=vault, outcome_store=outcome_store)


@pytest.fixture()
def guardian():
    return Guardian(timeout=1.0)


class TestLearningLoopIntegration:
    @pytest.mark.asyncio
    async def test_end_to_end_reflection(self, reflector, outcome_store, vault):
        for i in range(6):
            outcome_store.record(
                Outcome(
                    task_id=f"task-{i}",
                    department="engineering",
                    success=False,
                    revisions=2,
                    timestamp=f"2026-01-01T{i:02d}:00:00+00:00",
                )
            )
        await reflector.run({})
        playbooks = get_playbooks("engineering", vault)
        assert len(playbooks) >= 1

    @pytest.mark.asyncio
    async def test_proposer_reads_playbooks(self, reflector, outcome_store, vault):
        for i in range(6):
            outcome_store.record(
                Outcome(
                    task_id=f"task-{i}",
                    department="engineering",
                    success=False,
                    timestamp=f"2026-01-01T{i:02d}:00:00+00:00",
                )
            )
        await reflector.run({})

        architect = Architect(librarian=None, obsidian=vault)
        result = await architect.run({"request": "build auth"})
        assert len(result["brain_context"]) >= 1

    @pytest.mark.asyncio
    async def test_measurable_improvement(self, reflector, outcome_store, vault):
        architect_no_playbook = Architect(librarian=None, obsidian=vault)
        result_before = await architect_no_playbook.run({"request": "build feature"})
        context_before = result_before["brain_context"]

        for i in range(6):
            outcome_store.record(
                Outcome(
                    task_id=f"task-{i}",
                    department="engineering",
                    success=False,
                    revisions=3,
                    timestamp=f"2026-01-01T{i:02d}:00:00+00:00",
                )
            )
        await reflector.run({})

        architect_with_playbook = Architect(librarian=None, obsidian=vault)
        result_after = await architect_with_playbook.run({"request": "build feature"})
        context_after = result_after["brain_context"]

        assert len(context_after) > len(context_before)
        assert result_after["draft"]


class TestGuardianIntegration:
    @pytest.mark.asyncio
    async def test_shell_blocked_without_approval(self, guardian):
        set_approval_callback(lambda a, d: False)
        checker = guardian_permission_checker(guardian)
        set_permission_checker(checker)
        tool = FakeShellTool()
        with pytest.raises(PermissionError):
            await tool.execute()

    @pytest.mark.asyncio
    async def test_destructive_blocked_without_approval(self, guardian):
        set_approval_callback(lambda a, d: False)
        checker = guardian_permission_checker(guardian)
        set_permission_checker(checker)
        tool = FakeDestructiveTool()
        with pytest.raises(PermissionError):
            await tool.execute()

    @pytest.mark.asyncio
    async def test_shell_allowed_with_approval(self, guardian):
        set_approval_callback(lambda a, d: True)
        checker = guardian_permission_checker(guardian)
        set_permission_checker(checker)
        tool = FakeShellTool()
        result = await tool.execute()
        assert result == "executed"

    def test_kill_switch_stops_operations(self, guardian):
        guardian.kill()
        assert is_killed()
        with pytest.raises(KillSwitchError):
            guardian.check_permission(FakeShellTool())
