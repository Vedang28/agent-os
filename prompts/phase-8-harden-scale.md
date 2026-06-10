# Phase 8 — Harden & Scale (Complete Build Prompt)

> Paste this into a new Claude Code session to build Phase 8 of agent-os.
> **Final phase.** Focus: reliability, security, cost control, and proving the system runs autonomously.

## Context

Phase 7 is complete. All departments from the AGENT_ROSTER.md catalog are built, registered, and passing end-to-end tests. Every code-producing department has a SecurityGate. Every department has a triad with bounded critic loop. The full company graph routes any request to the right department via the Orchestrator. Composio tools are wired into Growth and Sales departments. Dev Experience departments are being dogfooded.

Phase 8 hardens the system: eval harness per department, cost dashboards, lane tuning, comprehensive security audit, load testing, and the production-grade Postgres checkpointer. The exit gate is the ultimate proof: **agent-os runs unattended for 48 hours with no crash, generates briefings, improves playbooks, handles requests, and stays within cost ceiling.**

## What exists now

- `core/` — state, graph, dispatcher, orchestrator, checkpointer — full company graph with all departments
- `agents/` — protocol, registry, guardian, security_gate
- `agents/departments/` — all divisions: engineering, intelligence, backend (4 depts), frontend (3), quality (2), devops (3), ai_ml (2), growth (4), sales_ops (3), perception (3), dev_experience (8)
- `tools/` — base, registry, bash, file, web (+ Composio/MCP tools)
- `integrations/` — composio bridge, mcp bridge, token store, tool wrappers (gmail, notion, slack, github, calendar)
- `brain/` — schema, obsidian, qdrant, librarian, reflector, outcome, playbook
- `infra/` — daemon, model_router, telemetry
- `io/` — dashboard_api, voice, event_bus
- `dashboard/` — Next.js frontend

## Workflow to follow

STEP 1: /start-phase (load context, verify Phase 7 gate still passes)
STEP 2: PLAN — enter plan mode, design the workstreams, get approval
STEP 3: BUILD — use workflow for audit, then targeted fixes
STEP 4: TEST — full test suite + new eval/cost tests + 48h soak test
STEP 5: VERIFY (5-step verification protocol):
5a. @test-runner → all tests green, all evals green
5b. @architect + /code-review high → no layer violations
5c. @security-auditor + /security-review → comprehensive audit (all three security layers)
5d. @gate-checker → all exit criteria pass with evidence
5e. Fix any failures → re-run from 5a
STEP 6: /log → commit → push

## How to run this phase

**Recommended — Workflow for audit, then targeted fixes:**
```
Run a workflow to audit agent-os for security, performance, and reliability issues
```

Then fix issues with targeted agents:
```
claude agents
```
1. `@spine-builder Build eval harness and cost tracker in /infra/`
2. `@edge-builder Swap checkpointer from SQLite to Postgres in /infra/checkpointer.py`
3. `@security-auditor Full security audit — all three layers`
4. `@gate-checker Verify Phase 8 exit gate after 48h soak test`

---

## What to build

### Workstream 1 — Eval Harness Per Department

**`infra/eval_harness.py`** — Eval runner:

- `EvalCase(BaseModel)`:
  - `name: str` — eval name (e.g. "engineering.api_generation")
  - `department: str` — target department
  - `input_request: str` — the fixed test request
  - `expected_traits: list[str]` — what the output must exhibit (keywords, patterns, structure)
  - `max_tokens: int` — token budget ceiling for this eval
  - `max_seconds: float` — wall-clock ceiling

- `EvalResult(BaseModel)`:
  - `name: str`
  - `passed: bool`
  - `traits_matched: list[str]`
  - `traits_missed: list[str]`
  - `tokens_used: int`
  - `seconds_elapsed: float`
  - `within_budget: bool`

