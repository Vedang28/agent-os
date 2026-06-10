# Phase 4 — Learning Loop + Guardian (Complete Build Prompt)

> Paste this into a new Claude Code session to build Phase 4 of agent-os.

## Context

Phase 3 is complete. The daemon heartbeat runs on a configurable interval, saves checkpoints after each tick, and resumes after restart. The Intelligence department (Scout → Analyst → Skeptic) produces briefing notes written to the brain. The model router maps task types to model configs. Two departments (Engineering, Intelligence) are registered and working through the company graph.

Phase 4 adds the **learning loop** (Reflector that reviews outcomes and writes playbooks) and the **Guardian** (permission enforcement, human-in-the-loop interrupt, kill switch). This is where agent-os starts getting smarter over time and safer by design.

## What exists now

- `core/state.py` — `AgentState` TypedDict with 12 fields
- `core/graph.py` — full company StateGraph with lane routing, department dispatch
- `core/dispatcher.py` — lane classifier (instant/fast/deep)
- `core/orchestrator.py` — routes to departments, decomposes plans, reads brain context
- `core/checkpointer.py` — `get_checkpointer()` wrapping `MemorySaver`
- `agents/protocol.py` — `Agent` Protocol
- `agents/registry.py` — register/get/list_agents/clear
- `agents/security_gate.py` — `SecurityGate` ABC
- `agents/departments/engineering/` — Architect → Scaffolder → CodeDoctor triad
- `agents/departments/intelligence/` — Scout → Analyst → Skeptic triad
- `tools/base.py` — `Tool` ABC with `Permission` enum
- `tools/permissions.py` — default checker (auto-approves READ/WRITE, blocks SHELL/DESTRUCTIVE)
- `tools/bash.py`, `tools/file.py`, `tools/web.py` — permission-gated tools
- `brain/schema.py` — `Note` Pydantic model
- `brain/obsidian.py` — Obsidian vault (write/read/list/backlinks)
- `brain/qdrant.py` — Qdrant vector store (embed/search)
- `brain/librarian.py` — `Librarian.query()`
- `infra/telemetry.py` — `get_logger()` with JSON formatter
- `infra/daemon.py` — daemon heartbeat, job registry, checkpoint persistence, resume-after-restart
- `infra/model_router.py` — model routing by task type

## Workflow to follow

STEP 1: /start-phase (load context, verify Phase 3 gate still passes)
STEP 2: PLAN — enter plan mode, design both tracks, get approval
STEP 3: BUILD Track A (Reflector) + Track B (Guardian) — sequential or parallel
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
1. `@spine-builder Build Phase 4 Track A: Reflector — reviews outcomes in the brain, writes playbook notes, proposers read playbooks in /brain/reflector.py`
2. `@edge-builder Build Phase 4 Track B: Guardian — permission gates, human-in-the-loop interrupt via LangGraph interrupt(), kill switch in /agents/guardian.py`

Merge test:
3. `@gate-checker Verify Phase 4 exit gate`

---

## What to build

### Track A — Reflector (`/brain/`)

**`brain/outcome.py`** — Outcome schema (new file):

- `Outcome(BaseModel)`:
  - `task_id: str` — unique identifier for the task
  - `department: str` — which department handled it
  - `success: bool` — did the task complete successfully
  - `revisions: int` — how many critic loops before approval
  - `critic_verdict: str` — final critic decision (approved/escalated)
  - `user_feedback: str | None` — optional user feedback
  - `tool_errors: list[str]` — any tool execution errors
  - `tokens_used: int` — total tokens consumed
  - `wall_clock_seconds: float` — total time taken
  - `timestamp: str` — ISO 8601 timestamp

- `OutcomeStore` class:
  - `record(outcome: Outcome)` — writes outcome as a brain note tagged `#outcome`
  - `query_recent(n: int = 20) -> list[Outcome]` — reads recent outcomes from brain
  - `query_by_department(department: str) -> list[Outcome]` — filter by department
  - `query_failures() -> list[Outcome]` — returns outcomes where `success=False`

**`brain/reflector.py`** — Reflector agent (replace existing stub if any):

