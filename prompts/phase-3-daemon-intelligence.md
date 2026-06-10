# Phase 3 — Autonomous Engine: Daemon + Intelligence (Complete Build Prompt)

> Paste this into a new Claude Code session to build Phase 3 of agent-os.

## Context

Phase 2 is complete. The orchestration spine (Dispatcher, Orchestrator, company StateGraph with lane routing) and the first department (Engineering triad: Architect → Scaffolder → CodeDoctor with bounded critic loop) are in place. The full flow works: user request → lane assignment → orchestration → department sub-graph → critic loop → approved output. 114 passing tests, CI green.

Phase 3 adds the **autonomous engine** — the daemon that makes agent-os run continuously without human initiation, and the **Intelligence department** that gives the system awareness of the outside world.

## What exists now

- `core/state.py` — `AgentState` TypedDict with 12 fields
- `core/graph.py` — full company StateGraph: START → Dispatcher → route_by_lane → (instant_response | orchestrator → department_node) → END
- `core/dispatcher.py` — lane classifier (instant/fast/deep) using keyword heuristics
- `core/orchestrator.py` — routes deep requests to departments, decomposes plans, reads brain context
- `core/checkpointer.py` — `get_checkpointer()` wrapping LangGraph `MemorySaver`
- `agents/protocol.py` — `Agent` Protocol with `name: str` and `async def run(state) -> AgentState`
- `agents/registry.py` — register/get/list_agents/clear (dict-based)
- `agents/security_gate.py` — `SecurityGate` ABC with `async def review(state) -> AgentState`
- `agents/departments/engineering/` — Architect, Scaffolder, CodeDoctor, sub-graph with conditional edge, MAX_REVISIONS=3
- `tools/base.py` — `Tool` ABC with `Permission` enum, permission checker, `execute()` gate
- `tools/permissions.py` — default checker (auto-approves READ/WRITE, blocks SHELL/DESTRUCTIVE)
- `tools/bash.py`, `tools/file.py`, `tools/web.py` — permission-gated tools
- `brain/schema.py` — `Note` Pydantic model
- `brain/obsidian.py` — Obsidian vault interface (write/read/list/backlinks)
- `brain/qdrant.py` — Qdrant vector store (embed/search, in-memory for tests)
- `brain/librarian.py` — `Librarian.query()` — semantic search + backlink enrichment
- `infra/telemetry.py` — `get_logger()` with JSON formatter

## Workflow to follow

STEP 1: /start-phase (load context, verify Phase 2 gate still passes)
STEP 2: PLAN — enter plan mode, design both tracks, get approval
STEP 3: BUILD Track A (Daemon + Model Router) + Track B (Intelligence department) — sequential or parallel
STEP 4: INSTALL — add any new deps (apscheduler or asyncio scheduling, feedparser for RSS), verify imports
STEP 5: TEST — write all tests, run pytest, fix until green
STEP 6: VERIFY (5-step verification protocol):
6a. @test-runner → all tests green
6b. @architect + /code-review high → no layer violations
6c. @security-auditor + /security-review → no injection, no secrets, no SSRF
6d. @gate-checker → all exit criteria pass with evidence
6e. Fix any failures → re-run from 6a
STEP 7: /log → commit → push

## How to run this phase

**Recommended — Parallel:**
```
claude agents
```
Dispatch:
1. `@spine-builder Build Phase 3 Track A: Daemon heartbeat loop, checkpoint persistence, resume-after-restart in /infra/daemon.py + model router in /infra/model_router.py`
2. `@edge-builder Build Phase 3 Track B: Intelligence department — Scout/Analyst/Skeptic triad in /agents/departments/intelligence/`

Merge test:
3. `@gate-checker Verify Phase 3 exit gate`

---

## What to build

### Track A — Daemon + Model Router (`/infra/`)

**`infra/daemon.py`** — Daemon heartbeat:

- `Daemon` class with configurable tick interval (default: 900 seconds / 15 min)
- `async def start()` — begins the heartbeat loop
- `async def tick()` — one daemon cycle:
  - Loads registered jobs (department sub-graphs to trigger)
  - Invokes each job through the company graph with checkpointing
  - Saves state after every tick via `get_checkpointer()`
  - Logs tick start/end/duration via `telemetry.get_logger()`
- `async def stop()` — graceful shutdown
  - Handles SIGTERM/SIGINT via `signal` module
  - Saves current state before exiting
  - Sets a `_running` flag to break the loop cleanly
