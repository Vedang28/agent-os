# Code Pipeline

> The 9-stage pipeline every code-producing department runs. No shortcuts, no skipping stages.
> **Stack-agnostic.** The stages are universal — the specific commands, tools, and patterns adapt to whatever tech stack the user is running.

## The Pipeline

```
PLAN → SCAFFOLD → BUILD → TEST → DEBUG → REVIEW → AUDIT → PROD-READY → PUSH
```

Every department that produces code follows this exact sequence. Non-code departments (Intelligence, Marketing, Sales, Support) use a simplified version without SCAFFOLD, TEST, DEBUG, or AUDIT.

## Stack Detection (PLAN stage, step 0)

Before the pipeline runs, agent-os detects the user's tech stack by reading their project:

```
Read project root:
  package.json     → Node.js / JS / TS ecosystem
  pyproject.toml   → Python ecosystem
  composer.json    → PHP / Laravel
  Gemfile          → Ruby / Rails
  go.mod           → Go
  Cargo.toml       → Rust
  pom.xml          → Java / Maven
  build.gradle     → Java / Kotlin / Gradle
  *.csproj         → .NET / C#
  pubspec.yaml     → Dart / Flutter
  mix.exs          → Elixir / Phoenix
  Package.swift    → Swift
  docker-compose.* → Containerized app
  Makefile         → Build system

Read framework markers:
  artisan          → Laravel
  manage.py        → Django
  next.config.*    → Next.js
  nuxt.config.*    → Nuxt
  angular.json     → Angular
  svelte.config.*  → SvelteKit
  astro.config.*   → Astro
  Fastfile         → iOS/Android (Fastlane)
  serverless.yml   → Serverless Framework
  terraform/       → Infrastructure as Code
  .github/workflows/ → CI/CD already configured

Read database:
  .env / config    → DB connection strings → MySQL, Postgres, Mongo, SQLite, Redis
  migrations/      → ORM migrations exist
  prisma/          → Prisma schema
  schema.rb        → Rails migrations
```

This detection feeds into every stage so the pipeline uses the RIGHT commands, patterns, and security checks for the user's stack.

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
**What:** Read the codebase, detect the stack, explore the DB, produce a clear plan before any code.

```
Input:  request + brain_context (read-before-act) + detected stack
Output: plan (list of steps), draft (design document)

Substeps:
  1a. Read brain for existing patterns, playbooks, and past decisions
  1b. Detect tech stack (see Stack Detection above)
  1c. Explore existing code structure (what exists, what needs changing)
  1d. Explore database schema (if applicable)
  1e. Identify files to create/modify
  1f. Consider edge cases and failure modes
  1g. Estimate scope (token budget, file count)
  1h. Produce plan in stack-native terms

Checks:
  ✓ Queried brain for existing patterns and playbooks
  ✓ Plan addresses the actual request, not a tangent
  ✓ Plan uses the project's actual patterns (not generic templates)
  ✓ Plan considers the existing code — don't reinvent what's already there
  ✓ Plan estimates scope (token budget, file count)
```

**Stack-specific examples:**
| Stack | What PLAN reads |
|---|---|
| Laravel | routes/web.php, app/Models/, database/migrations/, .env |
| Django | urls.py, models.py, settings.py, migrations/ |
| Next.js | app/ or pages/, API routes, prisma/schema.prisma |
| Rails | config/routes.rb, app/models/, db/schema.rb |
| Go | go.mod, cmd/, internal/, handlers/ |
| Spring | pom.xml, src/main/java, application.properties |

The Proposer reads playbooks from the brain first. If the Reflector has noted "always use parameterized queries for DB work," the plan includes that from the start.

---

### 2. SCAFFOLD

**Who:** Worker agent (scaffolding mode)
**What:** Generate boilerplate — models, migrations, controllers, routes, views, types. Use the stack's native generators when available.

```
Input:  plan from PLAN stage + detected stack
Output: skeleton files with interfaces, type signatures, empty test files

Substeps:
  2a. Use native scaffolding tools when available (see below)
  2b. Create empty test files alongside source files
  2c. Verify imports resolve, no circular dependencies
  2d. Verify file structure follows the project's conventions

Checks:
  ✓ Files created in the correct project directories
  ✓ Interfaces/types match the plan's contracts
  ✓ Test files created alongside source files
  ✓ Imports resolve (no circular dependencies)
  ✓ Follows project's existing naming conventions
```

