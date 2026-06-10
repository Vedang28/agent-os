# Phase 2 — Spine + First Department (Complete Build Prompt)

> Paste this into a new Claude Code session to build Phase 2 of agent-os.

## Context

Phase 1 is complete (commit `b88a52c`). The brain layer (Obsidian + Qdrant + Librarian) and tools layer (BashTool, FileTool, WebTool with permission gates) are in place. 73 passing tests, CI green.

Phase 2 builds the **orchestration spine** (the company graph that routes requests) and the **first department** (Engineering triad: Architect → Scaffolder → CodeDoctor). This proves the full flow: user request → lane assignment → orchestration → department sub-graph → critic loop → approved output.

## What exists now

- `core/state.py` — `AgentState` TypedDict with 12 fields (request, lane, plan, department, task, draft, result, critique, approved, revisions, brain_context, history)
- `core/graph.py` — placeholder no-op graph (just passes through and sets `approved=True`)
- `core/dispatcher.py` — stub docstring only
- `core/orchestrator.py` — stub docstring only
- `agents/protocol.py` — `Agent` Protocol with `name: str` and `async def run(state) -> AgentState`
- `agents/registry.py` — register/get/list_agents/clear (dict-based)
- `agents/security_gate.py` — `SecurityGate` ABC with `async def review(state) -> AgentState`
- `agents/departments/engineering/__init__.py` — empty
- `tools/base.py` — `Tool` ABC with `Permission` enum, permission checker, `execute()` gate
- `tools/permissions.py` — default checker (auto-approves READ/WRITE, blocks SHELL/DESTRUCTIVE)
- `brain/librarian.py` — `Librarian.query()` — semantic search + backlink enrichment
- `infra/telemetry.py` — `get_logger()` with JSON formatter

## Workflow to follow

STEP 1: /start-phase (load context, verify Phase 1 gate still passes)
STEP 2: PLAN — enter plan mode, design both tracks, get approval
STEP 3: BUILD Track A (Spine) + Track B (Engineering department) — sequential or parallel
STEP 4: INSTALL — add any new deps if needed, verify imports
STEP 5: TEST — write all tests, run pytest, fix until green
STEP 6: VERIFY (5-step verification protocol):
6a. @test-runner → all tests green
6b. @architect + /code-review high → no layer violations
6c. @security-auditor + /security-review → no injection, path traversal, SSRF
6d. @gate-checker → all exit criteria pass with evidence
6e. Fix any failures → re-run from 6a
STEP 7: /log → commit → push

## How to run this phase

**Recommended — Parallel:**
```
claude agents
```
Dispatch:
1. `@spine-builder Build Phase 2 Track A: Company StateGraph, Orchestrator node, Dispatcher, checkpointer in /core`
2. `@edge-builder Build Phase 2 Track B: Engineering department — Architect/Scaffolder/CodeDoctor triad in /agents/departments/engineering/`

Merge test:
3. `@gate-checker Verify Phase 2 exit gate`

---

## What to build

### Track A — Spine (`/core/`)

**`core/dispatcher.py`** — Lane Dispatcher:

- `assign_lane(state: AgentState) -> AgentState` — LangGraph node function
- Classifies the request into one of three lanes:
  - `"instant"` — trivial requests (greetings, time, echo). These skip the company entirely.
  - `"fast"` — single-step tasks (lookup, simple question). Route to one agent, no triad.
  - `"deep"` — multi-step tasks (code generation, research, planning). Full triad + critic loop.
- Classification logic: keyword heuristics first (keep it simple — no LLM call needed yet)
  - Instant: matches greetings ("hello", "hi", "hey"), time queries, echo requests
  - Deep: matches code/build/design/architecture keywords, multi-sentence requests
  - Fast: everything else (default lane for unmatched)
- Sets `state["lane"]` and returns updated state
- **Lane discipline:** 90% of requests should never enter the company.

**`core/orchestrator.py`** — Orchestrator node:

- `orchestrate(state: AgentState) -> AgentState` — LangGraph node function
- For `"deep"` lane: selects the right department from the agent registry, sets `state["department"]`
- For `"fast"` lane: picks a single agent, sets `state["department"]`
- For `"instant"` lane: should never reach here (dispatcher short-circuits)
- Decomposition: breaks `state["request"]` into `state["plan"]` (list of steps)
- Uses the agent registry to resolve department name → sub-graph
- Reads `brain_context` via librarian (read-before-act)

**`core/graph.py`** — Company StateGraph (replace the no-op placeholder):

- Build the full company graph:
  ```
  START → dispatcher → route_by_lane
    - instant → instant_response → END
    - fast/deep → orchestrator → department_node → END
  ```
- `route_by_lane` is a conditional edge based on `state["lane"]`
- `instant_response` node handles cheap requests directly (returns a response, skips the company)
- `department_node` invokes the registered department sub-graph
- Wire the LangGraph **checkpointer** (`MemorySaver` for now — SQLite swap in Phase 8)
- The graph must compile and be invokable end-to-end
- Expose `build_company_graph()` returning the compiled graph

