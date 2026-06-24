---
name: phase8-review
description: Phase 8 (Harden & Scale) architectural review findings — lane_analyzer upward import, checkpointer/cost_tracker need ADR
metadata:
  type: project
---

Phase 8 review completed 2026-06-24.

**Blocking:** `infra/lane_analyzer.py:23` imports `core.dispatcher.assign_lane` — upward dependency from bottom to near-top layer. Needs fix (DI or relocation to core/).

**ADR needed:** `core/checkpointer.py` now delegates to `infra/checkpointer.py`, and `core/graph.py:70` imports `infra.cost_tracker`. Both are core→infra skips following the telemetry precedent but lack a recorded ADR.

**Minor:** `infra/checkpointer.py:34-59` uses if-elif on backend string (3 cases). Low severity but doesn't match registry pattern.

**Why:** These patterns, if unrecorded, set implicit precedents that erode the layer rule over time.

**How to apply:** When reviewing future infra modules imported by core, check whether they have ADR coverage. Flag any new infra→core (upward) imports immediately.

See also: [[phase6-layer-violations]], [[layer-violation-telemetry]]