**Stack-specific scaffolding:**
| Stack | Native scaffolding commands |
|---|---|
| Laravel | `php artisan make:model`, `make:controller`, `make:migration`, `make:request`, `make:test` |
| Django | `python manage.py startapp`, manual models/views/urls |
| Next.js | Create files in `app/` or `pages/`, create API route handlers |
| Rails | `rails generate model`, `scaffold`, `controller`, `migration` |
| Go | Create packages in `internal/`, define interfaces, handler structs |
| Spring | Create `@Controller`, `@Service`, `@Repository`, `@Entity` classes |
| Express | Create route files, middleware, model schemas |
| FastAPI | Create router files, Pydantic models, dependency functions |
| Flutter | Create widgets, models, services, BLoC/providers |
| .NET | `dotnet new`, create controllers, models, DbContext |

Scaffold first, build second. This catches structural issues before the expensive code generation step.

---

### 3. BUILD

**Who:** Worker agent (implementation mode)
**What:** Write the working code — service layer, controller logic, views, client-side code. Use the stack's native patterns.

```
Input:  scaffolded files + plan + detected stack
Output: working implementation

Checks:
  ✓ All interfaces from SCAFFOLD are implemented
  ✓ Code follows the plan's design
  ✓ No TODOs or placeholder code left
  ✓ Uses the stack's native patterns (not generic code)
  ✓ Follows project's existing conventions (naming, structure, style)
  ✓ Database queries use the stack's ORM/query builder (not raw SQL)
```

**Stack-specific patterns the BUILD stage follows:**
| Stack | Patterns used |
|---|---|
| Laravel | Eloquent ORM, Blade templates, Form Requests, Middleware, Service classes |
| Django | Django ORM, class-based views, serializers, middleware |
| Next.js | Server components, API routes, Server Actions, React hooks |
| Rails | ActiveRecord, ERB/Haml, concerns, service objects |
| Go | Interfaces, dependency injection, error handling, goroutines |
| Spring | Spring Data JPA, dependency injection, AOP, Bean validation |
| Express | Middleware chains, async/await, Mongoose/Sequelize |
| FastAPI | Pydantic models, dependency injection, async handlers |

---

### 4. TEST

**Who:** Testing agent (or Worker in test mode)
**What:** Write tests AND run them using the stack's native test framework.

```
Input:  implemented code from BUILD + detected stack
Output: test files + test results

Substeps:
  4a. Write unit tests for each public function/class
  4b. Write integration tests for cross-module interactions
  4c. Write edge case tests (empty input, malformed data, timeouts, large input)
  4d. Run full test suite using the stack's test runner
  4e. Check coverage: identify untested paths

Checks:
  ✓ Every public function has at least one test
  ✓ Happy path tested
  ✓ Error/edge cases tested
  ✓ All tests pass
  ✓ No flaky tests (run twice to confirm)
```

**Stack-specific test commands:**
| Stack | Test framework | Run command |
|---|---|---|
| Laravel | PHPUnit / Pest | `php artisan test` |
| Django | Django TestCase | `python manage.py test` |
| Next.js / React | Jest / Vitest | `npm test` or `npx vitest` |
| Rails | Minitest / RSpec | `rails test` or `rspec` |
| Go | testing package | `go test ./...` |
| Spring | JUnit / Mockito | `mvn test` or `gradle test` |
| Express | Jest / Mocha | `npm test` |
| FastAPI | pytest | `pytest -v` |
| Flutter | flutter_test | `flutter test` |
| Rust | built-in | `cargo test` |
| .NET | xUnit / NUnit | `dotnet test` |

If tests fail → go to DEBUG.

---

### 5. DEBUG

**Who:** Worker agent (debug mode)
**What:** Start the app, test it live, fix any runtime issues.

This is NOT just "fix failing unit tests." This is real-world verification:

```
Input:  failing tests / review findings / audit findings / runtime issues + detected stack
Output: fixed code, verified working

Process:
  5a. Start the server / app / service (using the stack's dev server)
  5b. Test in browser / via API / via CLI — verify the feature actually works
  5c. Test the golden path end-to-end (not just unit tests)
  5d. Test edge cases live (empty input, wrong user, expired token)
  5e. If issues found:
      - Read the actual error message and stack trace
      - Identify root cause (not symptoms)
      - Implement minimal targeted fix
      - Re-run to confirm fix
      - Run full test suite to confirm no regressions
  5f. Repeat until the feature works in the real app, not just in tests

Rules:
  ✗ Never delete a test to make it pass
  ✗ Never swallow errors silently
  ✗ Never widen scope to escape a bug
  ✗ Never claim "tested" without actually running the app
  ✓ One fix at a time, re-test after each
  ✓ Max 3 debug loops before escalating
  ✓ Type checking and test suites verify code correctness — 
    running the app verifies feature correctness. Both are required.
```