**`core/checkpointer.py`** — Checkpointer configuration (new file):

- Wrap LangGraph's `MemorySaver` as the default checkpointer
- Expose `get_checkpointer()` for use by the company graph
- This enables resume-after-interrupt and human-in-the-loop (Phase 4)

---

### Track B — Engineering Department (`/agents/departments/engineering/`)

**`agents/departments/engineering/architect.py`** — Architect (proposer):

- Implements `Agent` protocol
- `name = "engineering.architect"`
- `role = "proposer"`
- `async def run(self, state: AgentState) -> AgentState`:
  - Queries the brain (`Librarian().query(state["request"])`) for relevant context
  - Stores brain results in `state["brain_context"]`
  - Produces a `draft` — a plan/design for the requested task
  - Sets `state["draft"]` and returns
  - In Phase 2 the draft is heuristic (template-based), not LLM-generated

**`agents/departments/engineering/scaffolder.py`** — Scaffolder (worker):

- Implements `Agent` protocol
- `name = "engineering.scaffolder"`
- `role = "worker"`
- `async def run(self, state: AgentState) -> AgentState`:
  - Takes `state["draft"]` (the architect's plan)
  - Produces `state["result"]` — the actual implementation/output
  - Uses tools (FileTool, BashTool) as needed via the tool registry
  - In Phase 2 the result is heuristic (echoes the draft as a scaffold), not LLM-generated

**`agents/departments/engineering/code_doctor.py`** — CodeDoctor (critic):

- Implements `Agent` protocol
- `name = "engineering.code_doctor"`
- `role = "critic"`
- `async def run(self, state: AgentState) -> AgentState`:
  - Reviews `state["result"]` against `state["draft"]`
  - Either approves (`state["approved"] = True`) or rejects with critique
  - On rejection: sets `state["approved"] = False`, populates `state["critique"]` (dict with `reason` and `suggestions`), increments `state["revisions"]`
  - Approval logic in Phase 2: heuristic checks (result non-empty, matches draft intent)

**`agents/departments/engineering/graph.py`** — Engineering sub-graph:

- Builds a LangGraph `StateGraph` for the Engineering department:
  ```
  START → architect → scaffolder → code_doctor → route_decision
    - approved → END
    - revise → scaffolder (loop back)
    - max_revisions_hit → escalate → END
  ```
- `MAX_REVISIONS = 3` (module-level constant)
- `route_decision` is a conditional edge function:
  - If `state["approved"] == True` → END
  - If `state["revisions"] >= MAX_REVISIONS` → `"escalate"`
  - Otherwise → `"scaffolder"` (revise loop)
- `escalate` node: logs the failure via telemetry, sets `state["result"]` to an escalation message
- **This is the bounded critic loop** — NEVER unbounded
- Exports `build_engineering_graph()` → returns compiled sub-graph

**`agents/departments/engineering/__init__.py`** — Department registration:

- Import and register all three agents in the agent registry
- Export `build_engineering_graph` for the company graph to use

---

### Integration: Wire department into company graph

**Update `core/graph.py`**:

- Import `build_engineering_graph` from the engineering department
- The `department_node` resolves to the engineering sub-graph when `state["department"] == "engineering"`
- The full flow works: request → dispatcher → orchestrator → engineering triad → result

---

## Tests to write

### `tests/test_core/test_dispatcher.py`
- Instant request ("hello") gets `lane="instant"`
- Instant request ("what time is it") gets `lane="instant"`
- Deep request ("build a REST API for user management") gets `lane="deep"`
- Deep request ("design the authentication architecture") gets `lane="deep"`
- Fast request ("what is the capital of France") gets `lane="fast"`
- Empty/edge-case request gets a lane (no crash)

### `tests/test_core/test_orchestrator.py`
- Deep request routes to "engineering" department
- Plan is decomposed (list with at least one step)
- State has `department` set after orchestration

### `tests/test_core/test_graph.py`
- Instant request flows through and returns a response without hitting orchestrator
- Deep request flows through dispatcher → orchestrator → department → result
- Graph compiles without errors
- Checkpointer is wired (invoke with `config={"configurable": {"thread_id": "t1"}}`, state persists)

### `tests/test_core/test_checkpointer.py`
- `get_checkpointer()` returns a `MemorySaver` instance
- Checkpointer can be passed to graph compilation

### `tests/test_agents/test_engineering/test_architect.py`
- Architect produces a non-empty draft given a request
- Architect populates `brain_context` (mock librarian to verify it's called)
- Architect sets `state["draft"]`

### `tests/test_agents/test_engineering/test_scaffolder.py`
- Scaffolder produces a non-empty result given a draft
- Scaffolder sets `state["result"]`

### `tests/test_agents/test_engineering/test_code_doctor.py`
- Good result (non-empty, matches draft) → `approved=True`
- Bad result (empty) → `approved=False`, critique populated, revisions incremented
- Revisions counter increments correctly

### `tests/test_agents/test_engineering/test_graph.py`
- Happy path: request → architect → scaffolder → critic approves → done
- Revise path: critic rejects → scaffolder runs again → critic approves
- Bounded loop: after `MAX_REVISIONS` (3), escalates instead of looping infinitely
- Escalation sets a message in result

### `tests/test_integration/test_full_flow.py`
- End-to-end: a deep request flows User → Dispatcher → Orchestrator → Engineering triad → approved output
- A deliberately bad draft triggers exactly one revise loop then passes
- An instant request short-circuits the company (does NOT enter orchestrator)

---

## Exit gate (ALL must pass)

- [ ] `core/dispatcher.py` — classifies requests into instant/fast/deep lanes
- [ ] `core/orchestrator.py` — routes deep requests to the engineering department
- [ ] `core/graph.py` — full company graph compiles and routes correctly (instant short-circuits, deep hits department)
- [ ] Checkpointer wired — state persists across invocations with `thread_id`
- [ ] Engineering sub-graph — Architect → Scaffolder → CodeDoctor with conditional edge
- [ ] Bounded critic loop — `max_revisions = 3` enforced, escalation on exceeded
- [ ] A deep request flows: User → Dispatcher → Orchestrator → Engineering triad → approved output
- [ ] A deliberately bad draft triggers exactly one revise loop then passes
- [ ] Engineering department registers in agent registry (no if-elif dispatch)
- [ ] Engineering sub-graph plugs into company graph as one node
- [ ] All `pytest` green

---

## Non-negotiable rules

- Layer rule: agents call Tools, never raw `subprocess`
- No if-elif dispatch — use the registry
- Bounded critic loop: `max_revisions = 3`, then escalate. NEVER unbounded.
- Typed state only — nothing outside `AgentState`
- One class = one agent (single responsibility)
- Read-before-act: the Architect queries the brain before producing a draft
- Permission-gated tools: Scaffolder uses tools through the Tool base class
- Department = sub-graph + registry line. No editing the orchestrator to add a department.
- Do NOT build Phase 3 work (daemon, Intelligence department)

## Security checklist (enforced at VERIFY step)

- [ ] No command injection in any agent's tool invocations
- [ ] No path traversal in generated file paths
- [ ] No unbounded loops (all critic loops capped at `max_revisions`)
- [ ] No secrets in code or git history
- [ ] No unsafe deserialization (no pickle, no yaml.load)
- [ ] No eval/exec
- [ ] Permission gates still enforced on all tools
- [ ] Escalation path exists (no silent failures)

## Architecture diagram

```
                           ┌─────────────────────────────────────────┐
                           │           COMPANY GRAPH                  │
                           │                                         │
  Request ──► START ──► [Dispatcher] ──► route_by_lane               │
                              │                                       │
              ┌───────────────┼───────────────────┐                  │
              ▼               ▼                   ▼                  │
         "instant"        "fast"             "deep"                  │
              │               │                   │                  │
              ▼               ▼                   ▼                  │
     [instant_response]  [orchestrator]     [orchestrator]           │
              │               │                   │                  │
              ▼               ▼                   ▼                  │
             END        [department]        [department]             │
                              │                   │                  │
                              ▼                   ▼                  │
                             END    ┌─────────────────────────┐     │
                                    │   ENGINEERING SUB-GRAPH  │     │
                                    │                         │     │
                                    │  [Architect] (proposer)  │     │
                                    │       │                  │     │
                                    │       ▼                  │     │
                                    │  [Scaffolder] (worker)◄─┐│     │
                                    │       │                 ││     │
                                    │       ▼                 ││     │
                                    │  [CodeDoctor] (critic)  ││     │
                                    │       │                 ││     │
                                    │   ┌───┴───┐            ││     │
                                    │   ▼       ▼            ││     │
                                    │ approve  revise────────┘│     │
                                    │   │       (max 3)       │     │
                                    │   ▼                     │     │
                                    │  END / escalate         │     │
                                    └─────────────────────────┘     │
                           └─────────────────────────────────────────┘
```

## Key design decisions

1. **Dispatcher is a pure function** — no LLM call, just keyword heuristics. Fast, deterministic, testable. LLM-based classification can be swapped in later.

2. **Department as sub-graph** — each department is a self-contained LangGraph `StateGraph` that compiles independently. The company graph treats it as one node. Adding a new department = new sub-graph + one registry line.

3. **Conditional edge for critic loop** — LangGraph's native conditional edge pattern. The decision function checks `approved` and `revisions` count. Three possible outcomes: approve, revise, escalate.

4. **Checkpointer from day one** — `MemorySaver` for now. Wiring it in Phase 2 means the company graph supports `thread_id`-based invocation, enabling resume-after-interrupt and state inspection. SQLite swap in Phase 8.

5. **Agents are thin** — in Phase 2, agents use simple heuristic logic (no LLM calls). The protocol is proven by structure. LLM integration comes when we wire the model router (Phase 3+).

6. **Escalation over failure** — when `max_revisions` is hit, the department escalates (logs + flag) rather than crashing or silently dropping work. This is the foundation for Guardian human-in-the-loop in Phase 4.

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
