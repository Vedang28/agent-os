import pytest

from agents.guardian import (
    Guardian,
    KillSwitchError,
    PermissionDeniedError,
    _reset_approval_callback_for_testing,
    guardian_permission_checker,
    install_guardian,
    is_killed,
    set_approval_callback,
)
from tools.base import Permission, Tool, set_permission_checker


class FakeReadTool(Tool):
    name = "read_tool"
    permission = Permission.READ

    async def _run(self, **kwargs) -> str:
        return "read result"


class FakeWriteTool(Tool):
    name = "write_tool"
    permission = Permission.WRITE

    async def _run(self, **kwargs) -> str:
        return "write result"


class FakeShellTool(Tool):
    name = "shell_tool"
    permission = Permission.SHELL

    async def _run(self, **kwargs) -> str:
        return "shell result"


class FakeDestructiveTool(Tool):
    name = "destructive_tool"
    permission = Permission.DESTRUCTIVE

    async def _run(self, **kwargs) -> str:
        return "destructive result"


@pytest.fixture(autouse=True)
def reset_guardian():
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
def guardian():
    return Guardian(timeout=1.0)


class TestCheckPermission:
    def test_read_allowed(self, guardian):
        decision = guardian.check_permission(FakeReadTool())
        assert decision.allowed is True
        assert not decision.requires_approval

    def test_read_logged(self, guardian):
        guardian.check_permission(FakeReadTool())
        assert len(guardian.audit_log) == 1
        assert guardian.audit_log[0]["tool"] == "read_tool"

    def test_write_allowed_with_audit(self, guardian):
        decision = guardian.check_permission(FakeWriteTool())
        assert decision.allowed is True
        assert len(guardian.audit_log) == 1
        assert guardian.audit_log[0]["permission"] == "write"

    def test_shell_requires_approval(self, guardian):
        decision = guardian.check_permission(FakeShellTool())
        assert decision.allowed is False
        assert decision.requires_approval is True

    def test_destructive_requires_approval(self, guardian):
        decision = guardian.check_permission(FakeDestructiveTool())
        assert decision.allowed is False
        assert decision.requires_approval is True


class TestRequestApproval:
    def test_approval_granted(self, guardian):
        set_approval_callback(lambda action, details: True)
        result = guardian.request_approval("test action")
        assert result is True
        assert any(
            e.get("type") == "approval_request" and e["approved"] is True
            for e in guardian.audit_log
        )

    def test_approval_denied(self, guardian):
        set_approval_callback(lambda action, details: False)
        result = guardian.request_approval("test action")
        assert result is False

    def test_no_callback_defaults_to_deny(self, guardian):
        result = guardian.request_approval("test action")
        assert result is False


class TestKillSwitch:
    def test_kill_sets_flag(self, guardian):
        assert not is_killed()
        guardian.kill()
        assert is_killed()

    def test_kill_logged(self, guardian):
        guardian.kill()
        assert any(e.get("type") == "kill_switch" for e in guardian.audit_log)

    def test_kill_blocks_permission_check(self, guardian):
        guardian.kill()
        with pytest.raises(KillSwitchError):
            guardian.check_permission(FakeReadTool())

    def test_cost_ceiling_breach(self, guardian):
        guardian.cost_ceiling_breach(tokens_used=10_000, ceiling=5_000)
        assert is_killed()

    def test_cost_ceiling_no_breach(self, guardian):
        guardian.cost_ceiling_breach(tokens_used=1_000, ceiling=5_000)
        assert not is_killed()

    def test_time_ceiling_breach(self, guardian):
        guardian.time_ceiling_breach(elapsed=600.0, ceiling=300.0)
        assert is_killed()

    def test_time_ceiling_no_breach(self, guardian):
        guardian.time_ceiling_breach(elapsed=100.0, ceiling=300.0)
        assert not is_killed()

    def test_reset_kill_switch(self, guardian):
        guardian.kill()
        assert is_killed()
        set_approval_callback(lambda a, d: True)
        guardian.reset_kill_switch()
        assert not is_killed()

    def test_reset_kill_switch_denied(self, guardian):
        guardian.kill()
        assert is_killed()
        set_approval_callback(lambda a, d: False)
        guardian.reset_kill_switch()
        assert is_killed()

    def test_reset_kill_switch_logged(self, guardian):
        guardian.kill()
        set_approval_callback(lambda a, d: True)
        guardian.reset_kill_switch()
        assert any(e.get("type") == "kill_switch_reset" for e in guardian.audit_log)


class TestAuditTrail:
    def test_all_checks_logged(self, guardian):
        guardian.check_permission(FakeReadTool())
        guardian.check_permission(FakeWriteTool())
        guardian.check_permission(FakeShellTool())
        guardian.check_permission(FakeDestructiveTool())
        assert len(guardian.audit_log) == 4
        perms = [e["permission"] for e in guardian.audit_log]
        assert perms == ["read", "write", "shell", "destructive"]


class TestGuardianPermissionChecker:
    def test_read_tool_passes(self, guardian):
        checker = guardian_permission_checker(guardian)
        assert checker(FakeReadTool()) is True

    def test_shell_tool_denied_without_approval(self, guardian):
        set_approval_callback(lambda a, d: False)
        checker = guardian_permission_checker(guardian)
        assert checker(FakeShellTool()) is False

    def test_shell_tool_approved(self, guardian):
        set_approval_callback(lambda a, d: True)
        checker = guardian_permission_checker(guardian)
        assert checker(FakeShellTool()) is True

    def test_destructive_tool_denied_without_approval(self, guardian):
        set_approval_callback(lambda a, d: False)
        checker = guardian_permission_checker(guardian)
        assert checker(FakeDestructiveTool()) is False


class TestInstallGuardian:
    @pytest.mark.asyncio
    async def test_install_wires_permission_checker(self, guardian):
        set_approval_callback(lambda a, d: False)
        install_guardian(guardian)
        tool = FakeShellTool()
        with pytest.raises(PermissionError):
            await tool.execute()

    @pytest.mark.asyncio
    async def test_install_allows_read(self, guardian):
        install_guardian(guardian)
        tool = FakeReadTool()
        result = await tool.execute()
        assert result == "read result"


class TestFrozenCallback:
    def test_freeze_prevents_change(self):
        _reset_approval_callback_for_testing()
        set_approval_callback(lambda a, d: False, freeze=True)
        set_approval_callback(lambda a, d: True)
        guardian = Guardian(timeout=1.0)
        result = guardian.request_approval("test")
        assert result is False
