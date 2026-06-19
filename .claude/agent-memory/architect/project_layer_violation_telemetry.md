---
name: layer-violation-telemetry-crosscut
description: Telemetry (infra layer 7) is imported directly by brain (layer 5) and tools (layer 4), skipping intermediate layers — a recurring cross-cutting concern pattern
metadata:
  type: project
---

Both brain/ and tools/ import `infra.telemetry.get_logger` directly, which technically violates the strict "call only the layer directly below" rule. Layers 4 (tools) and 5 (brain) both skip down to layer 7 (infra).

**Why:** Telemetry is a cross-cutting concern. Enforcing strict layering would require wrapping `get_logger` at every intermediate layer, which adds indirection with no value.

**How to apply:** When reviewing for layer violations, treat telemetry/logging as an architectural exception — flag it but don't block on it. However, if non-telemetry infra imports (daemon, checkpointer, model_router) appear in brain or tools, those ARE genuine violations and should be blocked. This precedent should be formally recorded as an ADR if the team agrees.
