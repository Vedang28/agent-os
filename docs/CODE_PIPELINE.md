# Code Pipeline

> The 9-stage pipeline every code-producing department runs. No shortcuts, no skipping stages.

## The Pipeline

```
PLAN → SCAFFOLD → BUILD → TEST → DEBUG → REVIEW → AUDIT → PROD-READY → PUSH
```

Every department that produces code follows this exact sequence. Non-code departments (Intelligence, Marketing, Sales, Support) use a simplified version without SCAFFOLD, TEST, DEBUG, or AUDIT.

## Stage-by-Stage

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ┌────────┐   ┌──────────┐   ┌────────┐   ┌────────┐   ┌────────┐  │
│  │  PLAN  │──▶│ SCAFFOLD │──▶│ BUILD  │──▶│  TEST  │──▶│ DEBUG  │  │
│  └────────┘   └──────────┘   └────────┘   └────────┘   └───┬────┘  │
│                                                             │       │
│                                              tests fail ◀───┘       │
│                                              back to BUILD          │
│                                                             │       │
│                                                    all pass ▼       │
│                                                                      │
│  ┌────────┐   ┌────────┐   ┌────────────┐   ┌────────┐             │
│  │  PUSH  │◀──│ AUDIT  │◀──│   REVIEW   │◀──│ DEBUG  │             │
│  └────────┘   └───┬────┘   └─────┬──────┘   └────────┘             │
│                   │              │                                    │
│            fail ──┘  back to     └── fail                            │
│            back to   BUILD           back to BUILD                   │
│            BUILD                                                     │
│                                                                      │
│  Total: 9 stages. Max 3 loops back before escalation.               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 1. PLAN

**Who:** Proposer agent (e.g., Architect, ReviewPlanner, TestPlanner)
**What:** Design the approach before writing a single line of code.

```
Input:  request + brain_context (read-before-act)
Output: plan (list of steps), draft (design document)

Checks:
  ✓ Queried brain for existing patterns and playbooks
  ✓ Plan addresses the actual request, not a tangent
  ✓ Plan identifies files to create/modify
  ✓ Plan considers edge cases
  ✓ Plan estimates scope (token budget, file count)
```

The Proposer reads playbooks from the brain first. If the Reflector has noted "always use parameterized queries for DB work," the plan includes that from the start.

---

### 2. SCAFFOLD

**Who:** Worker agent (scaffolding mode)
**What:** Create the file structure, interfaces, and contracts before implementation.

```
Input:  plan from PLAN stage
Output: skeleton files with interfaces, type signatures, empty test files

Checks:
  ✓ Files created in the correct layer folder
  ✓ Interfaces match the plan's contracts
  ✓ Test files created alongside source files
  ✓ Imports resolve (no circular dependencies)
  ✓ Layer rule not violated (no upward imports)
```

Scaffold first, build second. This catches structural issues before the expensive code generation step.

---

### 3. BUILD

**Who:** Worker agent (implementation mode)
**What:** Fill in the scaffolded files with actual implementation.

```
Input:  scaffolded files + plan
Output: working implementation

Checks:
  ✓ All interfaces from SCAFFOLD are implemented
  ✓ Code follows the plan's design
  ✓ No TODOs or placeholder code left
  ✓ Typed state contract respected
  ✓ Registry pattern used (no if-elif)
  ✓ Tools used via Tool interface, not raw subprocess
```

---

### 4. TEST

**Who:** Testing agent (or Worker in test mode)
**What:** Write tests AND run them.

```
Input:  implemented code from BUILD
Output: test files + test results

Substeps:
  4a. Write unit tests for each public function/class
  4b. Write integration tests for cross-module interactions
  4c. Write edge case tests (empty input, malformed data, timeouts, large input)
  4d. Run full test suite: pytest -v --tb=short
  4e. Check coverage: identify untested paths

Checks:
  ✓ Every public function has at least one test
  ✓ Happy path tested
  ✓ Error/edge cases tested
  ✓ All tests pass
  ✓ No flaky tests (run twice to confirm)
```

If tests fail → go to DEBUG.

---

### 5. DEBUG

**Who:** Worker agent (debug mode)
**What:** Fix any failures from TEST, REVIEW, or AUDIT.

```
Input:  failing tests / review findings / audit findings
Output: fixed code

Process:
  5a. Read the actual error message and stack trace
  5b. Identify root cause (not symptoms)
  5c. Implement minimal targeted fix
  5d. Re-run failing tests to confirm fix
  5e. Run full suite to confirm no regressions

Rules:
  ✗ Never delete a test to make it pass
  ✗ Never swallow errors silently
  ✗ Never widen scope to escape a bug
  ✓ One fix at a time, re-test after each
  ✓ Max 3 debug loops before escalating
```

