# Phase 7 — Mass-Produce Departments (Complete Build Prompt)

> Paste this into a new Claude Code session to build Phase 7 of agent-os.
> **This is the biggest phase.** The proven Engineering pattern gets replicated across all remaining divisions.

## Context

Phase 6 is complete. Composio integration provides OAuth-based access to Gmail, Notion, Slack, GitHub, and Calendar. MCP bridge connects to external tool servers. All integration tools register in the tool registry with namespaced names, gated by Guardian permissions. Token storage is encrypted. Two departments (Engineering, Intelligence) are active and battle-tested.

Phase 7 mass-produces the remaining departments from the `AGENT_ROSTER.md` catalog. Each department follows the proven pattern: proposer → worker → critic triad, sub-graph with bounded critic loop (max_revisions=3), registered in the agent registry with one line.

## What exists now

- `core/` — state, graph, dispatcher, orchestrator, checkpointer — full company graph
- `agents/protocol.py` — `Agent` Protocol
- `agents/registry.py` — register/get/list_agents/clear
- `agents/guardian.py` — permission gates, human-in-the-loop interrupt, kill switch
- `agents/security_gate.py` — `SecurityGate` ABC
- `agents/departments/engineering/` — Architect → Scaffolder → CodeDoctor (the reference pattern)
- `agents/departments/intelligence/` — Scout → Analyst → Skeptic
- `tools/base.py` — `Tool` ABC with `Permission` enum, Guardian-gated execution
- `tools/registry.py` — tool registry (built-in + Composio + MCP namespaced)
- `tools/bash.py`, `tools/file.py`, `tools/web.py` — built-in tools
- `integrations/composio.py` — Composio bridge, OAuth, tool wrappers
- `integrations/mcp.py` — MCP bridge, tool discovery
- `integrations/tools/` — gmail, notion, slack, github, calendar tool wrappers
- `integrations/token_store.py` — encrypted token storage
- `brain/` — schema, obsidian, qdrant, librarian, reflector, outcome, playbook
- `infra/` — daemon, model_router, telemetry
- `io/` — dashboard_api, voice, event_bus
- `dashboard/` — Next.js frontend

## Workflow to follow

STEP 1: /start-phase (load context, verify Phase 6 gate still passes)
STEP 2: PLAN — enter plan mode, design the division split, get approval
STEP 3: BUILD — use parallel agents with worktree isolation for maximum throughput
STEP 4: TEST — each department must have one eval test, run full pytest
STEP 5: VERIFY (5-step verification protocol):
5a. @test-runner → all tests green
5b. @architect + /code-review high → no layer violations
5c. @security-auditor + /security-review → no injection, no secrets, code-producing departments have SecurityGate
5d. @gate-checker → all exit criteria pass with evidence
5e. Fix any failures → re-run from 5a
STEP 6: /log → commit → push

## How to run this phase

**This is the biggest phase.** Use parallel agents with worktree isolation.

**Recommended — Parallel agent view:**
```
claude agents
```

Dispatch Track A (spine divisions — each in its own worktree):
1. `@spine-builder Build Backend division: Backend, Database, Auth, API Gateway departments in /agents/departments/backend/`
2. `@spine-builder Build DevOps division: DevOps, Cloud/Infra, Observability departments in /agents/departments/devops/`
3. `@spine-builder Build AI/ML division: AI Agent, ML departments in /agents/departments/ai_ml/`
4. `@spine-builder Build Dev Experience division (24 agents): Code Review, Testing, Security, Bug Triage, Dependency, Docs, Performance, DevOps/CI departments in /agents/departments/dev_experience/`

Dispatch Track B (edge divisions):
5. `@edge-builder Build Frontend division: Frontend Build, Frontend Design, Graphics departments in /agents/departments/frontend/`
6. `@edge-builder Build Growth division: Trends, Marketing, Lead Gen, SEO departments — wire Gmail/Notion/Slack tools — in /agents/departments/growth/`
7. `@edge-builder Build Sales/Ops division: SDR, Customer Support, Finance/Compliance departments in /agents/departments/sales_ops/`

Shared:
8. `Build Perception division: Screen, Video, Document-reading departments in /agents/departments/perception/`
9. `Build Quality division: Testing, UI Testing departments in /agents/departments/quality/`

Verify:
10. `@gate-checker Verify Phase 7 exit gate — every department has passing tests`

---

## What to build

### The pattern (copy for EVERY department)

Each department = ~4 files + sub-graph + ONE registry line:

