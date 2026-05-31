# Verification Protocol

> Run this after EVERY phase build, BEFORE advancing to the next phase.
> This ensures code is reviewed, tested, secure, and actually works.

## The 5-step verification (run in order)

### Step 1: Test
```
@test-runner Run full test suite and report results
```
- All tests must pass.
- If failures: builders fix → re-run tests → repeat until green.

### Step 2: Code Review
```
@architect Review the code built in this phase against architectural constraints
```
Then run:
```
/code-review high
```
Checks:
- Layer rule compliance (no layer reaches past the one below it)
- Registry pattern (no if-elif dispatch anywhere)
- Single responsibility (one class = one agent)
- State contract (nothing outside AgentState)
- Bounded loops (max_revisions = 3 everywhere)
- Code quality, bugs, readability, DRY

### Step 3: Security Review
```
@security-auditor Audit all code built in this phase
```
Or run:
```
/security-review
```
Checks:
- No command injection in BashTool (shell metacharacters escaped)
- No path traversal in FileTool (paths validated)
- No SSRF in WebTool (internal IPs blocked)
- No secrets in code, brain, or git history
- No unsafe deserialization (pickle, yaml.load)
- No eval/exec outside sandboxed tools
- Permission gates enforced on all tools
- DESTRUCTIVE actions require Guardian approval
- Dashboard endpoints authenticated (Phase 5+)
- OAuth tokens stored securely (Phase 6+)

### Step 4: Feature Verification
Manually verify the key features work:
- Import the main classes and run them
- Execute the happy path end-to-end
- Try edge cases (empty input, malformed data, timeouts)
- Verify the exit gate criteria with real commands, not just "it should work"

### Step 5: Gate Check
```
@gate-checker Verify Phase N exit gate
```
- Every checkbox must PASS with evidence.
- If any fail: fix → re-run from Step 1.

## Only when ALL 5 steps pass

```
/log
```
Then advance to the next phase.

---

## Quick reference: agent view dispatch sequence

```bash
# After builders finish:
@test-runner Run full test suite
@architect Review Phase N code against architectural constraints
@security-auditor Audit all code from Phase N for vulnerabilities
@gate-checker Verify Phase N exit gate

# If all pass:
# /log → next phase
# If any fail:
# Builders fix → re-run from @test-runner
```

## What each agent catches

```
@test-runner       → broken code, regressions, missing coverage
@architect         → layer violations, god objects, if-elif dispatch, unbounded loops
@security-auditor  → injection, path traversal, SSRF, secrets, permission bypass
@gate-checker      → incomplete work, missing files, failing exit criteria
/code-review       → bugs, readability, DRY, performance, edge cases
/security-review   → OWASP top 10, attack vectors, hardcoded credentials
```

## The full build + verify loop (per phase)

```
┌─────────────────────────────────────┐
│  BUILD                              │
│  @spine-builder + @edge-builder     │
│  (parallel, worktree-isolated)      │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  TEST                               │
│  @test-runner                       │
│  All pytest green?                  │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  REVIEW                             │
│  @architect + /code-review high     │
│  No layer violations? No bugs?      │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  SECURITY                           │
│  @security-auditor + /security-review│
│  No injection? No secrets? No SSRF? │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  GATE                               │
│  @gate-checker                      │
│  All exit criteria pass?            │
└──────────────┬──────────────────────┘
               │
          ALL PASS? ──No──→ Fix → back to TEST
               │
              Yes
               ▼
┌─────────────────────────────────────┐
│  /log → advance to next phase       │
└─────────────────────────────────────┘
```