After DEBUG, return to whichever stage triggered it (TEST, REVIEW, or AUDIT).

---

### 6. REVIEW

**Who:** Critic agent (e.g., CodeDoctor, BackendReviewer, DesignCritic)
**What:** Code review for quality, architecture, and correctness.

```
Input:  implemented + tested code
Output: critique (approved: bool, findings: list)

Review checklist:
  Architecture:
    ✓ Layer rule compliance (no upward dependencies)
    ✓ Single responsibility (one class = one job)
    ✓ Registry pattern (no if-elif dispatch)
    ✓ State contract (nothing outside AgentState)
    ✓ Open/closed (no editing orchestrator to add features)
  
  Quality:
    ✓ Code is readable and well-named
    ✓ No duplicated logic (DRY)
    ✓ Error handling is appropriate (not excessive)
    ✓ No dead code or unreachable paths
    ✓ Performance: no obvious N+1, blocking calls, memory leaks
  
  Correctness:
    ✓ Logic matches the plan's intent
    ✓ Edge cases handled
    ✓ Concurrent access safe where needed
    ✓ Bounded loops (max_revisions = 3)

If findings:
  → approved = False
  → back to DEBUG with specific findings
  → counts toward max_revisions (3 max, then escalate)
```

---

### 7. AUDIT

**Who:** Security Gate (SecurityGate class)
**What:** Security audit against all attack vectors.

```
Input:  reviewed + approved code
Output: security verdict (pass/fail + findings)

Scan for:
  Injection:
    ✓ SQL uses parameterized queries
    ✓ Shell commands sanitized
    ✓ HTML output encoded (XSS)
    ✓ LDAP, XML (XXE) safe
  
  Secrets:
    ✓ No API keys, tokens, passwords in code
    ✓ No secrets in logs or error messages
    ✓ Environment variables used for config
  
  Auth:
    ✓ All endpoints authenticated
    ✓ Authorization on protected resources
    ✓ Passwords hashed properly (bcrypt/argon2)
    ✓ Session tokens cryptographically random
  
  Input:
    ✓ All external inputs validated
    ✓ File paths checked for traversal
    ✓ URLs checked for SSRF
    ✓ Deserialization safe (no pickle/yaml.load)
  
  Dependencies:
    ✓ No known CVEs (critical/high)
    ✓ Versions pinned
  
  Infrastructure:
    ✓ CORS restrictive
    ✓ Security headers set
    ✓ Debug mode off in prod config
    ✓ Rate limiting on public endpoints

If findings:
  → fail
  → back to DEBUG with security-specific fixes required
  → counts toward max_revisions (3 max, then escalate)
```

---

### 8. PROD-READY

**Who:** Production Readiness agent (new agent in each department)
**What:** Final checklist before code is considered shippable.

```
Input:  code that passed TEST + REVIEW + AUDIT
Output: production readiness verdict

Checks:
  Reliability:
    ✓ Error handling covers realistic failure modes
    ✓ Graceful degradation (service continues if a dep is down)
    ✓ Timeouts configured on all external calls
    ✓ Retry logic with backoff (not infinite loops)
    ✓ Circuit breakers where appropriate
  
  Observability:
    ✓ Structured logging on key operations
    ✓ Metrics/counters for monitoring
    ✓ Health check endpoint (if service)
    ✓ Error tracking wired (stack traces, context)
  
  Performance:
    ✓ No obvious bottlenecks under expected load
    ✓ Database queries indexed
    ✓ Caching where beneficial
    ✓ Payload sizes reasonable
  
  Configuration:
    ✓ All config via environment (not hardcoded)
    ✓ Defaults are safe (secure, restrictive)
    ✓ Feature flags for risky changes
  
  Documentation:
    ✓ API documented (if new endpoints)
    ✓ README updated (if new setup steps)
    ✓ Breaking changes noted
  
  Rollback:
    ✓ Change is reversible (can revert without data loss)
    ✓ Database migrations are backward-compatible
    ✓ No destructive schema changes without migration plan

If not ready:
  → back to BUILD with specific items to address
  → counts toward max_revisions (3 max, then escalate)
```

---

### 9. PUSH

**Who:** Worker agent (delivery mode) + Guardian
**What:** Ship the code.

