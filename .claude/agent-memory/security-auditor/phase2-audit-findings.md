---
name: phase2-audit-findings
description: Phase 2 audit findings -- asyncio.run deadlock risk, no error handling, XSS in output strings, thread-unsafe globals, unvalidated graph registration
metadata:
  type: project
---

Phase 2 (Spine + Engineering department) introduced: core/dispatcher.py, core/orchestrator.py, core/graph.py, core/checkpointer.py, and agents/departments/engineering/* (architect, scaffolder, code_doctor, graph, __init__).

Key findings:

1. **asyncio.run() in _make_node** (engineering/graph.py:18) -- will deadlock/crash when running inside an existing event loop (Phase 5 FastAPI). Medium severity.

2. **Zero error handling** -- no try/except in any Phase 2 file. Unhandled exceptions crash the full graph invocation. Medium severity.

3. **Unsanitized request echoed in output** -- raw user input interpolated into result strings at multiple sites. Stored XSS risk when Phase 5 renders these. Low now, Medium at Phase 5.

4. **Global mutable state without locks** -- _department_graphs, _checkpointer, _registry all race-prone under concurrency. Medium severity for Phase 3/5.

5. **register_department_graph accepts any object** -- no type guard on compiled_graph parameter. Low severity.

6. **_select_department defaults to "engineering"** -- unrecognized input routes to engineering rather than being rejected. Privilege escalation risk grows with more departments in Phase 7.

7. **MemorySaver has no eviction** -- unbounded memory growth possible. OOM DoS risk.

Positive: MAX_REVISIONS=3 correctly enforced, no eval/exec/subprocess, no secrets, no deserialization, agents do not call tools directly (gate not bypassed).

**Why:** These patterns will compound in Phase 3 (daemon), Phase 5 (dashboard/FastAPI), and Phase 7 (more departments). The asyncio and thread-safety issues are dormant now but will become exploitable under concurrent load.

**How to apply:** In Phase 3+ audits, verify: (1) async compatibility fixed, (2) error handling added around graph.invoke(), (3) output encoding added before dashboard rendering, (4) locking on globals or immutable-after-init pattern adopted. See also [[phase1-audit-patterns]] [[permission-gate-arch]].