```
/agents/departments/<division>/<department>/
    __init__.py          # register agents, export build_<dept>_graph
    <proposer>.py        # reads brain + playbooks, produces draft
    <worker>.py          # executes draft using tools, produces result
    <critic>.py          # reviews result, approves or revises (max_revisions=3)
    graph.py             # sub-graph: START → proposer → worker → critic → [approve|revise|escalate]
```

Every proposer:
- Implements `Agent` protocol
- `role = "proposer"`
- Queries brain via `Librarian().query()` (read-before-act)
- Queries playbooks via `get_playbooks(department)` (learning loop)
- Stores context in `state["brain_context"]`
- Produces `state["draft"]`

Every worker:
- Implements `Agent` protocol
- `role = "worker"`
- Takes `state["draft"]` as input
- Uses tools from the tool registry as needed
- Produces `state["result"]`

Every critic:
- Implements `Agent` protocol
- `role = "critic"`
- Reviews `state["result"]` against `state["draft"]`
- Approves or rejects with `state["critique"]`
- Increments `state["revisions"]` on rejection

Every sub-graph:
- `MAX_REVISIONS = 3`
- Conditional edge: approve → END / revise → worker / max_revisions → escalate → END
- `build_<dept>_graph()` → returns compiled sub-graph

Every `__init__.py`:
- Registers all agents in `agents/registry.py`
- Exports `build_<dept>_graph`

**Code-producing departments** also wire the `SecurityGate` as a conditional edge after the critic approves (see `docs/SECURITY_ARCHITECTURE.md`).

---

### Division 1 — Backend (16 agents)

**`/agents/departments/backend/backend/`** — Backend department:
- `backend_architect.py` (proposer) — designs service structure, data flow, contracts
- `api_builder.py` (worker) — writes endpoints, controllers, route handlers. Uses `FileTool`, `BashTool`
- `schema_designer.py` (worker) — defines request/response models, input validation
- `backend_reviewer.py` (critic) — catches N+1 queries, blocking calls, contract drift
- `graph.py` — sub-graph with SecurityGate (code-producing)

**`/agents/departments/backend/database/`** — Database department:
- `database_architect.py` (proposer) — schema design, normalization, indexing
- `query_writer.py` (worker) — SQL, migrations. Uses `FileTool`, `BashTool`
- `migration_runner.py` (worker) — applies migrations with rollback plans
- `data_integrity_critic.py` (critic) — constraints, foreign keys, race conditions
- `graph.py` — sub-graph with SecurityGate

**`/agents/departments/backend/auth/`** — Auth department:
- `auth_architect.py` (proposer) — auth flows (OAuth, JWT, sessions)
- `token_manager.py` (worker) — issues, rotates, validates tokens
- `access_control_builder.py` (worker) — RBAC/ABAC rules, permission matrices
- `auth_critic.py` (critic) — privilege escalation, leaked tokens, insecure flows
- `graph.py` — sub-graph with SecurityGate

**`/agents/departments/backend/api_gateway/`** — API Gateway department:
- `gateway_architect.py` (proposer) — routing, API versioning
- `rate_limit_engineer.py` (worker) — throttling, quotas, backpressure
- `cache_strategist.py` (worker) — cache keys, TTLs, invalidation
- `load_critic.py` (critic) — hotspots, thundering herd, unfair throttling
- `graph.py` — sub-graph with SecurityGate

---

### Division 2 — Frontend (12 agents)

**`/agents/departments/frontend/build/`** — Frontend Build department:
- `frontend_architect.py` (proposer) — component structure, state management
- `component_builder.py` (worker) — React/Next components. Uses `FileTool`
- `state_wirer.py` (worker) — hooks, data fetching, form wiring
- `frontend_reviewer.py` (critic) — accessibility, re-render perf, prop-drilling
- `graph.py` — sub-graph with SecurityGate

**`/agents/departments/frontend/design/`** — UI/UX department:
- `ux_designer.py` (proposer) — flows, wireframes, IA
- `ui_stylist.py` (worker) — design tokens, theming, layout
- `interaction_designer.py` (worker) — motion, transitions, micro-interactions
- `design_critic.py` (critic) — visual consistency, hierarchy, brand
- `graph.py` — sub-graph (non-code: no SecurityGate)

**`/agents/departments/frontend/graphics/`** — Graphics department:
- `art_director.py` (proposer) — visual direction, composition
- `asset_generator.py` (worker) — icons, illustrations, assets
- `brand_keeper.py` (worker) — logo, palette, typography consistency
- `graphics_critic.py` (critic) — resolution, alignment, export correctness
- `graph.py` — sub-graph (non-code: no SecurityGate)

