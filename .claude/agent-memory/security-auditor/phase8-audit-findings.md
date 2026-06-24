---
name: phase8-audit-findings
description: Security audit findings for Phase 8 (Harden & Scale) -- unauthenticated cost endpoints, Postgres DSN logging risk, no path validation on storage/db paths
metadata:
  type: project
---

Phase 8 introduced EvalHarness (YAML-based eval runner), CostTracker (JSON file storage), LaneAnalyzer (dispatcher stats), infra Checkpointer (memory/SQLite/Postgres), cost dashboard endpoints, full security audit test suite, and daemon soak tests.

Key findings:
1. **Cost endpoints missing auth** (MEDIUM) -- GET /api/costs, /api/costs/department/{dept}, /api/costs/burn-rate lack `require_auth` dependency
2. **No path validation on cost_tracker storage_path** (LOW) -- user-supplied path resolves but no containment; mkdir parents=True could create dirs anywhere on disk
3. **No path validation on SQLite db_path** (LOW) -- env var AGENT_OS_CHECKPOINTER_DB_PATH passed directly to SqliteSaver.from_conn_string, no containment check
4. **Postgres DSN in env var** (INFO) -- DSN may contain credentials; safe from logging (confirmed not logged), but no warning in docs
5. **YAML safe_load used correctly** (PASS) -- eval_harness.py:50 uses yaml.safe_load, not yaml.load

Good patterns confirmed in Phase 8:
- yaml.safe_load (not yaml.load) in eval harness
- No subprocess/eval/exec/pickle in any new infra file
- No hardcoded secrets or API keys
- Connection string not logged
- Pydantic Literal type constrains checkpointer backend to three values
- Cost endpoint /costs/burn-rate validates window_hours (ge=1, le=720)
- RequestBody validates request length (min=1, max=5000)
- test_full_audit.py comprehensively tests permissions, secrets, SSRF, path traversal, unsafe imports
- Auth HMAC comparison is constant-time (hmac.compare_digest)
- All mutating endpoints (POST) require auth

**Why:** Phase 8 is "Harden & Scale" -- finding auth gaps here is especially important since hardening is the stated goal.

**How to apply:** Finding #1 (missing auth on cost endpoints) is the priority fix. Findings #2 and #3 are low risk (internal API, env-var-controlled paths) but worth noting for defense-in-depth.