- `Reflector` class implementing `Agent` protocol
- `name = "core.reflector"`
- `role = "learning"`
- `MIN_OUTCOMES_TO_REFLECT: int = 5` — only reflect when enough data exists
- `async def run(self, state: AgentState) -> AgentState`:
  - Triggered by the daemon after ticks with sufficient new outcomes
  - Reads recent outcomes from `OutcomeStore.query_recent()`
  - **Pattern detection**:
    - Repeated failures in a department → playbook entry about the failure pattern
    - High revision count → playbook entry about drafting better first time
    - Tool errors → playbook entry about tool usage patterns
    - Successful strategies → playbook entry reinforcing what works
    - Cost outliers → playbook entry about budget-conscious approaches
  - **Writes playbook notes** to the brain via `obsidian.py`:
    - Tagged `#playbook` and `#playbook/{department}`
    - Format: `{"title": "Playbook: ...", "content": "When X, do Y because Z", "tags": ["playbook", ...]}`
    - Each playbook note has: pattern observed, recommended action, evidence (outcome IDs)
  - Returns state with `state["result"]` = summary of playbook updates

**Update proposers to read playbooks**:

- **Update `agents/departments/engineering/architect.py`**:
  - During `read-before-act`, also query for `#playbook/engineering` notes
  - Include relevant playbook entries in `state["brain_context"]`
  - The draft should be informed by past learnings

- **Update `agents/departments/intelligence/scout.py`**:
  - Same pattern: query for `#playbook/intelligence` notes before drafting

**`brain/playbook.py`** — Playbook query helper (new file):

- `get_playbooks(department: str) -> list[Note]` — queries brain for playbook notes tagged for this department
- `get_all_playbooks() -> list[Note]` — all playbook notes
- Used by proposers during read-before-act

---

### Track B — Guardian (`/agents/`)

**`agents/guardian.py`** — Guardian agent (new file):

- `Guardian` singleton class
- `name = "core.guardian"`
- `role = "safety"`

- **Permission gate enforcement**:
  - `async def check_permission(tool: Tool, args: dict) -> PermissionDecision`
  - `PermissionDecision(BaseModel)`: allowed (bool), reason (str), requires_approval (bool)
  - Decision logic:
    - `Permission.READ` → allowed, logged
    - `Permission.WRITE` → allowed, logged with audit trail
    - `Permission.SHELL` → **paused for approval** (human-in-the-loop)
    - `Permission.DESTRUCTIVE` → **paused for explicit approval + confirmation**
  - Audit trail: every permission check logged via `telemetry.get_logger()` with tool name, permission level, decision, timestamp

- **Human-in-the-loop interrupt** (LangGraph native):
  - `async def request_approval(action: str, details: dict) -> bool`
  - Uses LangGraph's `interrupt()` function to pause the graph
  - The graph state is saved to the checkpointer
  - When a human approves/rejects, the graph resumes via `Command(resume=...)`
  - Approval/rejection logged to audit trail
  - Timeout: if no response within configurable period (default: 300s), default to DENY

- **Kill switch**:
  - `async def kill()` → immediately stops all running graphs
  - Saves state before stopping (graceful via checkpointer)
  - Sets a global `_killed` flag checked by the daemon heartbeat
  - Triggers:
    - `cost_ceiling_breach(tokens_used: int, ceiling: int)` — auto-kill on budget exceeded
    - `time_ceiling_breach(elapsed: float, ceiling: float)` — auto-kill on time exceeded
    - `manual_kill()` — human-triggered emergency stop
  - After kill: daemon must be explicitly restarted (no auto-resume after kill)

**Wire Guardian into tool execution**:

- **Update `tools/base.py`** or `tools/permissions.py`:
  - Before `execute()`, route through `Guardian.check_permission()`
  - If `requires_approval`, invoke `Guardian.request_approval()` which triggers LangGraph `interrupt()`
  - If denied, raise `PermissionDeniedError` with the denial reason
  - If killed, raise `KillSwitchError`

**Wire Guardian into the company graph**:

- **Update `core/graph.py`**:
  - Add a Guardian check node or integrate into the tool execution path
  - The interrupt mechanism uses LangGraph's native `interrupt()` → the graph pauses, checkpoints, and waits for `Command(resume=...)` to continue

---

### Integration: Wire Reflector into daemon

**Update `infra/daemon.py`**:

- After department jobs complete, check if outcome count >= `MIN_OUTCOMES_TO_REFLECT`
- If yes, invoke the Reflector as part of the daemon tick
- Reflector runs after the Intelligence job, not during it

**Outcome recording**:

- **Update `core/graph.py`** or add a post-processing node:
  - After a department completes, record an `Outcome` to the brain via `OutcomeStore.record()`
  - Capture: department, success/failure, revisions, tokens, wall-clock time, tool errors

