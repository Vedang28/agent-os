# Phase 2 — Spine + First Department (Engineering)

> **Prerequisite:** Phase 1 exit gate must pass.
> **Parallel tracks.** Track A = Orchestration spine. Track B = Engineering department.

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

## Track A — Orchestration (Spine)

### `/core/dispatcher.py` — Lane assignment
- Takes incoming request, classifies into `lane`: `instant`, `fast`, or `deep`
- `instant` → respond directly (greetings, time). Never enters the company graph.
- `fast` → single agent, no triad
- `deep` → full department triad
- **Lane discipline:** 90% of requests should never enter the company.

### `/core/orchestrator.py` — Decompose + route
- Receives `deep` requests from Dispatcher
- Decomposes into plan steps
- Routes to the correct department sub-graph by name (via registry)
- Reads `brain_context` via librarian (read-before-act)

### `/core/graph.py` — Company StateGraph
- Wire: `START → dispatcher → [instant_end | orchestrator → department_subgraph → END]`
- Conditional edges based on lane
- Wire the LangGraph **checkpointer** (SQLite) for resume-after-restart
- The department sub-graph plugs in as one node (open/closed principle)

### Checkpointer
- Use LangGraph's built-in SQLite checkpointer
- Wire into the company graph
- Verify: interrupt mid-run → resume from checkpoint

---

## Track B — Engineering Department

### `/agents/departments/engineering/`

**`architect.py`** — Proposer:
- Reads brain context (read-before-act)
- Analyzes the task, produces a `draft` (implementation plan)

**`scaffolder.py`** — Worker:
- Takes the `draft`, executes it using tools
- Produces `result` (the actual code/output)

**`code_doctor.py`** — Critic:
- Reviews `result` against the original `request`
- Produces `critique` with `approved: bool`
- If not approved: increments `revisions`, sends back to Scaffolder
- **Bounded:** `max_revisions = 3`. After 3, escalate (set a flag, don't loop forever).

**`graph.py`** — Department sub-graph:
- `START → architect → scaffolder → code_doctor → [approved: END | revise: scaffolder]`
- Conditional edge on `code_doctor` output
- This sub-graph registers as one node in the company graph

**Register** in `agents/registry.py`.

---

## Merge point
Engineering sub-graph registers and plugs into the company graph as one node.

Test: a deep request flows `User → Dispatcher → Orchestrator → Engineering triad → approved output`.

---

## Exit gate (ALL must pass)
- [ ] Dispatcher classifies requests into lanes correctly
- [ ] `instant` lane responds without entering the company graph
- [ ] Orchestrator decomposes and routes to Engineering
- [ ] Engineering triad runs: Architect → Scaffolder → CodeDoctor
- [ ] Critic approves good work (approved = True, exits loop)
- [ ] Critic rejects bad work → exactly one revision loop → then passes
- [ ] `max_revisions` cap is respected (never more than 3 loops)
- [ ] Checkpointer wired — graph state survives interrupt
- [ ] Full flow: deep request → Dispatcher → Orchestrator → Engineering → approved output
- [ ] All `pytest` green

## Rules
- Department = sub-graph + registry line. No editing the orchestrator to add departments.
- Triad pattern: proposer/worker/critic. Every department follows this.
- Critic loop is BOUNDED at `max_revisions = 3`.
- Read-before-act: proposers query the brain first.


## Verification
After building, run the full **Verification Protocol** from `prompts/VERIFICATION_PROTOCOL.md`:
1. `@test-runner` — all tests green
2. `@architect` + `/code-review high` — no layer violations, no bugs
3. `@security-auditor` + `/security-review` — no injection, no secrets, no SSRF
4. `@gate-checker` — all exit criteria pass with evidence
