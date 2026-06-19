---
name: phase1-audit-patterns
description: Vulnerability patterns and secure coding conventions established during Phase 1 security audit of tools/ and brain/ layers
metadata:
  type: project
---

Phase 1 introduced BashTool, FileTool, WebTool, ObsidianVault, QdrantStore, and the permission gate. Key security patterns to verify in future phases:

1. **BashTool uses create_subprocess_shell** -- command injection is by-design (shell=True equivalent). The only defense is the permission gate (Permission.SHELL). Any call site that bypasses execute_with_gate is a critical vulnerability.

2. **FileTool path traversal defense** -- uses both ".." part check AND resolve() + is_relative_to(). Correctly handles symlinks. The allowed_root defaults to "." (cwd) which is dangerous in production.

3. **WebTool SSRF defense** -- DNS-then-check pattern (resolves hostname, then checks all IPs). Disables redirects. Blocks private/loopback/link-local/reserved/multicast. TOCTOU gap exists between _check_url and httpx.request (DNS rebinding). No URL re-check after redirect (mitigated by follow_redirects=False).

4. **ObsidianVault path traversal defense** -- sanitizes title with regex removing non-word chars, checks ".." in raw title, resolves and validates against vault_path. Defense is adequate.

5. **Permission gate is opt-in** -- tools can be called directly via tool.execute() without going through execute_with_gate(). The gate is NOT enforced at the Tool base class level.

6. **BashTool does not log the command** -- only logs timeout value. Destructive commands leave no audit trail.

7. **WebTool permission is READ** -- HTTP requests (including POST/PUT/DELETE) are auto-approved without guardian check.

**Why:** These patterns define the attack surface. Future phases (daemon, dashboard, integrations) must not introduce new paths that bypass these gates.

**How to apply:** Every future audit must grep for direct tool.execute() calls bypassing execute_with_gate, and verify new HTTP-making code goes through WebTool, not raw httpx/requests.