---

### Division 3 — Quality (7 agents)

**`/agents/departments/quality/testing/`** — Testing department:
- `test_strategist.py` (proposer) — coverage plan
- `test_writer.py` (worker) — unit + integration tests. Uses `FileTool`, `BashTool`
- `test_runner_agent.py` (worker) — executes suites, reports failures
- `bug_triager.py` (critic) — severity classification, root causes
- `graph.py` — sub-graph with SecurityGate

**`/agents/departments/quality/ui_testing/`** — UI Testing department:
- `visual_test_designer.py` (proposer) — visual test cases
- `playwright_operator.py` (worker) — browser automation. Uses `BashTool`
- `visual_regression_critic.py` (critic) — screenshot diffs, pixel drift
- `graph.py` — sub-graph with SecurityGate

---

### Division 4 — DevOps & Cloud (11 agents)

**`/agents/departments/devops/devops/`** — DevOps department:
- `cicd_architect.py` (proposer) — pipeline design
- `pipeline_builder.py` (worker) — build scripts, workflow files. Uses `FileTool`, `BashTool`
- `release_manager.py` (worker) — versioning, changelogs, deploy gates
- `deploy_critic.py` (critic) — rollbacks, env parity, secrets in CI
- `graph.py` — sub-graph with SecurityGate

**`/agents/departments/devops/cloud_infra/`** — Cloud/Infra department:
- `cloud_architect.py` (proposer) — infra topology, IaC
- `provisioner.py` (worker) — Terraform/Docker/K8s. Uses `FileTool`, `BashTool`
- `cost_watcher.py` (worker) — cost tracking, right-sizing
- `reliability_critic.py` (critic) — SLOs, failover, SPOF
- `graph.py` — sub-graph with SecurityGate

**`/agents/departments/devops/observability/`** — Observability department:
- `telemetry_engineer.py` (worker) — logs, metrics, traces
- `alert_designer.py` (worker) — alert rules, thresholds
- `incident_responder.py` (critic) — error parsing, crash summaries
- `graph.py` — sub-graph with SecurityGate

---

### Division 5 — AI/ML (8 agents)

**`/agents/departments/ai_ml/ai_agent/`** — AI Agent department:
- `prompt_engineer.py` (proposer) — prompt and system-prompt design
- `tool_function_builder.py` (worker) — tool schemas for function calling
- `model_router_agent.py` (worker) — picks model per task by cost/latency
- `eval_critic.py` (critic) — output quality, hallucination, regressions
- `graph.py` — sub-graph with SecurityGate

**`/agents/departments/ai_ml/ml/`** — ML department:
- `data_curator.py` (proposer) — dataset collection, cleaning, labeling
- `embedding_engineer.py` (worker) — embeddings, Qdrant management
- `trainer.py` (worker) — training/fine-tune runs, eval metrics
- `ml_critic.py` (critic) — overfitting, data leakage, model drift
- `graph.py` — sub-graph with SecurityGate

---

### Division 6 — Growth (12 agents)

**`/agents/departments/growth/trends/`** — Trends/Research department:
- This is the existing Intelligence department — **DO NOT duplicate**
- Just register an alias: `growth.trends` → `intelligence` sub-graph
- Or refactor Intelligence under Growth if the architecture allows

**`/agents/departments/growth/marketing/`** — Marketing department:
- `marketing_strategist.py` (proposer) — campaigns, positioning
- `copywriter.py` (worker) — ad/email/landing page copy. Uses `NotionWriteTool`
- `marketing_critic.py` (critic) — message clarity, CTA strength, brand fit
- `graph.py` — sub-graph (non-code: no SecurityGate)
- Wired tools: `GmailSendTool`, `NotionWriteTool`, `SlackSendTool`

**`/agents/departments/growth/lead_gen/`** — Lead Gen department:
- `prospector.py` (proposer) — finds leads matching ICP
- `enricher.py` (worker) — firmographic and contact data. Uses `WebTool`
- `qualifier.py` (critic) — scores/filters leads, removes junk
- `graph.py` — sub-graph (non-code: no SecurityGate)

**`/agents/departments/growth/seo/`** — SEO department:
- `keyword_scout.py` (proposer) — keyword and search-intent research
- `content_optimizer.py` (worker) — on-page SEO, content structure
- `seo_auditor.py` (critic) — technical SEO, broken links, rankings
- `graph.py` — sub-graph (non-code: no SecurityGate)

