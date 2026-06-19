---
name: project-phase4-review
description: Phase 4 architectural review findings — Guardian if-elif dispatch, Reflector layer violation (brain imports core.state), Guardian not Agent-protocol-compliant
metadata:
  type: project
---

Phase 4 review conducted 2026-06-12. Key findings:

1. **Guardian if-elif dispatch on Permission enum** (agents/guardian.py:93-119) — same pattern as [[project-filetool-if-elif-dispatch]]. Should use a registry/dict mapping.

2. **brain/reflector.py imports core.state.AgentState** — brain layer importing from core (orchestration) layer is an upward dependency violation. See [[project-layer-violation-telemetry]] for the telemetry exemption precedent; no such exemption exists for core.state.

3. **Guardian does not implement Agent protocol** — no `async def run(self, state: AgentState)` method. It sits in agents/ but is not an Agent. Architectural intent may be that Guardian is a utility, but the "one class = one agent" rule in CLAUDE.md applies to everything in agents/.

4. **Agents (architect.py, scout.py) import directly from brain.playbook** — agents layer reaching to brain layer. Per the 7-layer hierarchy (Agents -> Tools -> Memory/Brain), agents should not skip the tools layer to reach brain. However, brain/librarian.py was the established read-before-act pattern from Phase 1. This is a pre-existing pattern that may need a recorded decision.

**Why:** These are the same categories of violations seen in Phase 2 (FileTool if-elif, orchestrator keyword dispatch). If not addressed, they compound as departments scale.

**How to apply:** Flag these during Phase 4 exit gate verification. The Guardian if-elif is the highest-priority fix (clear rule 3 violation). The Reflector importing core.state needs an ADR if intentional.