- `EvalHarness` class:
  - `register_eval(case: EvalCase)` — add an eval case
  - `async def run_eval(name: str) -> EvalResult` — run one eval through the company graph
  - `async def run_all() -> list[EvalResult]` — run all registered evals
  - `async def run_department(department: str) -> list[EvalResult]` — run evals for one department
  - Evals use the same company graph — they're real invocations with fixed inputs

- **Regression evals** (one per department):
  - Fixed input → assert output matches expected traits
  - Output must be deterministic enough to test (structure, not exact text)
  - Regression = same input produces WORSE output than baseline

- **Cost evals** (one per department):
  - Same fixed input → assert `tokens_used <= max_tokens`
  - Assert `seconds_elapsed <= max_seconds`
  - These catch departments that suddenly become expensive

- **Wire into CI** (`tests/test_evals/`):
  - `test_eval_all.py` — runs `EvalHarness.run_all()`, asserts all pass
  - CI runs this as a required check

**Eval definitions** (`infra/eval_cases/`):
- One YAML or JSON file per department defining eval cases
- Example: `engineering.yaml`:
  ```yaml
  - name: engineering.api_generation
    department: engineering
    input_request: "Build a REST API for user management with CRUD endpoints"
    expected_traits: ["endpoint", "user", "create", "read", "update", "delete"]
    max_tokens: 50000
    max_seconds: 60
  ```

---

### Workstream 2 — Cost Dashboards

**`infra/cost_tracker.py`** — Cost tracking:

- `CostRecord(BaseModel)`:
  - `task_id: str`
  - `department: str`
  - `model: str` — which model was used
  - `tokens_input: int`
  - `tokens_output: int`
  - `cost_usd: float` — estimated cost based on model pricing
  - `wall_clock_seconds: float`
  - `timestamp: str`

- `CostTracker` class:
  - `record(cost: CostRecord)` — save a cost record
  - `get_total(since: str | None = None) -> CostSummary` — total cost, optionally since a timestamp
  - `get_by_department(department: str) -> list[CostRecord]` — filter by department
  - `get_by_model(model: str) -> list[CostRecord]` — filter by model
  - `get_burn_rate(window_hours: int = 24) -> float` — cost per hour over recent window
  - `check_ceiling(ceiling_usd: float) -> bool` — are we under budget?
  - Storage: brain notes tagged `#cost` or a separate lightweight store (not Qdrant — this is structured data)

- `CostSummary(BaseModel)`:
  - `total_cost_usd: float`
  - `total_tokens: int`
  - `by_department: dict[str, float]`
  - `by_model: dict[str, float]`
  - `burn_rate_per_hour: float`

**Wire cost tracking into company graph**:

- **Update `core/graph.py`** or post-processing:
  - After each task, record a `CostRecord`
  - Model and token count from the model router / LLM response metadata

**Dashboard cost page**:

- **Update `io/dashboard_api/routes.py`**:
  - `GET /api/costs` — cost summary
  - `GET /api/costs/department/{dept}` — per-department breakdown
  - `GET /api/costs/burn-rate` — current burn rate
- **Dashboard frontend** (`dashboard/app/costs/page.tsx`):
  - Token usage over time (chart)
  - Cost per department (bar chart)
  - Model routing distribution (pie chart)
  - Budget burn rate with ceiling line
  - Alert indicator when approaching ceiling

---

### Workstream 3 — Lane Tuning

**`infra/lane_analyzer.py`** — Lane distribution analysis:

- `LaneStats(BaseModel)`:
  - `total_requests: int`
  - `instant_count: int`
  - `fast_count: int`
  - `deep_count: int`
  - `instant_pct: float`
  - `false_positive_rate: float` — deep requests that should have been instant
  - `false_negative_rate: float` — instant requests that were misrouted as deep

- `LaneAnalyzer` class:
  - `analyze(requests: list[dict]) -> LaneStats` — compute lane distribution
  - `suggest_threshold_changes(stats: LaneStats) -> list[str]` — recommend dispatcher adjustments

