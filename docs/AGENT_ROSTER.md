# BURRY — FULL AGENT ROSTER

> Complete naming + purpose reference for the multi-agent company.
> Every agent = one singleton class, registered once, single responsibility.
> Most departments follow the **lead + triad** shape: a lead routes/sets the goal,
> then a **Proposer** drafts, a **Worker** executes, a **Critic** challenges before anything ships.
> The Critic is the role that makes the system "think like a human" — nothing leaves a department unreviewed.

**Total: 116 agents across 10 divisions / 36 departments.**

Naming convention: `division.department.agent` (e.g. `backend.api.builder`).
Registry key is lowercase dotted. Class name is PascalCase (e.g. `ApiBuilder`).

---

## 0. EXECUTIVE / CORE (5)

The always-on brain stem. These are singletons that never sleep.

| Agent | Type | Purpose |
|-------|------|---------|
| Orchestrator (CEO) | boss | Decomposes the request, picks the division, arbitrates the final answer |
| Dispatcher | router | Fast intent + lane assignment (instant / fast / deep), routes to the right division |
| Brain Librarian | memory | Owns the Obsidian vault — reads, writes, indexes, maintains backlinks |
| Reflector | learning | Periodically reviews outcomes, updates each proposer's playbook (the "get better" loop) |
| Guardian | safety | Permission gates, destructive-action approval, secret protection, kill-switch |

---

## 0.5 MEMORY & CONTINUITY (3) — system-level

Keeps both the dev workflow and the runtime from starting cold. Pairs with the Brain Librarian and Reflector above.

| Agent | Type | Purpose |
|-------|------|---------|
| Session Scribe | memory | Logs what each work session accomplished to the session log |
| Decision Recorder | memory | Records architectural decisions (ADR) so they're never re-litigated |
| Log Auditor | critic | Scans logs and outcomes for repeated failures, flags them to the Reflector |

---

## 1. BACKEND DIVISION (16)

### Backend department
| Agent | Type | Purpose |
|-------|------|---------|
| Backend Architect | proposer | Designs service structure, data flow, and contracts before code is written |
| API Builder | worker | Writes endpoints, controllers, route handlers |
| Schema Designer | worker | Defines request/response models and input validation |
| Backend Reviewer | critic | Catches N+1 queries, blocking calls on hot paths, contract drift |

### Database department
| Agent | Type | Purpose |
|-------|------|---------|
| Database Architect | proposer | Schema design, normalization, indexing strategy |
| Query Writer | worker | Writes and optimizes SQL, builds migrations |
| Migration Runner | worker | Applies migrations safely with rollback plans |
| Data Integrity Critic | critic | Checks constraints, foreign keys, race conditions, deadlocks |

### Authentication & Authorization department
| Agent | Type | Purpose |
|-------|------|---------|
| Auth Architect | proposer | Designs auth flows (OAuth, JWT, sessions, SSO) |
| Token Manager | worker | Issues, rotates, and validates tokens; handles key storage |
| Access-Control Builder | worker | Builds RBAC/ABAC rules and permission matrices |
| Auth Critic | critic | Hunts privilege escalation, leaked tokens, insecure flows |

### API Gateway & Rate-Limiting department
| Agent | Type | Purpose |
|-------|------|---------|
| Gateway Architect | proposer | Routing, API versioning, gateway configuration |
| Rate-Limit Engineer | worker | Throttling, quotas, backpressure, fair-use rules |
| Cache Strategist | worker | Cache keys, TTLs, invalidation strategy |
| Load Critic | critic | Flags hotspots, thundering-herd risk, unfair throttling |

---

## 2. FRONTEND DIVISION (12)

### Frontend Build department
| Agent | Type | Purpose |
|-------|------|---------|
| Frontend Architect | proposer | Component structure and state-management strategy |
| Component Builder | worker | Builds React/Next components |
| State/Data Wirer | worker | Hooks, data fetching, form wiring |
| Frontend Reviewer | critic | Accessibility, re-render performance, prop-drilling |

### Frontend Design (UI/UX) department
| Agent | Type | Purpose |
|-------|------|---------|
| UX Designer | proposer | Flows, wireframes, information architecture |
| UI Stylist | worker | Design tokens, theming (OKLCH, dark mode), layout polish |
| Interaction Designer | worker | Motion, transitions, micro-interactions |
| Design Critic | critic | Visual consistency, hierarchy, brand adherence |

### Graphics department
| Agent | Type | Purpose |
|-------|------|---------|
| Art Director | proposer | Visual direction, mood, composition |
| Asset Generator | worker | Icons, illustrations, image assets |
| Brand Keeper | worker | Logo, palette, and typography consistency |
| Graphics Critic | critic | Resolution, alignment, export correctness |

---