---

### Division 7 — Sales & Ops (9 agents)

**`/agents/departments/sales_ops/sdr/`** — SDR/Sales department:
- `outreach_planner.py` (proposer) — sequences and cadences
- `message_writer.py` (worker) — personalized outreach. Uses `GmailSendTool`, `SlackSendTool`
- `reply_handler.py` (critic) — triages responses, books meetings
- `graph.py` — sub-graph (non-code: no SecurityGate)

**`/agents/departments/sales_ops/customer_support/`** — Customer Support department:
- `ticket_triager.py` (proposer) — categorizes, prioritizes
- `resolver.py` (worker) — drafts answers via brain query
- `escalation_critic.py` (critic) — flags what needs a human
- `graph.py` — sub-graph (non-code: no SecurityGate)

**`/agents/departments/sales_ops/finance/`** — Finance/Compliance department:
- `bookkeeper.py` (worker) — categorizes expenses, invoices
- `reporter.py` (worker) — generates summaries, dashboards
- `compliance_critic.py` (critic) — policy/regulatory checks
- `graph.py` — sub-graph (non-code: no SecurityGate)

---

### Division 8 — Perception (9 agents)

**`/agents/departments/perception/screen/`** — Screen department:
- `screen_watcher.py` (worker) — captures frames, detects changes
- `vision_reader.py` (proposer) — interprets frames via vision model
- `frame_critic.py` (critic) — validates reading against raw pixels
- `graph.py` — sub-graph (non-code: no SecurityGate)

**`/agents/departments/perception/video/`** — Video department:
- `video_capturer.py` (worker) — records, samples frames
- `video_summarizer.py` (proposer) — summarizes recordings
- `video_critic.py` (critic) — verifies summary matches footage
- `graph.py` — sub-graph (non-code: no SecurityGate)

**`/agents/departments/perception/document/`** — Document-reading department:
- `doc_ingester.py` (worker) — loads PDFs/docs, splits into chunks
- `doc_extractor.py` (proposer) — extracts text, tables, structure
- `doc_critic.py` (critic) — verifies extraction accuracy
- `graph.py` — sub-graph (non-code: no SecurityGate)

---

### Division 9 — Developer Experience (24 agents, 8 departments)

**Priority: build these early** — they can be dogfooded immediately.

**`/agents/departments/dev_experience/code_review/`**:
- `review_planner.py` (proposer), `reviewer.py` (worker), `review_critic.py` (critic)
- `graph.py` — SecurityGate (code-producing)
- Uses: `GitHubReadRepoTool`, `FileTool`

**`/agents/departments/dev_experience/testing/`**:
- `test_planner.py` (proposer), `test_writer.py` (worker), `test_critic.py` (critic)
- `graph.py` — SecurityGate
- Uses: `FileTool`, `BashTool`

**`/agents/departments/dev_experience/security/`**:
- `security_scanner.py` (proposer), `security_analyst.py` (worker), `security_skeptic.py` (critic)
- `graph.py` — SecurityGate
- Uses: `BashTool`, `FileTool`

**`/agents/departments/dev_experience/bug_triage/`**:
- `bug_classifier.py` (proposer), `bug_reproducer.py` (worker), `bug_validator.py` (critic)
- `graph.py` — SecurityGate
- Uses: `BashTool`, `GitHubCreateIssueTool`

**`/agents/departments/dev_experience/dependency/`**:
- `dep_scanner.py` (proposer), `dep_upgrader.py` (worker), `dep_validator.py` (critic)
- `graph.py` — SecurityGate
- Uses: `BashTool`, `FileTool`

**`/agents/departments/dev_experience/documentation/`**:
- `doc_detector.py` (proposer), `doc_writer.py` (worker), `doc_reviewer.py` (critic)
- `graph.py` — SecurityGate
- Uses: `FileTool`

**`/agents/departments/dev_experience/performance/`**:
- `perf_profiler.py` (proposer), `perf_optimizer.py` (worker), `perf_validator.py` (critic)
- `graph.py` — SecurityGate
- Uses: `BashTool`

**`/agents/departments/dev_experience/devops_ci/`**:
- `ci_monitor.py` (proposer), `ci_fixer.py` (worker), `ci_validator.py` (critic)
- `graph.py` — SecurityGate
- Uses: `BashTool`, `FileTool`, `GitHubReadRepoTool`

---

### Update Orchestrator routing