- **Resume-after-restart:**
  - On startup, call `load_last_checkpoint()` to recover state
  - If a tick was interrupted mid-execution, resume from the last checkpoint
  - Uses `thread_id` per job for checkpoint isolation
- **Budgets per tick:**
  - `max_tokens_per_tick: int` (default: 100_000) — token ceiling
  - `max_wall_clock_per_tick: float` (default: 300.0) — seconds ceiling
  - If either limit is exceeded, the tick stops and logs a warning
- **Job registry:**
  - `register_job(name: str, graph: CompiledGraph, schedule: str)` — register a job to run on each tick
  - `list_jobs() -> list[str]` — list registered job names
  - Jobs are just compiled LangGraph graphs invoked with a trigger request

**`infra/model_router.py`** — Model routing:

- `ModelConfig(BaseModel)`: model_name, provider, api_base, max_tokens, temperature
- `route(task_type: str) -> ModelConfig` — returns the right model config per task:
  - `"code"` → Claude (provider: "anthropic")
  - `"long_docs"` → Gemini (provider: "google")
  - `"triage"` → local NIM/Ollama (provider: "local")
  - `"default"` → Claude (fallback)
- Config loaded from a dict (start simple, swap for YAML/env config later)
- `list_models() -> dict[str, ModelConfig]` — returns all configured routes
- `set_route(task_type: str, config: ModelConfig)` — override a route at runtime

---

### Track B — Intelligence Department (`/agents/departments/intelligence/`)

**`agents/departments/intelligence/__init__.py`** — Department registration:

- Import and register all three agents in the agent registry
- Export `build_intelligence_graph` for the company graph to use

**`agents/departments/intelligence/scout.py`** — Scout (proposer):

- Implements `Agent` protocol
- `name = "intelligence.scout"`
- `role = "proposer"`
- `async def run(self, state: AgentState) -> AgentState`:
  - **Read-before-act**: queries the brain (`Librarian().query()`) for recently reported items to avoid duplicates
  - Stores brain results in `state["brain_context"]`
  - Scans sources (in Phase 3: stubbed source list — HN, GitHub trending, RSS)
  - In Phase 3 the scan is heuristic (returns mock/template items), real web fetching comes when WebTool is wired
  - Produces `state["draft"]` — a list of interesting items with summaries
  - Each item: `{"title": str, "source": str, "summary": str, "url": str, "relevance": str}`

**`agents/departments/intelligence/analyst.py`** — Analyst (worker):