```
Input:  production-ready code
Output: delivered result (PR, commit, deployed artifact)

Steps:
  9a. Guardian final approval (destructive action gate)
  9b. Create commit/PR with:
       - Clear title describing the change
       - Summary of what and why
       - Test results
       - Security audit result
       - Production readiness confirmation
  9c. Deliver to user via:
       - Dashboard notification
       - Slack/email (if integrated)
       - Voice confirmation (if voice request)
  9d. Log outcome to brain for Reflector
```

---

## Failure Handling

```
Stage fails → DEBUG → re-run failing stage → pass?
                                                │
                                           Yes: continue
                                           No:  increment revisions
                                                │
                                        revisions > 3?
                                           │
                                      Yes: ESCALATE
                                           → Guardian notified
                                           → Human-in-the-loop
                                           → Dashboard alert
                                           → No silent failure
                                      No:  back to DEBUG
```

**Max 3 loops** across all stages combined. If BUILD fails TEST 2 times and then REVIEW fails once, that's 3 — next failure escalates. No unbounded loops.

---

## Pipeline Implementation (LangGraph)

Each department's sub-graph follows this structure:

```python
from langgraph.graph import StateGraph, START, END

def build_department_graph(department):
    graph = StateGraph(AgentState)
    
    # The 9 stages
    graph.add_node("plan", department.proposer.plan)
    graph.add_node("scaffold", department.worker.scaffold)
    graph.add_node("build", department.worker.build)
    graph.add_node("test", department.tester.test)
    graph.add_node("debug", department.worker.debug)
    graph.add_node("review", department.critic.review)
    graph.add_node("audit", department.security_gate.review)
    graph.add_node("prod_ready", department.prod_checker.check)
    graph.add_node("push", department.worker.push)
    
    # Happy path
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "scaffold")
    graph.add_edge("scaffold", "build")
    graph.add_edge("build", "test")
    
    # TEST → pass: REVIEW / fail: DEBUG → BUILD
    graph.add_conditional_edges("test", route_test)
    
    # DEBUG → back to whichever stage triggered it
    graph.add_conditional_edges("debug", route_debug)
    
    # REVIEW → pass: AUDIT / fail: DEBUG
    graph.add_conditional_edges("review", route_review)
    
    # AUDIT → pass: PROD-READY / fail: DEBUG
    graph.add_conditional_edges("audit", route_audit)
    
    # PROD-READY → pass: PUSH / fail: BUILD
    graph.add_conditional_edges("prod_ready", route_prod_ready)
    
    graph.add_edge("push", END)
    
    return graph.compile()
```

---

## Pipeline for Non-Code Departments

Intelligence, Marketing, Sales, Support use a simplified 5-stage pipeline:

```
PLAN → DRAFT → REVIEW → FACT-CHECK → DELIVER

  PLAN:       Read brain, design approach
  DRAFT:      Write the content
  REVIEW:     Critic checks quality, accuracy, tone
  FACT-CHECK: Verify claims, sources, data
  DELIVER:    Ship to user + log outcome
```

No SCAFFOLD, TEST, DEBUG, AUDIT, or PROD-READY since they produce text, not code.

---

## Pipeline Map by Department

| Department | Pipeline | Stages |
|---|---|---|
| Engineering | Full code | PLAN → SCAFFOLD → BUILD → TEST → DEBUG → REVIEW → AUDIT → PROD-READY → PUSH |
| Backend (all) | Full code | PLAN → SCAFFOLD → BUILD → TEST → DEBUG → REVIEW → AUDIT → PROD-READY → PUSH |
| Frontend (all) | Full code | PLAN → SCAFFOLD → BUILD → TEST → DEBUG → REVIEW → AUDIT → PROD-READY → PUSH |
| DevOps | Full code | PLAN → SCAFFOLD → BUILD → TEST → DEBUG → REVIEW → AUDIT → PROD-READY → PUSH |
| AI/ML | Full code | PLAN → SCAFFOLD → BUILD → TEST → DEBUG → REVIEW → AUDIT → PROD-READY → PUSH |
| Dev Experience (all) | Full code | PLAN → SCAFFOLD → BUILD → TEST → DEBUG → REVIEW → AUDIT → PROD-READY → PUSH |
| Intelligence | Content | PLAN → DRAFT → REVIEW → FACT-CHECK → DELIVER |
| Growth / Marketing | Content | PLAN → DRAFT → REVIEW → FACT-CHECK → DELIVER |
| Sales / Support | Content | PLAN → DRAFT → REVIEW → FACT-CHECK → DELIVER |
| Perception | Analysis | PLAN → CAPTURE → ANALYZE → VALIDATE → DELIVER |
