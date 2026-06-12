import html
import threading
import time

from pydantic import BaseModel

from infra.telemetry import get_logger
from tools.base import Permission, Tool, set_permission_checker

logger = get_logger("agents.guardian")

_audit_logger = get_logger("agents.guardian.audit")


class PermissionDecision(BaseModel):
    allowed: bool
    reason: str
    requires_approval: bool = False


class PermissionDeniedError(Exception):
    pass


class KillSwitchError(Exception):
    pass


_killed = False
_killed_lock = threading.Lock()

_approval_callback = None
_approval_callback_frozen = False


def set_approval_callback(callback, *, freeze: bool = False):
    global _approval_callback, _approval_callback_frozen
    if _approval_callback_frozen:
        logger.warning("approval callback is frozen — ignoring set_approval_callback")
        return
    _approval_callback = callback
    if freeze:
        _approval_callback_frozen = True
        logger.info("approval callback frozen — cannot be changed again")


def _reset_approval_callback_for_testing():
    global _approval_callback, _approval_callback_frozen
    _approval_callback = None
    _approval_callback_frozen = False


def is_killed() -> bool:
    with _killed_lock:
        return _killed


def _set_killed(value: bool) -> None:
    global _killed
    with _killed_lock:
        _killed = value


class Guardian:
    name = "core.guardian"
    role = "safety"

    DEFAULT_TIMEOUT: float = 300.0

    def __init__(self, timeout: float | None = None):
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._audit_log: list[dict] = []

    @property
    def audit_log(self) -> list[dict]:
        return list(self._audit_log)

    def _log_audit(self, entry: dict) -> None:
        self._audit_log.append(entry)
        _audit_logger.info("audit: %s", entry)

    _PERMISSION_POLICY: dict[Permission, tuple[bool, bool, str]] = {
        Permission.READ: (True, False, "auto-approved"),
        Permission.WRITE: (True, False, "approved with audit trail"),
        Permission.SHELL: (False, True, "requires human approval"),
        Permission.DESTRUCTIVE: (False, True, "requires explicit human approval and confirmation"),
    }

    def check_permission(self, tool: Tool, args: dict | None = None) -> PermissionDecision:
        if is_killed():
            raise KillSwitchError("Kill switch is active — all operations blocked")

        entry = {
            "tool": tool.name,
            "permission": tool.permission.value,
            "args_keys": list((args or {}).keys()),
            "timestamp": time.time(),
        }

        policy = self._PERMISSION_POLICY.get(tool.permission)
        if policy is not None:
            allowed, requires_approval, reason_suffix = policy
            decision = PermissionDecision(
                allowed=allowed,
                reason=f"{tool.permission.value.upper()} tool '{tool.name}' {reason_suffix}",
                requires_approval=requires_approval,
            )
        else:
            decision = PermissionDecision(
                allowed=False,
                reason=f"Unknown permission level: {tool.permission}",
            )

        entry["decision"] = decision.allowed
        entry["requires_approval"] = decision.requires_approval
        entry["reason"] = decision.reason
        self._log_audit(entry)

        return decision

    def request_approval(self, action: str, details: dict | None = None) -> bool:
        logger.info("requesting approval for: %s", action)
        entry = {
            "action": action,
            "details": details or {},
            "timestamp": time.time(),
            "type": "approval_request",
        }

        if _approval_callback is not None:
            try:
                approved = _approval_callback(action, details or {})
            except Exception:
                approved = False
        else:
            approved = False

        entry["approved"] = approved
        self._log_audit(entry)

        logger.info("approval result for '%s': %s", action, approved)
        return approved

    def kill(self) -> None:
        logger.warning("KILL SWITCH ACTIVATED")
        _set_killed(True)
        self._log_audit({
            "type": "kill_switch",
            "timestamp": time.time(),
            "reason": "manual_kill",
        })

    def cost_ceiling_breach(self, tokens_used: int, ceiling: int) -> None:
        if tokens_used >= ceiling:
            logger.warning(
                "cost ceiling breach: %d >= %d tokens", tokens_used, ceiling
            )
            self._log_audit({
                "type": "kill_switch",
                "timestamp": time.time(),
                "reason": f"cost_ceiling_breach: {tokens_used} >= {ceiling}",
            })
            _set_killed(True)

    def time_ceiling_breach(self, elapsed: float, ceiling: float) -> None:
        if elapsed >= ceiling:
            logger.warning(
                "time ceiling breach: %.1fs >= %.1fs", elapsed, ceiling
            )
            self._log_audit({
                "type": "kill_switch",
                "timestamp": time.time(),
                "reason": f"time_ceiling_breach: {elapsed:.1f} >= {ceiling:.1f}",
            })
            _set_killed(True)

    def reset_kill_switch(self) -> None:
        if _approval_callback is not None:
            approved = _approval_callback(
                "Reset kill switch", {"type": "kill_switch_reset"}
            )
            if not approved:
                logger.warning("kill switch reset DENIED by approval callback")
                return
        _set_killed(False)
        self._log_audit({
            "type": "kill_switch_reset",
            "timestamp": time.time(),
        })
        logger.info("kill switch reset")


def guardian_permission_checker(guardian: Guardian):
    def checker(tool: Tool) -> bool:
        decision = guardian.check_permission(tool)
        if decision.requires_approval:
            approved = guardian.request_approval(
                f"Execute {tool.permission.value} tool: {tool.name}",
                {"tool": tool.name, "permission": tool.permission.value},
            )
            if not approved:
                return False
            return True
        return decision.allowed
    return checker


def install_guardian(guardian: Guardian) -> None:
    checker = guardian_permission_checker(guardian)
    set_permission_checker(checker)
    logger.info("guardian installed as active permission checker")


def sanitize_for_content(value: str) -> str:
    return html.escape(str(value)[:500])
