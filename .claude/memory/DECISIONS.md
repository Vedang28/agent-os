# DECISION RECORD (ADR)

> Append-only architectural decisions. Write via `/reflect` or `node .claude/memory/memory.js decide "<title>" "<why>"`.
> Once recorded, don't re-litigate. If a decision changes, add a new dated entry that supersedes the old one.

## 2026-05-29 — Orchestration framework: LangGraph
Chosen over AgentScope. Sub-graphs map to departments, conditional edges model the critic revise loop, and built-in checkpointing gives resume-after-restart for the daemon. AgentScope's multimodal/voice edge is kept at the I/O layer, outside the graph.

## 2026-05-29 — Brain: Obsidian + Qdrant
Obsidian markdown for the human-readable knowledge graph (backlinks), Qdrant for vector retrieval. Complementary, not competing.

## 2026-05-29 — Architecture: 7-layer, dependency points downward
I/O → Orchestration → Agents → Tools → Memory → Integrations → Infra. A layer may only call the layer directly below it. Agents call Tools, never raw subprocess.

## 2026-05-29 — Agent pattern: lead + proposer/worker/critic triad
Every department uses the triad. The critic can reject and send work back, bounded at max_revisions = 3. This is what gives human-like critical review.

## 2026-06-05 — Telemetry is exempt from the strict layer rule
`infra.telemetry.get_logger` may be imported by any layer. Logging is a cross-cutting concern; routing it through intermediate layers adds indirection with no value. All other `infra.*` modules (daemon, model_router, checkpointer) remain subject to the strict layer rule.

## 2026-05-29 14:42 — Unified agent-os: one product for all users
No separate dev edition. One agent-os serves developers, marketers, engineers, sales — everyone. Claude Code workflow patterns (subagents, workflows, agent view, worktrees, persistent memory) are implemented INSIDE agent-os runtime so every user gets the full parallel orchestration experience. The daemon, brain, reflector, guardian, voice, and dashboard are what make it more than Claude Code.

## 2026-06-12 15:28 — AgentState (core.state) is a cross-cutting contract type — any layer may import it, like infra.telemetry. It defines the typed interface between graph nodes and is not orchestration logic. Moving it to a shared module would be over-engineering for the current phase count.
(no rationale given)

## 2026-06-12 15:28 — Guardian lives in agents/ but is NOT an Agent-protocol class. It is safety infrastructure that gates tool execution. It does not participate in department triads or the graph as a node. This is intentional — forcing it into the Agent protocol would add complexity without value. If it needs to be a graph node later (Phase 5 dashboard), wrap it then.
(no rationale given)

## 2026-06-12 15:28 — Agents may import brain layer directly for read-before-act (librarian.query, get_playbooks). This is an established pattern from Phase 1, not a layer violation. The brain is a shared knowledge layer, not a service that must be routed through tools. Tools are for external side effects (shell, file, web), not internal knowledge queries.
(no rationale given)
