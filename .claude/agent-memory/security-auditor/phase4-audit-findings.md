---
name: phase4-audit-findings
description: Phase 4 audit -- Guardian bypass paths, kill switch unenforceable, audit log volatile, tool_errors XSS, approval callback hijackable
metadata:
  type: project
---

Phase 4 (Learning loop + Guardian) introduced: brain/outcome.py, brain/reflector.py, brain/playbook.py, agents/guardian.py, and updated architect.py + scout.py.

Key findings:

1. **Guardian not wired in production** -- guardian_permission_checker() is defined but never passed to set_permission_checker(). The _active_checker remains None, so Tool.execute() skips all permission checks. The Guardian is dead code in production.

2. **Kill switch has no effect on daemon** -- daemon.py never calls is_killed(). Even after Guardian.kill(), the daemon continues running all jobs. Kill switch only blocks check_permission(), which is itself unwired.

3. **reset_kill_switch() has no access control or audit trail** -- any code that imports Guardian can call the static method to disable the kill switch. No authentication, no audit log entry, no confirmation required.

4. **Audit log is volatile (in-memory list)** -- _audit_log is a Python list that vanishes on restart. Not persisted to disk, not append-only. Any code with a reference to the Guardian instance can access guardian._audit_log directly and modify/clear it.

5. **_approval_callback is a hijackable global** -- set_approval_callback() accepts any callable with no type checking. A malicious agent can replace it with `lambda a,d: True` to auto-approve DESTRUCTIVE actions.

6. **tool_errors sanitization is insufficient for XSS** -- only truncates and strips null bytes. HTML/JS content passes through to Obsidian notes and playbook content. Dashboard rendering (Phase 5) would be vulnerable.

7. **department field is unvalidated** -- free-form string flows into note tags, log messages, and playbook content without validation against an allowlist.

Positive: No eval/exec/subprocess, no secrets, no pickle/unsafe deserialization, ObsidianVault path traversal defense covers note writes, Pydantic model validation on Outcome fields.

**Why:** The Guardian is the central security mechanism for the entire system. Its current implementation has multiple bypass paths that undermine the permission gate architecture.

**How to apply:** Phase 5+ audits must verify: (1) guardian_permission_checker wired as active checker, (2) daemon checks is_killed(), (3) audit log persisted to disk, (4) reset_kill_switch requires authentication. See also [[permission-gate-arch]] [[phase1-audit-patterns]] [[phase2-audit-findings]].
