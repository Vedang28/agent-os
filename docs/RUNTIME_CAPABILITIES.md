# Agent-OS Runtime Capabilities

> What agent-os does autonomously for every user — testing, reporting, fixing, documenting, and learning.

## Capability Map

| Capability | Department | What it does autonomously |
|---|---|---|
| **Testing features** | Dev Experience → Testing | Writes tests, finds coverage gaps, fixes flaky tests, runs regression |
| **Reporting broken things** | Dev Experience → Bug Triage + DevOps → Observability | Detects failures, reproduces them, classifies severity, alerts you |
| **Fixing issues** | Engineering (or whichever dept owns that layer) | Proposer diagnoses → Worker fixes → Critic reviews → PR ready |
| **Documenting it** | Dev Experience → Documentation | Detects code-doc drift, writes/updates API docs, READMEs, changelogs |
| **Monitoring & error tracking** | DevOps → Observability | Watches logs, detects anomalies, correlates errors across services |
| **CI/CD pipeline health** | Dev Experience → DevOps/CI | Monitors builds, investigates failures, fixes configs, retries |
| **Performance regression** | Dev Experience → Performance | Profiles before/after, catches latency spikes, suggests optimizations |
| **Security scanning** | Dev Experience → Security | Continuous OWASP scanning, dep audits, CVE alerts, auto-upgrade PRs |

## Stack Coverage

Every layer of a modern tech stack maps to an agent-os department:

| Stack Layer | Agent-OS Department |
|---|---|
| Frontend | Frontend Division (Build, Design, Graphics) |
| APIs & Backend Logic | Backend Division (Backend, API Gateway) |
| Database & Storage | Backend Division (Database dept) |
| Auth & Permissions | Backend Division (Auth & Authorization dept) |
| Hosting & Deployment | DevOps Division (DevOps dept) |
| Cloud & Compute | DevOps Division (Cloud/Infra dept) |
| CI/CD & Version Control | Dev Experience (DevOps/CI dept) |
| Security & RLS | Dev Experience (Security dept) |
| Rate Limiting | Backend Division (API Gateway dept) |
| Caching & CDN | DevOps Division (Cloud/Infra dept) |
| Load Balancing & Scaling | DevOps Division (Cloud/Infra dept) |
| Error Tracking & Logs | DevOps Division (Observability dept) |
| Availability & Recovery | DevOps Division (DevOps dept) |

## Proactive Daemon Loop

These don't just run when you ask. The daemon runs them every 15-20 minutes:

```
Daemon tick
  │
  ├─ Testing dept:     "any new code since last tick?" → runs tests → reports failures
  ├─ Bug Triage:       "any new errors in logs?" → reproduces → classifies → alerts
  ├─ Security:         "any new CVEs for our deps?" → scans → opens upgrade PR
  ├─ Docs:             "any merged PRs without doc updates?" → detects drift → updates
  ├─ Performance:      "any latency changes?" → benchmarks → flags regressions
  ├─ CI Monitor:       "any failed builds?" → investigates → fixes → retries
  │
  └─ Reflector:        "what patterns am I seeing?" → updates playbooks → next tick is smarter
```

## Full Bug Lifecycle

From detection to fix to docs to learning — fully autonomous:

```
Bug detected (by Observability or Testing dept)
  │
  ▼
BUG TRIAGE DEPARTMENT
  ├─ Bug Classifier (proposer)
  │    Reads error, checks brain for similar past bugs
  ├─ Bug Reproducer (worker)
  │    Attempts reproduction, captures exact steps
  └─ Bug Validator (critic)
       Confirms repro is accurate, confirms root cause
  │
  ▼
OWNING DEPARTMENT (e.g. Backend)
  ├─ Architect (proposer)
  │    Reads brain + bug report, plans the fix
  ├─ Builder (worker)
  │    Implements fix using tools
  └─ Reviewer (critic)
       Reviews fix, checks for regressions
       (max 3 revisions, then escalate)
  │
  ▼
TESTING DEPARTMENT
  Runs full test suite against the fix
  │
  ▼
DOCUMENTATION DEPARTMENT
  Updates any affected docs
  │
  ▼
GUARDIAN
  Gates the PR — is it safe to merge?
  │
  ▼
RESULT
  PR ready for your review on the dashboard
  │
  ▼
REFLECTOR
  Logs outcome → "this type of bug was caused by X,
  next time check Y first" → playbook updated
```