**Update `core/orchestrator.py`**:
- All new departments register in `agents/registry.py` — orchestrator discovers them automatically
- Each department's `__init__.py` registers keywords with the registry for routing
- Verify: no if-elif in orchestrator to add a department (open/closed principle)

---

## Tests to write

**Each department MUST have one eval test** that runs in CI:

```
tests/test_agents/test_<division>/test_<department>/test_graph.py
```

Per department test file (minimum):
- Happy path: request → proposer → worker → critic approves → done
- Revise path: critic rejects → worker retries → critic approves
- Bounded loop: after `MAX_REVISIONS` (3), escalates
- (Code-producing departments): SecurityGate runs after critic approval

### `tests/test_integration/test_all_departments.py`
- Every registered department can be invoked through the company graph
- Every department produces a non-empty result for a sample request
- No department uses if-elif dispatch in the orchestrator (verify registry-based routing)

### `tests/test_agents/test_registry_complete.py`
- All departments from AGENT_ROSTER.md are registered
- `list_agents()` returns the expected count
- Each agent has a unique name
- Each agent implements the Agent protocol

---

## Exit gate (ALL must pass)

- [ ] Every department has proposer, worker, critic, and sub-graph files
- [ ] Every department follows the triad pattern (proposer → worker → critic → conditional edge)
- [ ] Every department is registered in the agent registry (one line each)
- [ ] Every department has **a passing end-to-end test** through its triad and critic loop
- [ ] Every code-producing department has SecurityGate wired
- [ ] All departments wire through the company graph via Orchestrator
- [ ] **No department edits the Orchestrator to be added** (open/closed principle)
- [ ] `max_revisions = 3` enforced in every department
- [ ] Growth departments have Composio tools wired (Gmail, Notion, Slack)
- [ ] Sales departments have Composio tools wired (Gmail, Slack)
- [ ] Dev Experience departments have GitHub + built-in tools wired
- [ ] All `pytest` green

---

## Non-negotiable rules

- Layer rule: agents call Tools, never raw `subprocess`
- No if-elif dispatch — use the registry everywhere
- Bounded critic loop: `max_revisions = 3`, then escalate. NEVER unbounded.
- Typed state only — nothing outside `AgentState`
- One class = one agent (single responsibility)
- Read-before-act: every proposer queries brain + playbooks before drafting
- SecurityGate: mandatory on ALL code-producing department sub-graphs
- Department = sub-graph + registry line. Adding a department NEVER touches the orchestrator.
- No duplicating tools — use the tool registry
- Each department ships one eval test in CI
- Do NOT build Phase 8 work (hardening, eval harness, Postgres swap)

## Security checklist (enforced at VERIFY step)

- [ ] Every code-producing department has SecurityGate as a conditional edge
- [ ] SecurityGate checks: injection, secrets, auth, input validation, deserialization, path traversal
- [ ] No department bypasses Guardian for tool calls
- [ ] No secrets hardcoded in any agent (API keys, tokens, credentials)
- [ ] Tool permission levels correct for all departments (DESTRUCTIVE tools require approval)
- [ ] No agent calls raw subprocess — all through BashTool
- [ ] No agent accesses files outside allowed paths — all through FileTool
- [ ] No agent makes network calls outside WebTool/Composio — no raw httpx/requests
- [ ] No unsafe deserialization in any department
- [ ] No eval/exec in any department

## Key design decisions

1. **Copy, don't abstract** — each department gets its own files. Don't build a department factory or metaclass. The pattern is simple enough to copy; a premature abstraction would add complexity for no benefit.

2. **Intelligence ≈ Growth.Trends** — the Intelligence department built in Phase 3 IS the Trends department. Either register an alias or restructure under Growth. Don't build a duplicate.

3. **SecurityGate on code producers only** — Marketing, Sales, Perception, and text-only departments don't need the code security gate. They still go through Guardian for tool calls (Layer 1 security), but don't need Layer 2 code review.

4. **Dev Experience is highest priority** — these 24 agents (Code Review, Testing, Security, etc.) can be dogfooded immediately on agent-os itself. Build them first in the phase.

5. **Workers vary by department** — some departments have one worker, some have two (e.g., Backend has `api_builder` + `schema_designer`). The sub-graph handles this: both workers run in sequence or the proposer's draft determines which worker runs.

6. **Thin agents, thick later** — in Phase 7, agents use heuristic logic (like Phase 2-3). They're structurally correct but not LLM-powered yet. Full LLM wiring comes with model router integration in usage.

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
