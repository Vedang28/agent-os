# Phase 8 — Harden & Scale

> **Prerequisite:** Phase 7 exit gate must pass.
> **Final phase.** Focus: reliability, security, cost control.

## How to run this phase

**Recommended — Workflow for audit, then targeted fixes:**
Say: `Run a workflow to audit agent-os for security, performance, and reliability issues`

Then fix issues manually or with targeted agents.

---

## Workstreams

### 1. Eval harness per department
- Every department already has one eval test (from Phase 7)
- Add **regression eval**: a fixed input that must produce a stable output
- Add **cost eval**: verify token usage stays under budget for standard tasks
- Wire all evals into CI as a required check

### 2. Cost dashboards
- `infra/cost_tracker.py`:
  - Track tokens used per department, per task, per model
  - Track wall-clock time per task
  - Alert when approaching budget ceiling
- Dashboard integration: new `/costs` page showing:
  - Token usage over time (by department)
  - Cost per task type
  - Model routing distribution
  - Budget burn rate

### 3. Lane tuning
- Analyze: what % of requests go to each lane?
- Target: 90% of requests should be `instant` (never enter the company)
- Tune Dispatcher thresholds
- Add metrics: lane distribution, false-positive rate (deep requests that should have been instant)

### 4. Security audit
- **Secrets:** no API keys, tokens, or passwords in code or brain vault
- **Tool permissions:** verify Guardian enforces all permission levels
- **OAuth scopes:** Composio tools request minimum necessary scopes
- **Input validation:** all external inputs sanitized before reaching tools
- **Path traversal:** FileTool validates paths against allowed directories
- **Injection:** BashTool sanitizes inputs (no shell injection)
- **Brain isolation:** no PII in brain notes unless explicitly allowed

### 5. Load test the daemon
- Run daemon for extended period with synthetic requests
- Verify:
  - No memory leaks
  - Checkpoint file doesn't grow unbounded
  - Concurrent ticks don't interfere
  - Recovery after OOM kill

### 6. Swap checkpointer: SQLite → Postgres
- Replace SQLite checkpointer with Postgres
- Migration script for existing checkpoints
- Verify resume-after-restart still works
- Connection pooling configured

---

## Exit gate (ALL must pass)
- [ ] Every department has regression eval + cost eval in CI
- [ ] Cost dashboard shows token usage by department
- [ ] Lane distribution: ≥90% of test requests classified as `instant`
- [ ] Security audit passes: no secrets in code, permissions enforced, inputs validated
- [ ] Daemon runs **unattended for 48 hours** with no crash
- [ ] Briefings generated automatically during 48h run
- [ ] Costs within defined ceiling during 48h run
- [ ] Postgres checkpointer works with resume-after-restart
- [ ] All `pytest` green, all evals green
- [ ] **The system runs autonomously: daemon ticks → Intelligence briefs → Reflector improves playbooks → departments handle requests → Guardian gates dangerous actions → dashboard shows it all live**


## Verification
After building, run the full **Verification Protocol** from `prompts/VERIFICATION_PROTOCOL.md`:
1. `@test-runner` — all tests green
2. `@architect` + `/code-review high` — no layer violations, no bugs
3. `@security-auditor` + `/security-review` — no injection, no secrets, no SSRF
4. `@gate-checker` — all exit criteria pass with evidence