- **Target: 90% of test requests classified as `instant`**
  - If under 90%, tune `core/dispatcher.py` keyword lists
  - Add more instant keywords, tighten deep keywords

**Update `core/dispatcher.py`**:
- Metrics: count requests per lane (via telemetry/cost_tracker)
- Expose lane stats via dashboard API

---

### Workstream 4 — Security Audit

**Comprehensive audit of all three security layers** (see `docs/SECURITY_ARCHITECTURE.md`):

**Layer 1 — Tool Gates (Guardian):**
- [ ] Every tool call routes through Guardian — no bypass paths
- [ ] `Permission.READ` → auto-allowed with logging
- [ ] `Permission.WRITE` → auto-allowed with audit trail
- [ ] `Permission.SHELL` → pauses for approval
- [ ] `Permission.DESTRUCTIVE` → pauses for explicit approval + confirmation
- [ ] Composio tools get the same enforcement as built-in tools
- [ ] MCP tools get the same enforcement

**Layer 2 — Code Review Gate (SecurityGate):**
- [ ] Every code-producing department has SecurityGate wired
- [ ] SecurityGate checks: injection, secrets, auth, input validation, deserialization
- [ ] SecurityGate failures count toward `max_revisions`
- [ ] Non-code departments don't have SecurityGate (correct — Layer 1 still applies)

**Layer 3 — Continuous Scanning (for future use — verify foundations):**
- [ ] Brain notes don't contain PII/secrets
- [ ] Git history doesn't contain secrets
- [ ] All dependencies checked for known CVEs
- [ ] `.env` files in `.gitignore`

**Additional security checks:**
- [ ] API authentication on all mutating dashboard endpoints
- [ ] WebSocket authentication at connection time
- [ ] CORS restricted (no wildcard)
- [ ] Security headers on all responses
- [ ] OAuth tokens encrypted at rest
- [ ] OAuth scopes are minimal
- [ ] No command injection in BashTool
- [ ] No path traversal in FileTool
- [ ] No SSRF in WebTool
- [ ] No unsafe deserialization anywhere
- [ ] No eval/exec outside sandboxed tools

**`tests/test_security/test_full_audit.py`** — automated security checks:
- Scan all Tool subclasses for correct Permission declaration
- Scan all department sub-graphs for SecurityGate presence (code-producing only)
- Verify Guardian is in the tool execution path (mock a tool call, assert Guardian.check_permission called)
- Verify no secrets in codebase (regex scan for common patterns)
- Verify no unsafe imports (pickle, yaml.load without SafeLoader)

---

### Workstream 5 — Load Test the Daemon

**`tests/test_load/test_daemon_soak.py`** — soak test:

- Run daemon for extended period (simulate 48h with accelerated timer)
- Inject synthetic requests at varying rates:
  - 80% instant, 15% fast, 5% deep (matches lane discipline target)
  - Burst: 10x rate for 5 minutes, then back to baseline
