---
name: phase2-orchestrator-keyword-dispatch
description: Orchestrator uses keyword-in-loop pattern to select departments — borderline if-elif violation, but acceptable as a routing heuristic at the orchestration layer
metadata:
  type: project
---

`core/orchestrator.py:15-20` iterates over `_DEPARTMENT_KEYWORDS` dict and returns the first department whose keyword matches the request. This is structurally similar to if-elif dispatch (rule 3), but uses a data-driven dict rather than hardcoded branches.

**Why:** Rule 3 exists to prevent closed routing that requires editing existing code to add new routes. Here the dict is still inside the orchestrator, so adding a department requires editing `_DEPARTMENT_KEYWORDS`. The Open/Closed principle says "add a department without editing the orchestrator."

**How to apply:** Flag as a minor concern for now (Phase 2 is first-department proof-of-concept). By Phase 7 (mass-produce departments), this MUST be replaced with a proper routing strategy — either the department registry declares its own keywords, or an LLM classifier routes requests. Related: [[filetool-if-elif-dispatch]].
