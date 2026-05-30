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

## 2026-05-29 14:42 — Unified agent-os: one product for all users
No separate dev edition. One agent-os serves developers, marketers, engineers, sales — everyone. Claude Code workflow patterns (subagents, workflows, agent view, worktrees, persistent memory) are implemented INSIDE agent-os runtime so every user gets the full parallel orchestration experience. The daemon, brain, reflector, guardian, voice, and dashboard are what make it more than Claude Code.