- Verify:
  - No memory leaks (memory usage stays bounded)
  - Checkpoint file size stays bounded (doesn't grow unbounded)
  - No concurrent tick interference (ticks don't overlap)
  - Correct recovery after simulated OOM kill
  - Daemon handles graceful shutdown mid-load
  - All departments respond without hanging
  - Cost stays within ceiling

- `SyntheticRequestGenerator` class:
  - `generate(count: int, lane_distribution: dict) -> list[dict]` — creates test requests
  - Requests span all departments

---

### Workstream 6 — Checkpointer: MemorySaver → Postgres

**Update `infra/checkpointer.py`**:

- `CheckpointerConfig(BaseModel)`:
  - `backend: Literal["memory", "sqlite", "postgres"]`
  - `connection_string: str | None` — for postgres (from env var `DATABASE_URL`)
  - `pool_size: int` — connection pool size (default: 5)

- `get_checkpointer(config: CheckpointerConfig | None = None) -> BaseCheckpointSaver`:
  - `"memory"` → `MemorySaver` (tests, development)
  - `"sqlite"` → `SqliteSaver` (intermediate, local)
  - `"postgres"` → `PostgresSaver` (production)
  - Default: read from env var `CHECKPOINTER_BACKEND`, fallback to `"memory"`

- **Migration script** (`infra/migrate_checkpoints.py`):
  - `async def migrate(source: BaseCheckpointSaver, target: BaseCheckpointSaver)` — copy all checkpoints
  - Verify: state is identical after migration
  - Dry-run mode: compare without writing

- **Connection pooling**: use `asyncpg` or `psycopg` pool for Postgres
- **Add new deps**: `langgraph-checkpoint-postgres`, `asyncpg` or `psycopg[pool]`

- **Verify resume-after-restart** still works with Postgres backend

---

## Tests to write

### `tests/test_infra/test_eval_harness.py`
- `EvalCase` validates required fields
- `register_eval` adds case to harness
- `run_eval` invokes company graph with fixed input and checks traits
- `run_eval` reports token and time usage
- `run_all` runs all registered evals
- `run_department` filters to one department's evals
- Regression detected: output missing expected traits → `passed=False`
- Cost eval detected: tokens exceed ceiling → `within_budget=False`

### `tests/test_infra/test_cost_tracker.py`
- `record` saves a cost record
- `get_total` returns correct total
- `get_by_department` filters correctly
- `get_by_model` filters correctly
- `get_burn_rate` computes cost per hour
- `check_ceiling` returns True when under, False when over
- `CostSummary` aggregates correctly

### `tests/test_infra/test_lane_analyzer.py`
- `analyze` computes correct percentages
- `analyze` identifies false positives and false negatives
- `suggest_threshold_changes` recommends adjustments when instant < 90%

### `tests/test_infra/test_checkpointer_postgres.py`
- `get_checkpointer("memory")` returns `MemorySaver`
- `get_checkpointer("sqlite")` returns `SqliteSaver`
- `get_checkpointer("postgres")` returns `PostgresSaver` (mock connection)
- Config reads from env var
- Migration copies checkpoints between backends (mock both)
- Resume-after-restart works with Postgres backend (integration test)

### `tests/test_security/test_full_audit.py`
- All Tool subclasses declare a Permission level
- All code-producing department sub-graphs have SecurityGate
- Guardian is in the tool execution path
- No secrets patterns found in codebase
- No unsafe imports (pickle, yaml.load)
- API endpoints require auth where expected

### `tests/test_load/test_daemon_soak.py`
- Daemon handles 1000+ synthetic requests without crash
- Memory usage stays bounded (no leak)
- Checkpoint file size stays bounded
- No concurrent tick overlap
- Recovery after simulated kill
- Cost stays within ceiling

### `tests/test_evals/test_eval_all.py`
- Every department's eval case passes
- Every department stays within token budget
- Every department stays within time budget

---

## Exit gate (ALL must pass)

- [ ] Every department has a regression eval + cost eval in CI
- [ ] `EvalHarness.run_all()` passes — all departments produce expected output traits
- [ ] Cost evals: every department within token and time budgets
- [ ] `CostTracker` records per-task costs with department and model breakdown
- [ ] Cost dashboard page shows: token usage over time, cost per department, burn rate
- [ ] Lane distribution: ≥90% of test requests classified as `instant`
- [ ] Lane analyzer reports false positive/negative rates
- [ ] **Security audit passes**: no secrets in code, permissions enforced, inputs validated, SecurityGate on all code-producing departments
- [ ] Automated security test suite (`test_full_audit.py`) passes
- [ ] Daemon load test: 1000+ synthetic requests, no crash, no memory leak
- [ ] Checkpoint size stays bounded under load
- [ ] **Postgres checkpointer works** with resume-after-restart
- [ ] Migration script copies checkpoints between backends
- [ ] **Daemon runs unattended for 48 hours** with no crash
  - [ ] Intelligence briefings generated automatically during 48h run
  - [ ] Reflector improves playbooks during 48h run
  - [ ] Costs within defined ceiling during 48h run
- [ ] All `pytest` green, all evals green, `npm test` green
- [ ] **The system runs autonomously: daemon ticks → Intelligence briefs → Reflector improves playbooks → departments handle requests → Guardian gates dangerous actions → dashboard shows it all live**

---

## Non-negotiable rules

- Layer rule: agents call Tools, never raw `subprocess`
- No if-elif dispatch — use the registry
- Bounded critic loop: `max_revisions = 3`, then escalate. NEVER unbounded.
- Typed state only — nothing outside `AgentState`
- One class = one agent (single responsibility)
- Evals run through the REAL company graph (no mocked shortcuts)
- Cost ceiling is a hard limit — daemon STOPS when ceiling is hit
- Security audit is pass/fail — no partial credit
- The 48h soak test is mandatory — no skipping or shortening
- This is the final phase — everything must work together

## Security checklist (enforced at VERIFY step)

- [ ] Full three-layer security audit passes (Tool Gates + Code Review Gate + Continuous Scanning foundations)
- [ ] No secrets in codebase, git history, or brain notes
- [ ] All tool calls route through Guardian
- [ ] All code-producing departments have SecurityGate
- [ ] API authentication enforced on all mutating endpoints
- [ ] OAuth tokens encrypted and scoped minimally
- [ ] No injection, path traversal, SSRF, or deserialization vulnerabilities
- [ ] Postgres connection string loaded from env var, never hardcoded
- [ ] Database connection uses TLS
- [ ] Checkpoint data doesn't contain raw secrets

## Architecture diagram

```
                    THE COMPLETE AGENT-OS SYSTEM
  ┌──────────────────────────────────────────────────────────────────────┐
  │                                                                      │
  │  ┌────────────┐  ┌──────────────┐  ┌────────────────────────────┐  │
  │  │  VOICE I/O │  │  DASHBOARD   │  │  EXTERNAL INTEGRATIONS     │  │
  │  │  STT → TTS │  │  Next.js     │  │  Composio: Gmail/Notion/   │  │
  │  │  ACK-first │  │  WebSocket   │  │  Slack/GitHub/Calendar     │  │
  │  │            │  │  REST API    │  │  MCP: external tool servers │  │
  │  └─────┬──────┘  └──────┬───────┘  └──────────┬─────────────────┘  │
  │        │                │                      │                    │
  │        └────────────────┼──────────────────────┘                    │
  │                         │                                           │
  │                    ┌────▼─────┐                                     │
  │                    │ EVENT BUS│                                     │
  │                    └────┬─────┘                                     │
  │                         │                                           │
  │  ┌──────────────────────▼──────────────────────────────────────┐   │
  │  │                    COMPANY GRAPH                              │   │
  │  │                                                              │   │
  │  │  Request → [Dispatcher] → lane → [Orchestrator] → dept      │   │
  │  │                                                              │   │
  │  │  ┌──────────────────────────────────────────────────────┐   │   │
  │  │  │  DEPARTMENTS (all registered, registry-dispatched)    │   │   │
  │  │  │                                                      │   │   │
  │  │  │  Engineering · Intelligence · Backend (4) ·           │   │   │
  │  │  │  Frontend (3) · Quality (2) · DevOps (3) ·           │   │   │
  │  │  │  AI/ML (2) · Growth (4) · Sales/Ops (3) ·           │   │   │
  │  │  │  Perception (3) · Dev Experience (8)                 │   │   │
  │  │  │                                                      │   │   │
  │  │  │  Each: [Proposer] → [Worker] → [Critic] →           │   │   │
  │  │  │        [SecurityGate*] → approve/revise/escalate     │   │   │
  │  │  │        (* code-producing only)                       │   │   │
  │  │  └──────────────────────────────────────────────────────┘   │   │
  │  │                                                              │   │
  │  │  [Outcome Recording] → brain                                │   │
  │  │  [Cost Recording] → cost tracker                            │   │
  │  └─────────────────────────────────────────────────────────────┘   │
  │                         │                                           │
  │  ┌──────────────────────▼──────────────────────────────────────┐   │
  │  │                      SAFETY LAYER                            │   │
  │  │                                                              │   │
  │  │  [Guardian] ←── every tool call routes through here         │   │
  │  │     READ → allow    SHELL → interrupt    DESTR → confirm    │   │
  │  │  [Kill Switch] ←── cost/time ceiling or manual              │   │
  │  └─────────────────────────────────────────────────────────────┘   │
  │                                                                     │
  │  ┌──────────────────────────────────────────────────────────────┐  │
  │  │                      BRAIN LAYER                              │  │
  │  │                                                              │  │
  │  │  [Obsidian] ── notes, backlinks, #briefing, #playbook       │  │
  │  │  [Qdrant]   ── semantic search, embeddings                  │  │
  │  │  [Librarian] ── read-before-act query API                   │  │
  │  │  [Reflector] ── outcomes → playbooks → better drafts        │  │
  │  └─────────────────────────────────────────────────────────────┘  │
  │                                                                     │
  │  ┌──────────────────────────────────────────────────────────────┐  │
  │  │                    INFRASTRUCTURE                              │  │
  │  │                                                              │  │
  │  │  [Daemon]        ── heartbeat, tick, resume-after-restart    │  │
  │  │  [Checkpointer]  ── Postgres (prod), MemorySaver (dev)      │  │
  │  │  [Model Router]  ── Claude/Gemini/local per task type        │  │
  │  │  [Cost Tracker]  ── per-task token + dollar tracking         │  │
  │  │  [Eval Harness]  ── regression + cost evals in CI           │  │
  │  │  [Lane Analyzer] ── 90% instant target, tuning              │  │
  │  │  [Telemetry]     ── structured JSON logging                 │  │
  │  └─────────────────────────────────────────────────────────────┘  │
  │                                                                     │
  │  THE AUTONOMOUS LOOP:                                               │
  │    Daemon ticks → Intelligence briefs → Reflector improves →       │
  │    departments handle requests → Guardian gates actions →          │
  │    dashboard shows it all live → costs tracked → evals pass        │
  └──────────────────────────────────────────────────────────────────────┘
```

## Key design decisions

1. **Evals are real invocations** — eval cases run through the actual company graph, not mocked shortcuts. This means evals test the full pipeline: dispatcher → orchestrator → department triad → outcome recording. If the eval passes, the real system works.

2. **Cost ceiling is a hard stop** — when `CostTracker.check_ceiling()` returns False, the daemon stops. This is wired into the Guardian kill switch. There is no "soft warning then continue" mode. Production cost control requires a hard limit.

3. **Postgres is opt-in** — the checkpointer defaults to `MemorySaver` for tests and dev. Postgres is only used when `CHECKPOINTER_BACKEND=postgres` is set. This means existing tests don't break and local development stays lightweight.

4. **The 48h soak test is the real gate** — all other exit criteria are prerequisites. The soak test is what proves agent-os actually works as an autonomous system. If it crashes, leaks memory, or blows through the cost ceiling in 48h, the phase isn't done.

5. **Lane tuning is data-driven** — the LaneAnalyzer doesn't guess. It computes actual distribution from recorded requests, identifies false positives/negatives, and recommends specific threshold changes. The 90% instant target comes from the engineering principles.

6. **Security audit is automated + manual** — `test_full_audit.py` catches the automatable checks (permissions, imports, patterns). The manual review (by @security-auditor) catches design-level issues. Both must pass.

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
- **Celebrate** — agent-os is complete.