## Feature Request Lifecycle

```
User: "Add dark mode to the settings page"
  │
  ▼
DISPATCHER
  Classifies as "deep" → enters company
  │
  ▼
ORCHESTRATOR
  Queries brain for existing UI patterns, design system
  Decomposes: design → implement → test → document
  Routes to Frontend Division
  │
  ▼
FRONTEND DESIGN DEPARTMENT
  ├─ Designer (proposer)
  │    Reads brain for design system, plans dark mode approach
  ├─ Implementer (worker)
  │    Builds the feature using FileTool, follows design tokens
  └─ Design Critic
       Reviews for accessibility, consistency, edge cases
       (max 3 revisions)
  │
  ▼
TESTING DEPARTMENT
  Writes tests for dark mode toggle, persistence, edge cases
  │
  ▼
SECURITY DEPARTMENT
  Quick check — any XSS vectors in theme switching?
  │
  ▼
DOCUMENTATION DEPARTMENT
  Updates user docs with dark mode instructions
  │
  ▼
GUARDIAN
  Reviews PR, gates merge
  │
  ▼
RESULT
  PR ready with: feature code + tests + docs + security review
  │
  ▼
REFLECTOR
  "Frontend feature requests that include design tokens
   complete 2x faster" → playbook updated
```

## Incident Response Lifecycle

```
Observability dept detects: 500 errors spiking on /api/checkout
  │
  ▼
INTELLIGENCE DEPARTMENT (fast-track, no full triad)
  Immediate alert to dashboard + Slack
  │
  ▼
BUG TRIAGE DEPARTMENT
  ├─ Classifier: critical severity, checkout flow, P0
  ├─ Reproducer: reproduces with test request, captures stack trace
  └─ Validator: confirms — NullPointerException in payment handler
  │
  ▼
BACKEND DEPARTMENT (priority escalation)
  ├─ Architect: reads recent deploys, identifies PR #287 as cause
  ├─ Builder: implements hotfix (null check + fallback)
  └─ Reviewer: verifies fix, checks no other callers affected
  │
  ▼
TESTING → GUARDIAN → PR ready
  │
  ▼
DASHBOARD
  Shows: incident timeline, root cause, fix PR, affected users count
  │
  ▼
REFLECTOR
  "Payment handler changes need null-safety review in critic checklist"
  → Backend department playbook updated
  → Future PRs to payment code get extra scrutiny
```

## Continuous Improvement Loop

The Reflector makes agent-os smarter over time:

```
Week 1:  Bug fix takes 4 department hops, 3 critic revisions
Week 4:  Playbooks updated — proposers check common patterns first
Week 8:  Same bug type fixed in 2 hops, 1 revision
Week 12: Proposer prevents the bug class entirely (suggests guard clause during code review)

The brain compounds. Every outcome teaches the next run.
```

## What You See on the Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  AGENT-OS DASHBOARD                                     9:14 AM │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ACTIVE NOW                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ Testing     │ │ Security    │ │ Bug Triage  │               │
│  │ Running     │ │ Scanning    │ │ 2 new bugs  │               │
│  │ regression  │ │ deps for    │ │ classified  │               │
│  │ suite...    │ │ CVEs...     │ │ as P2       │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│                                                                 │
│  READY FOR REVIEW                                               │
│  ● PR #142 — Fix null pointer in payment handler     [Critical] │
│  ● PR #143 — Upgrade lodash (CVE-2026-1234)          [Security] │
│  ● PR #144 — Fix 3 flaky tests in auth module        [Testing]  │
│  ● PR #145 — Update API docs for v2.3 endpoints      [Docs]     │
│                                                                 │
│  OVERNIGHT SUMMARY                                              │
│  Tests: 847 passed, 0 failed (3 flaky fixed)                   │
│  Security: 1 CVE found, upgrade PR ready                        │
│  Performance: no regressions detected                           │
│  CI: all green, avg build time 4m12s                            │
│                                                                 │
│  BRAIN INSIGHTS                                                 │
│  "Auth module has had 4 null-pointer bugs this month.           │
│   Reflector added null-safety check to Code Review playbook."   │
│                                                                 │
│  COST THIS WEEK                                                 │
│  Tokens: 2.1M │ Cost: $4.82 │ Tasks: 47 │ PRs opened: 12      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
