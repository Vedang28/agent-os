# Development Workflow

> How to build agent-os phase by phase using Claude Code's parallel tooling.

## The Loop (every phase)

```
┌─────────────────────────────────────────────────────┐
│                   YOU (operator)                     │
│  Pick a phase prompt from prompts/phase-N-*.md      │
│  Choose how to run it ↓                             │
└──────────┬──────────────┬───────────────┬───────────┘
           │              │               │
     Option A        Option B        Option C
   Single Session    Workflow      Agent View
   (paste prompt)   (fan-out)    (parallel sessions)
           │              │               │
           ▼              ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│ One Claude   │  │ Orchestrated │  │ claude agents     │
│ does it all  │  │ subagents    │  │                   │
│ sequentially │  │ in parallel  │  │ @spine-builder ─┐ │
│              │  │              │  │ @edge-builder ──┤ │
│              │  │              │  │   (worktrees)   │ │
└──────┬───────┘  └──────┬───────┘  └────────┬────────┘
       │                 │                    │
       └────────┬────────┘────────────────────┘
                ▼
     ┌─────────────────────┐
     │  @gate-checker      │
     │  Verifies exit gate │
     │  (real checks, not  │
     │   self-grading)     │
     └─────────┬───────────┘
               │
          PASS? ──No──→ Fix and re-run
               │
              Yes
               │
         ┌─────▼──────┐
         │  /log       │
         │  Next phase │
         └─────────────┘
```

## Concrete Example: Running Phase 0

**Fastest path (Option C — Agent View):**

```
1. Open:       claude agents
2. Dispatch:   @spine-builder Build Phase 0: folders, Agent protocol, AgentState, LangGraph, telemetry
3. Dispatch:   @edge-builder Build Phase 0: folders, Tool base, Permission enum, tool registry
4. Watch both rows work (they're in separate worktrees, can't conflict)
5. When both finish:  @gate-checker Verify Phase 0 exit gate
6. Gate passes → /log → move to Phase 1
```

Phases 1–7 follow the same loop — just swap the prompt. Track A and Track B are always independent, always parallelizable.

## Three Execution Modes

| Mode | When to use | Speed | Token cost |
|------|------------|-------|------------|
| **Option A: Single session** | Simple phases, tight budget | Slowest | Lowest |
| **Option B: Workflow** | Fan-out tasks, research-heavy phases | Fast | Medium |
| **Option C: Agent view** | Any phase with Track A + Track B | Fastest | Highest |

**Option A — Single session:**
Copy the prompt from `prompts/phase-N-*.md` into a new Claude Code session. One agent does everything sequentially.

**Option B — Workflow:**
Say "Run a workflow to execute Phase N of agent-os" and Claude orchestrates subagents in parallel from a script.

**Option C — Agent view (recommended):**
Open `claude agents`, dispatch `@spine-builder` and `@edge-builder` as separate background sessions. Each gets its own git worktree so file edits can't conflict.

## Subagents Available

| Agent | Role | Model | Mode |
|-------|------|-------|------|
| `@spine-builder` | Track A: core, agents, brain, infra | Opus | Read/write, worktree |
| `@edge-builder` | Track B: tools, io, dashboard, integrations | Opus | Read/write, worktree |
| `@test-runner` | Runs pytest, diagnoses failures | Sonnet | Read-only |
| `@gate-checker` | Verifies exit gates with real commands | Sonnet | Read-only |
| `@architect` | Reviews designs against constraints | Opus | Read-only |

## Phase Map

| Phase | Prompt file | Track A (Spine) | Track B (Edges) |
|-------|------------|-----------------|-----------------|
| 0 | `phase-0-foundation.md` | Folders, protocol, state, graph, telemetry | Tool base, Permission enum, registry |
| 1 | `phase-1-brain-tools.md` | Brain: obsidian, qdrant, librarian | Tools: bash, file, web |
| 2 | `phase-2-spine-engineering.md` | Orchestrator, Dispatcher, checkpointer | Engineering: Architect/Scaffolder/CodeDoctor |
| 3 | `phase-3-daemon-intelligence.md` | Daemon heartbeat, model router | Intelligence: Scout/Analyst/Skeptic |
| 4 | `phase-4-learning-guardian.md` | Reflector (learning loop) | Guardian (permissions, kill switch) |
| 5 | `phase-5-dashboard-voice.md` | FastAPI + WebSocket backend | Voice STT/TTS + Next.js dashboard |
| 6 | `phase-6-integrations.md` | Composio bridge (OAuth) | Wire tools into departments |
| 7 | `phase-7-mass-departments.md` | Backend, DevOps, AI/ML divisions | Frontend, Growth, Sales/Ops divisions |
| 8 | `phase-8-harden-scale.md` | Evals, cost tracking, Postgres | Security audit, load test, lane tuning |

## What Changed (Before vs Now)

| Before | Now |
|--------|-----|
| One session does everything | Two builders work in parallel (worktree-isolated) |
| Self-check exit gates | Dedicated `@gate-checker` agent verifies independently |
| Only Phase 0 had a prompt | All 9 phases have detailed prompts with code examples |
| No permissions configured | `.claude/settings.json` pre-allows pytest, make, git, etc. |
| Manual track splitting | `@spine-builder` and `@edge-builder` know their layers |
| Builders learn nothing across sessions | Both builders have persistent project memory |

## TL;DR

Pick a phase prompt → dispatch spine-builder + edge-builder in parallel → gate-checker verifies → next phase. Repeat 9 times and you have agent-os running.
