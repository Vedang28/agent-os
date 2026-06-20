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

## 2026-06-20 — Tool ABC and Permission are exempt from the strict layer rule
`tools.base.Tool` and `tools.base.Permission` are protocol/interface types that any tool-producing layer may import. The integrations layer produces Tool subclasses — this is dependency inversion (depending on an abstraction), not a concrete upward call. Same precedent as telemetry (ADR 2026-06-05). `tools.registry.register` may be called from integration wiring code for the same reason.

## 2026-06-20 — Dashboard API has direct read access to all service layers
The dashboard API (`io_layer/dashboard_api/routes.py`) is an administrative interface that accesses services from any layer via dependency injection (`set_services`). This is an accepted exception to the strict layer rule for dashboard routes only. Non-dashboard I/O code (voice, CLI) must still respect the layer rule.

## 2026-05-29 14:42 — Unified agent-os: one product for all users
No separate dev edition. One agent-os serves developers, marketers, engineers, sales — everyone. Claude Code workflow patterns (subagents, workflows, agent view, worktrees, persistent memory) are implemented INSIDE agent-os runtime so every user gets the full parallel orchestration experience. The daemon, brain, reflector, guardian, voice, and dashboard are what make it more than Claude Code.