**Stack-specific dev servers:**
| Stack | Start command |
|---|---|
| Laravel | `php artisan serve` |
| Django | `python manage.py runserver` |
| Next.js | `npm run dev` |
| Rails | `rails server` |
| Go | `go run .` or `air` (hot reload) |
| Spring | `mvn spring-boot:run` or `gradle bootRun` |
| Express | `npm run dev` or `node server.js` |
| FastAPI | `uvicorn main:app --reload` |
| Flutter | `flutter run` |
| .NET | `dotnet run` |

After DEBUG, return to whichever stage triggered it (TEST, REVIEW, or AUDIT).

---

### 6. REVIEW

**Who:** Critic agent (e.g., CodeDoctor, BackendReviewer, DesignCritic)
**What:** Code review + active attack testing on endpoints.

This is NOT a passive read-through. The reviewer actively tries to break things:

```
Input:  implemented + tested + debugged code
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
  
  Active attack testing (if endpoints exist):
    ✓ curl-attack every endpoint with malformed input
    ✓ Send oversized payloads, unicode, null bytes
    ✓ Try accessing other users' data (IDOR)
    ✓ Try accessing without auth / with expired tokens
    ✓ Try SQL injection in every input field
    ✓ Try XSS payloads in every text field
    ✓ Try path traversal in file/URL parameters
    ✓ Test rate limiting — hammer an endpoint
    ✓ Test mass assignment — send extra fields in requests
    ✓ Fix every problem found before approving

If findings:
  → approved = False
  → back to DEBUG with specific findings
  → counts toward max_revisions (3 max, then escalate)
```

---

### 7. AUDIT

**Who:** Security Gate (SecurityGate class)
**What:** Automated security scan — the 15-point checklist + active attack testing.

```
Input:  reviewed + approved code
Output: security verdict (pass/fail + findings)

The 15-point security checklist:

  1. Input Validation
     ✓ All user inputs validated (type, length, range, format)
     ✓ Reject unexpected fields (no mass assignment)
     ✓ Whitelist allowed values where possible

  2. SQL Injection
     ✓ ALL queries use parameterized statements / ORM
     ✓ No raw string concatenation in queries — EVER
     ✓ Test: ' OR 1=1 --, UNION SELECT, DROP TABLE

  3. XSS (Cross-Site Scripting)
     ✓ All output HTML-encoded
     ✓ No raw HTML rendering of user input
     ✓ CSP headers configured
     ✓ Test: <script>alert(1)</script>, onerror=

  4. CSRF (Cross-Site Request Forgery)
     ✓ CSRF tokens on all state-changing forms/endpoints
     ✓ SameSite cookie attribute set
     ✓ Verify Origin/Referer headers

  5. Command Injection
     ✓ Shell commands use argument lists, not strings
     ✓ All metacharacters escaped (;|&`$)
     ✓ Test: ; rm -rf /, $(whoami), `id`

  6. Rate Limiting
     ✓ Rate limits on all public endpoints
     ✓ Rate limits on auth endpoints (login, register, reset)
     ✓ Test: hammer endpoint 100x in 1 second

  7. Mass Assignment
     ✓ Only expected fields accepted
     ✓ Server-side allowlist of fillable fields
     ✓ Test: send role=admin, is_staff=true in body

  8. Route Constraints
     ✓ Route parameters validated (numeric IDs are numeric)
     ✓ No wildcard routes leaking internal paths
     ✓ 404 for non-existent resources

  9. Access Control
     ✓ Auth required on all non-public endpoints
     ✓ Authorization checked per user per action
     ✓ Admin routes protected

  10. IDOR (Insecure Direct Object Reference)
      ✓ Every resource access checks ownership
      ✓ Test: change /users/5/data to /users/6/data
      ✓ UUIDs preferred over sequential IDs

  11. Secrets Exposure
      ✓ No keys, tokens, passwords in code
      ✓ No secrets in logs or error messages
      ✓ Environment variables for all config

  12. Authentication
      ✓ Passwords hashed (bcrypt/scrypt/argon2)
      ✓ Session tokens cryptographically random
      ✓ Token expiry configured
      ✓ Secure cookie flags (HttpOnly, Secure, SameSite)

  13. SSRF (Server-Side Request Forgery)
      ✓ URLs validated before server-side requests
      ✓ Block private IPs and cloud metadata endpoints

  14. Path Traversal
      ✓ File paths validated, symlinks resolved
      ✓ Reject ../ in any file parameter
      ✓ Restrict to allowed directories

  15. Dependencies
      ✓ No known CVEs (critical/high)
      ✓ Versions pinned, unused deps removed

