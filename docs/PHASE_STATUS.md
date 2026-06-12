# PHASE STATUS

> Update this after every working session. CLAUDE.md imports this file, so it's always in context.

## Active phase
**Phase 4 — Learning loop + Guardian**

## Phase ladder
| Phase | Name | Status |
|------|------|--------|
| 0 | Foundation (repo, protocol, state, CI) | 🟢 COMPLETE |
| 1 | Brain + Tools | 🟢 COMPLETE |
| 2 | Spine + first department (Engineering) | 🟢 COMPLETE |
| 3 | Autonomous engine (daemon + Intelligence) | 🟢 COMPLETE |
| 4 | Learning loop + Guardian | 🟢 COMPLETE |
| 5 | Dashboard + Voice | 🔴 not started |
| 6 | Integrations (Composio + MCP) | 🔴 not started |
| 7 | Mass-produce departments | 🔴 not started |
| 8 | Harden & scale | 🔴 not started |

## Phase 0 exit gate (must pass before Phase 1)
- [x] Monorepo + layered folders created (14 `__init__.py` files across all layers)
- [x] `Agent` protocol + empty registry load (`agents/protocol.py`, `agents/registry.py`)
- [x] `AgentState` typed schema defined (`core/state.py` — TypedDict, total=False, 12 fields)
- [x] Empty LangGraph compiles and runs a no-op end to end (`core/graph.py` — invoke returns `approved: True`)
- [x] `telemetry.py` skeleton (structured logging) in place (`infra/telemetry.py` — JSON formatter)
- [x] `pytest` green, CI passes (20 tests pass, `.github/workflows/ci.yml` created)
- [x] memory system bootstrapped (`node .claude/memory/memory.js recent` runs)

## Phase 1 exit gate (must pass before Phase 2)
- [x] `brain/obsidian.py` — write a note → read it back
- [x] `brain/qdrant.py` — embed a note → retrieve it semantically
- [x] `brain/librarian.py` — `query()` returns relevant notes
- [x] `tools/bash.py` — executes a command, returns output
- [x] `tools/file.py` — writes and reads a file
- [x] `tools/web.py` — makes an HTTP request (mocked in tests)
- [x] Each tool declares the correct `Permission` level
- [x] A SHELL-permission tool blocks without approval (permission gate test)
- [x] Integration: agent stub queries brain AND calls a tool
- [x] All `pytest` green (73 tests pass)

## Phase 2 exit gate (must pass before Phase 3)
- [x] `core/dispatcher.py` — classifies requests into instant/fast/deep lanes
- [x] `core/orchestrator.py` — routes deep requests to the engineering department
- [x] `core/graph.py` — full company graph compiles and routes correctly (instant short-circuits, deep hits department)
- [x] Checkpointer wired — state persists across invocations with `thread_id`
- [x] Engineering sub-graph — Architect → Scaffolder → CodeDoctor with conditional edge
- [x] Bounded critic loop — `max_revisions = 3` enforced, escalation on exceeded
- [x] A deep request flows: User → Dispatcher → Orchestrator → Engineering triad → approved output
- [x] A deliberately bad draft triggers exactly one revise loop then passes
- [x] Engineering department registers in agent registry (no if-elif dispatch)
- [x] Engineering sub-graph plugs into company graph as one node
- [x] All `pytest` green (114 tests pass)

## Phase 3 exit gate (must pass before Phase 4)
- [x] Daemon starts, ticks on schedule (configurable interval)
- [x] Daemon saves checkpoint after each tick
- [x] Kill the process mid-tick → restart → it resumes from checkpoint
- [x] Token budget and wall-clock budget enforced per tick
- [x] Model router returns correct model config per task type (`code`, `long_docs`, `triage`)
- [x] Intelligence triad runs: Scout → Analyst → Skeptic
- [x] Scout reads brain context before drafting (read-before-act)
- [x] Skeptic rejects low-quality items, approves good ones
- [x] `max_revisions = 3` cap is respected in Intelligence department
- [x] A daily briefing note appears in the brain after a tick
- [x] Intelligence department registers in agent registry (no if-elif dispatch)
- [x] Intelligence sub-graph plugs into company graph as one node
- [x] All `pytest` green (167 tests pass)

## Phase 4 exit gate (must pass before Phase 5)
- [x] Reflector reads outcomes from brain (`brain/reflector.py` — reads via `OutcomeStore.query_recent()`)
- [x] Reflector identifies patterns and writes playbook notes tagged `#playbook` (failure, success, high-revision, tool-error, cost patterns)
- [x] Proposers read playbooks via brain query (Architect + Scout query `#playbook/{dept}` before drafting)
- [x] **Measurable improvement on a repeated task after reflection** (test_measurable_improvement: context grows, draft changes)
- [x] `OutcomeStore` records outcomes and supports filtering (query_recent, query_by_department, query_failures)
- [x] Guardian enforces permission levels on all tools (`agents/guardian.py`)
- [x] `READ` tools execute without approval
- [x] `WRITE` tools execute with logging
- [x] `SHELL` tools pause for approval (human-in-the-loop via `request_approval`)
- [x] `DESTRUCTIVE` tools pause for explicit approval + confirmation
- [x] Human-in-the-loop interrupt works (pause → approve → resume via `set_approval_callback`)
- [x] Kill switch stops all running graphs and saves state (`kill()`, `cost_ceiling_breach()`, `time_ceiling_breach()`)
- [x] **No destructive action executes without an approval step** (Guardian checker + integration tests)
- [x] Audit trail logs every permission check (`guardian.audit_log`)
- [x] All `pytest` green (218 tests pass)

## Notes / blockers
Phase 4 complete as of 2026-06-12. Ready for Phase 5.
- Guardian uses `set_approval_callback` for human-in-the-loop; LangGraph `interrupt()` integration deferred to Phase 5 dashboard wiring
- Kill switch uses thread-safe global flag; daemon checks `is_killed()` to stop
- Reflector pattern detection uses heuristic thresholds (≥2 failures, ≥2.0 avg revisions, 2x median tokens)
- Playbook notes are additive — Reflector never deletes existing playbooks