## 3. QUALITY DIVISION (7)

### Testing department
| Agent | Type | Purpose |
|-------|------|---------|
| Test Strategist | proposer | Decides what to test and the coverage plan |
| Test Writer | worker | Writes unit and integration tests |
| Test Runner | worker | Executes suites and reports failures |
| Bug Triager | critic | Classifies severity and root-causes failures |

### UI Testing department (works with Perception's eyes)
| Agent | Type | Purpose |
|-------|------|---------|
| Visual-Test Designer | proposer | Defines visual and regression test cases |
| Playwright Operator | worker | Drives the browser, captures runs |
| Visual-Regression Critic | critic | Diffs screenshots, flags pixel/layout drift |

---

## 4. DEVOPS & CLOUD DIVISION (11)

### DevOps department
| Agent | Type | Purpose |
|-------|------|---------|
| CI/CD Architect | proposer | Pipeline design |
| Pipeline Builder | worker | Build scripts and workflow files |
| Release Manager | worker | Versioning, changelogs, deploy gates |
| Deploy Critic | critic | Checks rollbacks, env parity, secrets leaking into CI |

### Cloud / Infra department
| Agent | Type | Purpose |
|-------|------|---------|
| Cloud Architect | proposer | Infra topology and IaC design |
| Provisioner | worker | Terraform / Docker / k8s resource creation |
| Cost Watcher | worker | Resource cost tracking and right-sizing |
| Reliability Critic | critic | SLOs, failover, single points of failure |

### Observability department
| Agent | Type | Purpose |
|-------|------|---------|
| Telemetry Engineer | worker | Wires logs, metrics, traces |
| Alert Designer | worker | Alert rules and thresholds |
| Incident Responder | critic | Parses errors, surfaces crashes, writes incident summaries |

---

## 5. AI / ML DIVISION (8)

### AI Agent department (LLM orchestration)
| Agent | Type | Purpose |
|-------|------|---------|
| Prompt Engineer | proposer | Prompt and system-prompt design |
| Tool/Function Builder | worker | Defines tool schemas for function calling |
| Model Router | worker | Picks the model per task (NIM, Gemini, Claude) by cost/latency |
| Eval Critic | critic | Checks output quality, hallucination, regressions |

### ML department
| Agent | Type | Purpose |
|-------|------|---------|
| Data Curator | proposer | Dataset collection, cleaning, labeling |
| Embedding Engineer | worker | Embeddings and vector store (Qdrant) management |
| Trainer | worker | Training/fine-tune runs (LoRA), tracks eval metrics |
| ML Critic | critic | Overfitting, data leakage, model drift detection |

---

## 6. GROWTH DIVISION (12)

### Trends / Research department
| Agent | Type | Purpose |
|-------|------|---------|
| Scout | proposer | Pulls trending repos/news (GitHub, HN, X, Reddit) |
| Analyst | worker | Deep-dives top items, extracts the real signal |
| Skeptic | critic | Challenges hype, verifies sources |

### Marketing department
| Agent | Type | Purpose |
|-------|------|---------|
| Marketing Strategist | proposer | Campaigns, positioning, channel selection |
| Copywriter | worker | Ad, email, and landing-page copy |
| Marketing Critic | critic | Message clarity, CTA strength, brand fit |

### Lead Gen department
| Agent | Type | Purpose |
|-------|------|---------|
| Prospector | proposer | Finds leads matching the ideal customer profile |
| Enricher | worker | Fills firmographic and contact data |
| Qualifier | critic | Scores and filters leads, removes junk |

### SEO department
| Agent | Type | Purpose |
|-------|------|---------|
| Keyword Scout | proposer | Keyword and search-intent research |
| Content Optimizer | worker | On-page SEO and content structure |
| SEO Auditor | critic | Technical SEO, broken links, ranking checks |

---

## 7. SALES & OPS DIVISION (9) — industry / other teams

### SDR / Sales department
| Agent | Type | Purpose |
|-------|------|---------|
| Outreach Planner | proposer | Sequences and cadences |
| Message Writer | worker | Personalized outreach messages |
| Reply Handler | critic | Triages responses, books meetings, flags spam |

### Customer Support department
| Agent | Type | Purpose |
|-------|------|---------|
| Ticket Triager | proposer | Categorizes and prioritizes tickets |
| Resolver | worker | Drafts answers via knowledge-base lookup |
| Escalation Critic | critic | Flags what genuinely needs a human |

### Finance / Compliance department
| Agent | Type | Purpose |
|-------|------|---------|
| Bookkeeper | worker | Categorizes expenses and invoices |
| Reporter | worker | Generates summaries and dashboards |
| Compliance Critic | critic | Checks policy/regulatory issues (e.g. UK care compliance) |

---

## 8. PERCEPTION DIVISION (9) — the eyes