---

## Tests to write

### `tests/test_brain/test_outcome.py`
- `Outcome` model validates required fields
- `Outcome` model rejects invalid data (negative tokens, etc.)
- `OutcomeStore.record()` writes outcome as a brain note tagged `#outcome`
- `OutcomeStore.query_recent()` returns outcomes in reverse chronological order
- `OutcomeStore.query_by_department()` filters correctly
- `OutcomeStore.query_failures()` returns only failed outcomes

### `tests/test_brain/test_reflector.py`
- Reflector reads recent outcomes from the brain
- Reflector identifies repeated failure pattern → writes a playbook note
- Reflector identifies successful strategy → writes a reinforcement playbook note
- Reflector skips when fewer than `MIN_OUTCOMES_TO_REFLECT` outcomes exist
- Playbook notes are tagged `#playbook` and `#playbook/{department}`
- Playbook note contains: pattern, recommended action, evidence
- Reflector returns summary of updates in `state["result"]`

### `tests/test_brain/test_playbook.py`
- `get_playbooks("engineering")` returns playbook notes for engineering
- `get_playbooks("nonexistent")` returns empty list
- `get_all_playbooks()` returns all playbook notes
- Proposer reads playbooks: mock Architect, verify brain query includes playbook tag

### `tests/test_agents/test_guardian.py`
- `check_permission` for READ tool → allowed, logged
- `check_permission` for WRITE tool → allowed, logged with audit trail
- `check_permission` for SHELL tool → requires approval
- `check_permission` for DESTRUCTIVE tool → requires explicit approval
- `request_approval` triggers LangGraph `interrupt()` (mock the interrupt mechanism)
- Approval resumes graph execution
- Denial stops execution and raises `PermissionDeniedError`
- Timeout on approval → defaults to DENY
- Kill switch sets `_killed` flag
- Kill switch saves state before stopping
- `cost_ceiling_breach` triggers kill when tokens exceed ceiling
- `time_ceiling_breach` triggers kill when time exceeds ceiling
- After kill, daemon loop detects `_killed` and stops
- Audit trail: every permission check logged (verify log output)

### `tests/test_integration/test_learning_loop.py`
- End-to-end: record 5+ outcomes → Reflector runs → playbook note exists in brain
- Proposer reads playbook: Architect query includes playbook results
- **Measurable improvement**: run a task WITHOUT playbook → record outcome → Reflector writes playbook → run SAME task WITH playbook → verify different (improved) behavior
- Guardian blocks a SHELL tool call without approval
- Guardian blocks a DESTRUCTIVE tool call without explicit approval
- Guardian interrupt pauses graph → approve → graph resumes and completes
- Kill switch stops all running graphs

---

## Exit gate (ALL must pass)

- [ ] Reflector reads outcomes from brain
- [ ] Reflector identifies patterns and writes playbook notes tagged `#playbook`
- [ ] Proposers read playbooks via brain query (verify: brain query includes playbook tag)
- [ ] **Measurable improvement on a repeated task after reflection** (different behavior with vs without playbook)
- [ ] `OutcomeStore` records outcomes and supports filtering
- [ ] Guardian enforces permission levels on all tools
- [ ] `READ` tools execute without approval
- [ ] `WRITE` tools execute with logging
- [ ] `SHELL` tools pause for approval (human-in-the-loop interrupt)
- [ ] `DESTRUCTIVE` tools pause for explicit approval + confirmation
- [ ] Human-in-the-loop interrupt works (pause → approve → resume)
- [ ] Kill switch stops all running graphs and saves state
- [ ] **No destructive action executes without an approval step**
- [ ] Audit trail logs every permission check
- [ ] All `pytest` green

---

## Non-negotiable rules

- Layer rule: agents call Tools, never raw `subprocess`
- No if-elif dispatch — use the registry
- Bounded critic loop: `max_revisions = 3`, then escalate. NEVER unbounded.
- Typed state only — nothing outside `AgentState`
- One class = one agent (single responsibility)
- Read-before-act: proposers query brain + playbooks before drafting
- Permission-gated tools: every tool call flows through Guardian
- Guardian is mandatory — no tool executes without permission check
- Kill switch is always available — no bypass
- Playbook notes are additive — Reflector never deletes existing playbooks, only adds new ones or updates
- Do NOT build Phase 5 work (Dashboard, Voice I/O)

## Security checklist (enforced at VERIFY step)

