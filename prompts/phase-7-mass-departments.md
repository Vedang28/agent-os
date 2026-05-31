# Phase 7 — Mass-Produce Departments

> **Prerequisite:** Phase 6 exit gate must pass.
> **Parallel tracks — split the catalog.** Track A = Backend + DevOps + AI/ML. Track B = Frontend + Growth + Sales/Ops. Perception is shared.

## How to run this phase

**This is the biggest phase.** Use agent view with worktree isolation for maximum parallelism.

**Recommended — Parallel agent view:**
```
claude agents
```

Dispatch Track A departments (each in its own worktree):
1. `@spine-builder Build Backend division: Backend, Database, Auth, API Gateway departments`
2. `@spine-builder Build DevOps division: DevOps, Cloud/Infra, Observability departments`
3. `@spine-builder Build AI/ML division: AI Agent, ML departments`

Dispatch Track B departments:
4. `@edge-builder Build Frontend division: Frontend Build, Frontend Design, Graphics departments`
5. `@edge-builder Build Growth division: Trends, Marketing, Lead Gen, SEO departments — wire Gmail/Notion/Slack tools`
6. `@edge-builder Build Sales/Ops division: SDR, Customer Support, Finance/Compliance departments`

Shared:
7. `Build Perception division: Screen-watcher, Vision-reader, Frame-critic departments`
8. `Build Quality division: Testing, UI Testing departments`

Verify each:
9. `@gate-checker Verify Phase 7 exit gate — all departments have passing tests`

---

## Pattern for every department

Each department = ~4 files + sub-graph + ONE registry line. Copy the Engineering pattern:

```
/agents/departments/<name>/
    __init__.py
    <proposer>.py    # reads brain, produces draft
    <worker>.py      # executes draft using tools, produces result
    <critic>.py      # reviews result, approves or revises (max_revisions=3)
    graph.py         # sub-graph: START → proposer → worker → critic → [approve|revise]
```

Register in `agents/registry.py` — one line per department.

### Division catalog (from AGENT_ROSTER.md)

| Division | Departments | Agent count |
|----------|------------|-------------|
| Backend | Backend, Database, Auth, API Gateway | 16 |
| Frontend | Frontend Build, Frontend Design, Graphics | 12 |
| Quality | Testing, UI Testing | 7 |
| DevOps | DevOps, Cloud/Infra, Observability | 11 |
| AI/ML | AI Agent, ML | 8 |
| Growth | Trends, Marketing, Lead Gen, SEO | 12 |
| Sales/Ops | SDR, Customer Support, Finance/Compliance | 9 |
| Perception | Screen, Video, Document-reading | 9 |
| **Dev Experience** | Code Review, Testing, Security, Bug Triage, Dependency, Docs, Performance, DevOps/CI | **24** |

**Consult `docs/AGENT_ROSTER.md` for the full list** of agents in each department.

---

## Per-department checklist
For EACH department:
- [ ] Proposer reads brain context before drafting
- [ ] Worker uses appropriate tools from the tool registry
- [ ] Critic reviews with bounded loop (max_revisions = 3)
- [ ] Sub-graph follows the triad pattern
- [ ] Registered in agent registry (one line)
- [ ] **One eval test** that runs the triad end-to-end in CI

---

## Exit gate (ALL must pass)
- [ ] Every department has proposer, worker, critic, and sub-graph
- [ ] Every department is registered in the agent registry
- [ ] Every department has **a passing end-to-end test** through its triad and critic loop
- [ ] All departments wire through the company graph via Orchestrator
- [ ] No department edits the Orchestrator to be added (open/closed principle)
- [ ] All `pytest` green


## Verification
After building, run the full **Verification Protocol** from `prompts/VERIFICATION_PROTOCOL.md`:
1. `@test-runner` — all tests green
2. `@architect` + `/code-review high` — no layer violations, no bugs
3. `@security-auditor` + `/security-review` — no injection, no secrets, no SSRF
4. `@gate-checker` — all exit criteria pass with evidence
