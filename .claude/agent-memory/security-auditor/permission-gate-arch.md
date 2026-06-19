---
name: permission-gate-arch
description: Permission gate is opt-in at call sites -- tools can be invoked directly without gate checks, which is an architectural gap
metadata:
  type: project
---

The permission gate (tools/permissions.py) works as follows:
- AUTO_APPROVED: {READ, WRITE} -- auto-approved without guardian
- SHELL, DESTRUCTIVE -- rejected by default_checker, require custom checker (guardian)
- execute_with_gate() wraps tool.execute() with a permission check
- BUT: nothing in the Tool base class enforces that execute() can only be called via execute_with_gate()

This means any agent or graph node that calls `tool.execute()` directly bypasses the gate entirely. The gate is advisory, not enforced.

**Why:** This is the single most important architectural gap. If the daemon (Phase 3) or any integration (Phase 6) calls tool.execute() directly, all permission gates are void.

**How to apply:** In Phase 2+ audits, grep for `.execute(` calls that don't go through `execute_with_gate`. Recommend moving the gate check into Tool.execute() itself (template method pattern) so it cannot be bypassed. See also [[phase1-audit-patterns]].