- [ ] Guardian: no bypass path for permission checks (every tool call routes through Guardian)
- [ ] Guardian: DESTRUCTIVE actions require TWO confirmations (approval + confirmation)
- [ ] Guardian: interrupt mechanism cannot be spoofed (only legitimate approval resumes)
- [ ] Guardian: kill switch cannot be disabled by an agent (only human can restart)
- [ ] Guardian: audit trail is append-only (agents cannot edit or delete logs)
- [ ] Reflector: playbook notes cannot contain executable code (data only)
- [ ] Reflector: outcome data sanitized before storage (no injection via tool_errors field)
- [ ] No secrets in code or git history
- [ ] No unsafe deserialization (no pickle, no yaml.load)
- [ ] No eval/exec
- [ ] Permission gates enforced on all tools including new integrations

## Architecture diagram

```
                    ┌──────────────────────────────────────────────────────┐
                    │                  LEARNING LOOP                       │
                    │                                                      │
                    │   Department completes task                          │
                    │         │                                            │
                    │         ▼                                            │
                    │   ┌──────────────┐                                  │
                    │   │ OutcomeStore  │ ── records success/failure ──►  │
                    │   │  .record()   │    brain note #outcome           │
                    │   └──────────────┘                                  │
                    │         │                                            │
                    │     (≥5 outcomes accumulated)                        │
                    │         │                                            │
                    │         ▼                                            │
                    │   ┌──────────────┐    ┌───────────────────┐        │
                    │   │  Reflector   │───►│ Playbook Notes     │        │
                    │   │  .run()      │    │ #playbook/dept     │        │
                    │   │              │    │ "When X, do Y"     │        │
                    │   └──────────────┘    └───────────────────┘        │
                    │                              │                      │
                    │                     read-before-act                 │
                    │                              │                      │
                    │                              ▼                      │
                    │                     ┌─────────────────┐            │
                    │                     │  Proposer reads  │            │
                    │                     │  playbooks →     │            │
                    │                     │  better drafts   │            │
                    │                     └─────────────────┘            │
                    └──────────────────────────────────────────────────────┘

                    ┌──────────────────────────────────────────────────────┐
                    │                    GUARDIAN                          │
                    │                                                      │
                    │   Agent calls tool                                   │
                    │         │                                            │
                    │         ▼                                            │
                    │   ┌──────────────────┐                              │
                    │   │ check_permission  │                              │
                    │   │                  │                              │
                    │   │  READ  → allow   │                              │
                    │   │  WRITE → allow+log│                              │
                    │   │  SHELL → interrupt│──► pause graph              │
                    │   │  DESTR → interrupt│──► pause + confirm          │
                    │   └──────────────────┘        │                     │
                    │                               ▼                     │
                    │                    ┌─────────────────┐              │
                    │                    │ Human approves? │              │
                    │                    │  YES → resume   │              │
                    │                    │  NO  → deny     │              │
                    │                    │  timeout → deny │              │
                    │                    └─────────────────┘              │
                    │                                                      │
                    │   Kill switch:                                       │
                    │     cost_ceiling_breach() ──┐                       │
                    │     time_ceiling_breach() ──┼──► kill() → stop all  │
                    │     manual_kill()        ──┘    save state          │
                    └──────────────────────────────────────────────────────┘
```

## Key design decisions

1. **Reflector is a brain agent, not a core agent** — it lives in `/brain/` because its job is reading and writing knowledge. It's triggered by the daemon but doesn't own orchestration.

2. **Playbooks are brain notes, not config** — stored in Obsidian as `#playbook` tagged notes. This means they're searchable via `librarian.query()`, visible to humans, and versioned like any other knowledge. No separate config system.

3. **Guardian uses LangGraph `interrupt()`** — native pause/resume mechanism. The graph checkpoints its state when interrupted, and resumes exactly where it left off when the human responds. No custom pause mechanism.

4. **Kill switch is a hard stop** — after `kill()`, the daemon does NOT auto-restart. This is intentional: a cost ceiling breach or manual kill means "stop everything now." Human must explicitly restart.

5. **Outcome recording is automatic** — every completed task records an outcome. The Reflector doesn't need to be asked to reflect — it runs when enough data accumulates. This is the foundation for continuous improvement.

6. **Measurable improvement = testable** — the exit gate requires a concrete test: same task, with and without playbook, produces different (better) behavior. This isn't vague — it's an assertion in a test.

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