Active attack verification (if endpoints exist):
  ✓ curl / httpie / Postman — hit every endpoint with attack payloads
  ✓ Verify each check with real requests, not just code reading
  ✓ Document what was tested and what passed

Stack-specific security patterns to verify:
  Laravel:  Form Requests, $fillable/$guarded, CSRF middleware, Sanctum/Passport
  Django:   CSRF middleware, queryset filtering, @login_required, bleach
  Next.js:  Server Actions validation, API route auth, CSP headers, sanitize-html
  Rails:    Strong Parameters, CSRF token, has_secure_password, Pundit/CanCanCan
  Go:       sql.DB with ?, template.HTMLEscapeString, crypto/rand
  Spring:   Spring Security, @Valid, CSRF protection, BCryptPasswordEncoder
  Express:  helmet, express-rate-limit, express-validator, cors, csurf
  FastAPI:  Pydantic validation, Depends() for auth, CORS middleware

If findings:
  → fail
  → back to DEBUG with security-specific fixes required
  → counts toward max_revisions (3 max, then escalate)
```

---

### 8. PROD-READY

**Who:** Production Readiness agent (new agent in each department)
**What:** Final live verification — curl-verify everything works, confirm it's ship-quality. The agent must confirm "tested" before the pipeline advances. No rubber-stamping.

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
  
  Live verification (mandatory):
    ✓ Start the app / server fresh
    ✓ curl-verify every new/changed endpoint
    ✓ Verify the feature works end-to-end in the real app
    ✓ Check for regressions in adjacent features
    ✓ Confirm "TESTED" with evidence (request/response logs)
    ✓ No advancing without explicit "TESTED" confirmation

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
  9b. Stage specific files (NEVER git add -A or git add .)
       - Only add files that were created/modified in this pipeline run
       - Verify no secrets, .env, or temp files are staged
  9c. Create commit/PR with:
       - Clear title describing the change
       - Summary of what and why
       - Test results summary
       - Security audit result (15-point checklist status)
       - "TESTED" confirmation from PROD-READY
  9d. Push to remote
  9e. Deliver to user via:
       - Dashboard notification
       - Slack/email (if integrated)
       - Voice confirmation (if voice request)
  9f. Log outcome to brain for Reflector
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

---

## Stack-Agnostic Principle

The 9 stages are universal. The commands, patterns, and tools adapt.

```
What stays the same across ALL stacks:
  ✓ The 9-stage sequence (never skip, never reorder)
  ✓ The 15-point security checklist
  ✓ Max 3 debug loops, then escalate
  ✓ "TESTED" confirmation required before PUSH
  ✓ Specific file staging (never git add -A)
  ✓ Brain read-before-act at PLAN stage
  ✓ Reflector learning after PUSH

What adapts per stack:
  ✗ Scaffolding commands (artisan make vs rails generate vs manual)
  ✗ ORM / query builder (Eloquent vs Django ORM vs Prisma vs ActiveRecord)
  ✗ Test framework (PHPUnit vs pytest vs Jest vs RSpec vs go test)
  ✗ Dev server (artisan serve vs runserver vs npm run dev)
  ✗ Security patterns (Form Requests vs Pydantic vs Strong Parameters)
  ✗ File structure conventions (app/Http vs src/handlers vs internal/)
  ✗ Build tools (composer vs pip vs npm vs cargo vs gradle)
```

Agent-os detects the stack at PLAN time and adapts every subsequent stage. A Laravel project gets Eloquent patterns and `php artisan test`. A Go project gets interfaces and `go test ./...`. A Next.js project gets Server Components and `npx vitest`. The pipeline doesn't change — the implementation does.