### Screen department
| Agent | Type | Purpose |
|-------|------|---------|
| Screen-watcher | worker | Captures screen frames, detects changes |
| Vision-reader | proposer | Interprets frames via NIM vision (UI elements, OCR, state) |
| Frame-critic | critic | Validates the reading against raw pixels, catches hallucinations |

### Video department
| Agent | Type | Purpose |
|-------|------|---------|
| Video-capturer | worker | Records screen/video, samples frames |
| Video-summarizer | proposer | Summarizes recordings (NVIDIA VILA) |
| Video-critic | critic | Verifies the summary matches the footage |

### Document-reading department
| Agent | Type | Purpose |
|-------|------|---------|
| Doc-ingester | worker | Loads PDFs/docs, splits into chunks |
| Doc-extractor | proposer | Extracts text, tables, and structure |
| Doc-critic | critic | Verifies extraction accuracy and completeness |

---

## 9. DEVELOPER EXPERIENCE DIVISION (24) — every developer gets a full team

### Code Review department
| Agent | Type | Purpose |
|-------|------|---------|
| Review Planner | proposer | Reads PR diff, brain for project patterns, plans review strategy |
| Reviewer | worker | Line-by-line review: bugs, style, security, performance |
| Review Critic | critic | Challenges false positives, verifies severity ratings |

### Testing department
| Agent | Type | Purpose |
|-------|------|---------|
| Test Planner | proposer | Identifies coverage gaps, plans what tests to write |
| Test Writer | worker | Writes unit/integration/e2e tests |
| Test Critic | critic | Validates tests actually cover the intended behavior |

### Security department
| Agent | Type | Purpose |
|-------|------|---------|
| Security Scanner | proposer | Scans codebase for OWASP top 10, known patterns |
| Security Analyst | worker | Deep analysis: injection, auth bypass, data exposure |
| Security Skeptic | critic | Adversarially challenges findings, filters false positives |

### Bug Triage department
| Agent | Type | Purpose |
|-------|------|---------|
| Bug Classifier | proposer | Categorizes issues by severity, component, reproducibility |
| Bug Reproducer | worker | Attempts to reproduce bugs, captures repro steps |
| Bug Validator | critic | Verifies reproduction is accurate, confirms root cause |

### Dependency Management department
| Agent | Type | Purpose |
|-------|------|---------|
| Dep Scanner | proposer | Monitors dependencies for CVEs, breaking changes, updates |
| Dep Upgrader | worker | Creates upgrade PRs, runs tests, verifies compatibility |
| Dep Validator | critic | Validates upgrade doesn't break anything, checks changelogs |

### Documentation department
| Agent | Type | Purpose |
|-------|------|---------|
| Doc Detector | proposer | Identifies code-doc drift, missing docs, stale READMEs |
| Doc Writer | worker | Writes/updates API docs, guides, inline docs |
| Doc Reviewer | critic | Verifies docs match actual code behavior |

### Performance department
| Agent | Type | Purpose |
|-------|------|---------|
| Perf Profiler | proposer | Identifies hot paths, latency regressions, memory leaks |
| Perf Optimizer | worker | Implements optimizations, caching, query improvements |
| Perf Validator | critic | Benchmarks before/after, validates improvement is real |

### DevOps / CI department
| Agent | Type | Purpose |
|-------|------|---------|
| CI Monitor | proposer | Watches CI pipelines, detects failures and flaky runs |
| CI Fixer | worker | Investigates failures, fixes configs, retries with changes |
| CI Validator | critic | Verifies fix actually resolves the failure, not a fluke |

---

## BUILD ORDER (don't build all 116 at once)

1. **Executive / Core first** — Orchestrator, Dispatcher, Brain Librarian, Reflector, Guardian. Nothing works without these.
2. **Obsidian brain layer** — note schema, read-before-act query, reflector loop. Every agent depends on it.
3. **One full department end-to-end** — Engineering. Prove the lead → triad → critic → brain loop actually catches errors.
4. **Developer Experience division early** — Code Review, Testing, Security departments. These are high-value and can be dogfooded immediately while building the rest of agent-os.
5. **Replicate** — each new department after that is ~4 small class files + registry lines. Mass-produce by copying the proven pattern.

## ENGINEERING RULES FOR EVERY AGENT

- One class, one responsibility. If an agent does two things, split it.
- Shared `Agent` protocol + registry. No agent re-implements routing or memory.
- Reuse shared tools (DRY) — never duplicate a capability across agents.
- No `if-elif` dispatch chains — use the registry.
- Heavy agents (Perception, ML, deep research) live in the **deep lane only**, run in the background with an ACK. Simple commands skip the company entirely.
- Every department's critic must be able to send work back (revise) — approval is never automatic.