- Implements `Agent` protocol
- `name = "intelligence.analyst"`
- `role = "worker"`
- `async def run(self, state: AgentState) -> AgentState`:
  - Takes `state["draft"]` (Scout's item list)
  - Cross-references each item with brain knowledge via `Librarian().query()`
  - Produces a structured briefing note:
    ```python
    {
        "title": "Daily Briefing — {date}",
        "items": [...],
        "cross_references": [...],
        "actionable_insights": [...]
    }
    ```
  - Writes the briefing to the brain via `brain/obsidian.py` — `write_note()` with tag `#briefing`
  - Sets `state["result"]` to the serialized briefing

**`agents/departments/intelligence/skeptic.py`** — Skeptic (critic):

- Implements `Agent` protocol
- `name = "intelligence.skeptic"`
- `role = "critic"`
- `async def run(self, state: AgentState) -> AgentState`:
  - Reviews `state["result"]` (the briefing) for quality:
    - Rejects items already in the brain (duplicate check)
    - Rejects low-signal items (too short, no actionable insight)
    - Rejects items with missing sources
  - Approval logic:
    - All items pass quality checks → `state["approved"] = True`
    - Any item fails → `state["approved"] = False`, `state["critique"]` with reasons, `state["revisions"]` incremented
  - **Bounded**: `max_revisions = 3`, then escalate

**`agents/departments/intelligence/graph.py`** — Intelligence sub-graph:

- Builds a LangGraph `StateGraph` for the Intelligence department:
  ```
  START → scout → analyst → skeptic → route_decision
    - approved → END
    - revise → analyst (loop back)
    - max_revisions_hit → escalate → END
  ```
- `MAX_REVISIONS = 3` (module-level constant)
- `route_decision` conditional edge function (same pattern as Engineering)
- `escalate` node: logs the failure via telemetry, sets escalation message
- Exports `build_intelligence_graph()` → returns compiled sub-graph

---

### Integration: Wire daemon + Intelligence

**Update `core/graph.py`**:

- Import `build_intelligence_graph` from the intelligence department
- The `department_node` resolves to the intelligence sub-graph when `state["department"] == "intelligence"`
- No if-elif: use the existing registry-based dispatch

**Update `core/orchestrator.py`**:

- Add intelligence-related keywords to department routing (trends, news, briefing, research, analysis)
- Keywords read from registry, NOT hardcoded in orchestrator (open/closed principle)

**Wire daemon → intelligence**:

- In `infra/daemon.py`, register the intelligence graph as a default job
- Each tick creates a trigger request: `{"request": "Generate daily intelligence briefing", "lane": "deep"}`
- The company graph handles routing to the Intelligence department

---

## Tests to write

### `tests/test_infra/test_daemon.py`
- Daemon starts and ticks on schedule (mock the timer, verify tick count)
- Daemon saves checkpoint after each tick (verify checkpointer is called)
- Daemon respects `max_tokens_per_tick` budget (mock token counter)
- Daemon respects `max_wall_clock_per_tick` budget (mock clock)
- Daemon handles graceful shutdown (send stop signal, verify state saved)
- **Kill the process mid-tick → restart → it resumes from checkpoint** (critical test)
- Daemon registers and lists jobs
- Daemon invokes registered jobs in order

### `tests/test_infra/test_model_router.py`
- `route("code")` returns Claude config
- `route("long_docs")` returns Gemini config
- `route("triage")` returns local config
- `route("unknown")` returns default (Claude) config
- `set_route()` overrides a route at runtime
- `list_models()` returns all configured routes
- `ModelConfig` validates required fields

### `tests/test_agents/test_intelligence/test_scout.py`
- Scout produces a non-empty draft given a request
- Scout queries brain context (mock librarian, verify it's called)
- Scout sets `state["draft"]` with structured items
- Each item has required fields (title, source, summary)

### `tests/test_agents/test_intelligence/test_analyst.py`
- Analyst produces a non-empty result given a draft
- Analyst writes a briefing note to brain (mock obsidian, verify write_note called)
- Analyst cross-references with brain (mock librarian)
- Result contains structured briefing with title and items

### `tests/test_agents/test_intelligence/test_skeptic.py`
- Good briefing (novel, sourced, actionable) → `approved=True`
- Bad briefing (duplicate items) → `approved=False`, critique populated
- Bad briefing (missing sources) → `approved=False`
- Revisions counter increments correctly

### `tests/test_agents/test_intelligence/test_graph.py`
- Happy path: request → scout → analyst → skeptic approves → done
- Revise path: skeptic rejects → analyst runs again → skeptic approves
- Bounded loop: after `MAX_REVISIONS` (3), escalates instead of looping infinitely
- Escalation sets a message in result

### `tests/test_integration/test_daemon_flow.py`
- Daemon tick triggers the Intelligence sub-graph through the company graph
- A briefing note appears in the brain after a tick
- Daemon resumes after simulated restart (checkpoint recovery)
- End-to-end: daemon tick → intelligence triad → briefing in brain

---

## Exit gate (ALL must pass)

- [ ] Daemon starts, ticks on schedule (configurable interval)
- [ ] Daemon saves checkpoint after each tick
- [ ] **Kill the process mid-tick → restart → it resumes and completes** (critical test)
- [ ] Token budget and wall-clock budget enforced per tick
- [ ] Model router returns correct model config per task type (`code`, `long_docs`, `triage`)
- [ ] Intelligence triad runs: Scout → Analyst → Skeptic
- [ ] Scout reads brain context before drafting (read-before-act)
- [ ] Skeptic rejects low-quality items, approves good ones
- [ ] `max_revisions = 3` cap is respected in Intelligence department
- [ ] A daily briefing note appears in the brain after a tick
- [ ] Intelligence department registers in agent registry (no if-elif dispatch)
- [ ] Intelligence sub-graph plugs into company graph as one node
- [ ] All `pytest` green

---

## Non-negotiable rules

- Layer rule: agents call Tools, never raw `subprocess`
- No if-elif dispatch — use the registry
- Bounded critic loop: `max_revisions = 3`, then escalate. NEVER unbounded.
- Typed state only — nothing outside `AgentState`
- One class = one agent (single responsibility)
- Read-before-act: Scout queries the brain before producing a draft
- Permission-gated tools: all tool calls go through the Tool base class
- Department = sub-graph + registry line. No editing the orchestrator to add a department.
- Daemon tick must be idempotent — safe to re-run after crash
- No raw `time.sleep()` in the daemon — use async scheduling
- Do NOT build Phase 4 work (Reflector, Guardian)

## Security checklist (enforced at VERIFY step)

- [ ] Daemon: no privilege escalation on restart
- [ ] Daemon: checkpoint files not world-readable (appropriate file permissions)
- [ ] Model router: no API keys stored in code (config only, env vars)
- [ ] Intelligence: URLs in briefings validated (no SSRF if followed later)
- [ ] Intelligence: no credential logging in briefing notes
- [ ] Intelligence: brain notes don't contain raw API responses with auth headers
- [ ] No secrets in code or git history
- [ ] No unsafe deserialization (no pickle, no yaml.load)
- [ ] No eval/exec
- [ ] Permission gates still enforced on all tools

## Architecture diagram

```
                    ┌─────────────────────────────────────────────────┐
                    │                   DAEMON                        │
                    │                                                 │
                    │   ┌─────────────┐    ┌──────────────────┐      │
                    │   │  Heartbeat   │    │  Job Registry     │      │
                    │   │  (15 min)    │───►│  - intelligence   │      │
                    │   └─────────────┘    │  - (future jobs)  │      │
                    │         │             └──────────────────┘      │
                    │         ▼                      │                │
                    │   ┌─────────────┐              ▼                │
                    │   │ Checkpointer│◄── save after each tick      │
                    │   │ (MemorySaver)│                               │
                    │   └─────────────┘                               │
                    │         │                                       │
                    │    resume on restart                             │
                    └─────────┼───────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────────────────────────────────┐
                    │              COMPANY GRAPH                       │
                    │                                                 │
                    │  trigger request → Dispatcher → Orchestrator    │
                    │       → department_node (intelligence)          │
                    │                                                 │
                    │  ┌──────────────────────────────────────┐      │
                    │  │      INTELLIGENCE SUB-GRAPH           │      │
                    │  │                                       │      │
                    │  │   [Scout] (proposer)                  │      │
                    │  │      │  reads brain, scans sources    │      │
                    │  │      ▼                                │      │
                    │  │   [Analyst] (worker) ◄────────┐      │      │
                    │  │      │  writes briefing        │      │      │
                    │  │      ▼                         │      │      │
                    │  │   [Skeptic] (critic)           │      │      │
                    │  │      │                         │      │      │
                    │  │   ┌──┴───┐                     │      │      │
                    │  │   ▼      ▼                     │      │      │
                    │  │ approve  revise ───────────────┘      │      │
                    │  │   │      (max 3)                      │      │
                    │  │   ▼                                   │      │
                    │  │  END / escalate                       │      │
                    │  └──────────────────────────────────────┘      │
                    │                                                 │
                    │  Output: briefing note → brain/obsidian.py     │
                    └─────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────────┐
                    │              MODEL ROUTER                       │
                    │                                                 │
                    │   "code"     → Claude (anthropic)               │
                    │   "long_docs"→ Gemini (google)                  │
                    │   "triage"   → local NIM/Ollama                 │
                    │   "default"  → Claude (fallback)                │
                    └─────────────────────────────────────────────────┘
```

## Key design decisions

1. **Daemon is async, not threaded** — uses `asyncio` event loop with a timer. No threads, no raw `time.sleep()`. Simpler, safer, and composable with LangGraph's async invoke.

2. **Jobs are compiled graphs** — the daemon doesn't know about departments. It holds a registry of compiled LangGraph graphs and invokes them. Adding a new daemon job = registering another graph.

3. **Resume = checkpoint reload** — on restart, the daemon calls `load_last_checkpoint()` per job. LangGraph's checkpointer handles the state recovery. No custom serialization needed.

4. **Intelligence agents are thin** — in Phase 3, they use heuristic logic (template items, simple quality checks). Real LLM calls and web fetching come when the model router is wired to actual APIs. The protocol is proven by structure.

5. **Briefings go to the brain** — Intelligence output is written as Obsidian notes tagged `#briefing`. This means any agent can find them via `librarian.query()`, and the Reflector (Phase 4) can review them.

6. **Model router is config, not code** — routes are a dict lookup. No LLM call to pick a model. This keeps it fast and testable. Dynamic routing (cost-aware, latency-aware) comes in Phase 8.

## When stuck

Follow `docs/WHEN_STUCK.md`:

1. Read the actual error
2. One targeted fix, re-run
3. Consult docs/decisions
4. Search memory: `node .claude/memory/memory.js search "<error>"`
5. Max 2 retries on same fix, then log blocker and STOP

## End of session

- Run `/exit-gate` to verify all criteria pass
- Run `/log` to record the session
- Run `/save-session` to save full conversation
- Commit and push
