# Architecture Mapping: Claude Code Patterns → Agent-OS Runtime

> Agent-OS implements Claude Code's orchestration patterns as first-class runtime features.
> Every user (developer, marketer, engineer, sales) gets the full experience.

## Decision

One agent-os. No separate editions. Claude Code's patterns aren't just inspiration — they're implemented inside agent-os so every user gets the same powerful parallel orchestration, regardless of role.

## The Mapping

```
Claude Code (dev tool)              Agent-OS (autonomous runtime)
────────────────────                ─────────────────────────────

Subagents                     →     Department triads
  - Specialized workers               - Proposer / Worker / Critic
  - Own context, own tools             - Own sub-graph, own tools
  - Report results back                - Write results to brain

Agent View                    →     Dashboard (live)
  - See all sessions                   - See all departments working
  - Dispatch new work                  - Submit requests via UI/voice/API
  - Peek / attach / detach             - Watch any triad live, intervene

Dynamic Workflows             →     LangGraph orchestration
  - Script orchestrates agents         - StateGraph with conditional edges
  - pipeline() / parallel()            - Sub-graphs compose into company graph
  - Resumable runs                     - Checkpointer: resume after crash

Agent Teams                   →     Cross-department collaboration
  - Teammates message each other       - Departments share brain context
  - Shared task list                   - Orchestrator decomposes across depts
  - Team lead coordinates              - CEO Orchestrator routes work

Worktree Isolation            →     Sub-graph isolation
  - Each session gets own worktree     - Each department is own sub-graph
  - Can't step on each other           - Typed state contract prevents leaks
  - Merge results back                 - Results merge through AgentState

Persistent Memory             →     Brain (Obsidian + Qdrant)
  - Memory files per agent             - Semantic knowledge graph
  - Survives across sessions           - Survives across ticks, improves over time
  - Manual save                        - Auto-enriched by Reflector

Background Sessions           →     Daemon
  - Supervisor keeps them alive        - Daemon ticks every 15-20 min
  - Run while you're away              - Runs 24/7 autonomously
  - Resume after restart               - Checkpointed, resume after crash

Permission Modes              →     Guardian + Permission Gates
  - acceptEdits, auto, bypass          - READ / WRITE / SHELL / DESTRUCTIVE
  - Per-session rules                  - Per-tool declarations
  - User approves interactively        - Guardian approves via policy

Hooks                         →     Critic Loop + Learning
  - PreToolUse / PostToolUse           - Critic reviews every output
  - Validate before execution          - Reflector learns from outcomes
  - Block bad actions                  - Guardian blocks dangerous actions

/deep-research workflow       →     Intelligence Department
  - Fan-out web searches               - Scout / Analyst / Skeptic triad
  - Cross-check sources                - Brain-enriched, adversarial review
  - Cited report                       - Briefing notes in knowledge graph
```

## What Agent-OS adds BEYOND Claude Code

| Capability | Claude Code | Agent-OS |
|---|---|---|
| **Always running** | Stops when you close terminal | Daemon runs 24/7 |
| **Learns automatically** | Manual memory saves | Reflector writes playbooks from outcomes |
| **Proactive** | You ask, it does | Intelligence scouts, departments act on schedule |
| **Voice** | Terminal only | STT/TTS with ACK-first for deep tasks |
| **Dashboard** | Agent view (terminal) | Full web UI: live stream, brain browser, approvals |
| **Business departments** | N/A | Marketing, Sales, Growth, Finance, etc. |
| **Knowledge graph** | Flat memory files | Obsidian (backlinks) + Qdrant (semantic search) |
| **Safety** | Permission prompts to you | Guardian with autonomous policy-based decisions |
| **Integrations** | MCP servers (you configure) | Composio: Gmail, Notion, Slack, Calendar, GitHub |
| **Multi-user** | Single developer | Anyone — dev, marketer, manager, via any interface |

## How It Feels for Different Users

### Developer
```
"Review my latest PR for security issues"
  → Dispatcher: deep
  → Orchestrator: routes to Security + Code Review departments
  → Code Review triad: reads brain for project patterns, reviews code
  → Security triad: scans for OWASP top 10, checks dependencies
  → Results merge, Guardian gates any destructive suggestions
  → Delivered via: dashboard, Slack, or CLI
  
Meanwhile (proactive, no prompt needed):
  → Testing dept: found 2 flaky tests, opened fix PRs
  → Dependency dept: CVE in lodash, upgrade PR ready
  → Docs dept: API docs drifted from code, updated
```

### Marketer
```
"Write a blog post about our new feature launch"
  → Dispatcher: deep
  → Orchestrator: routes to Marketing + Growth departments
  → Marketing triad: reads brain for brand voice, past campaigns
  → Growth triad: SEO analysis, keyword strategy
  → Results merge, critic ensures brand consistency
  → Delivered via: dashboard, Notion page, email draft

Meanwhile (proactive):
  → Trends dept: spotted competitor launch on HN, briefing ready
  → SEO dept: 3 pages dropped in rankings, fix suggestions ready
```

### Sales person
```
"Prepare a proposal for Acme Corp"
  → Dispatcher: deep
  → Orchestrator: routes to Sales + Finance departments
  → Sales triad: reads brain for Acme history, past proposals
  → Finance triad: pricing analysis, margin check
  → Guardian: flags if discount exceeds policy
  → Delivered via: dashboard, email draft, Notion doc

Meanwhile (proactive):
  → Lead Gen dept: 12 new qualified leads from web scraping
  → Customer Support dept: Acme opened a ticket, flagged as VIP
```

### Engineering Manager
```
"What's the status of the auth module rewrite?"
  → Dispatcher: fast (single agent, no full triad needed)
  → Orchestrator: queries brain for recent auth-related outcomes
  → Returns: summary of PRs, test status, blockers, timeline
  → Delivered via: voice ("The auth rewrite is 70% done, 3 PRs merged...")

Meanwhile (proactive):
  → DevOps dept: CI pipeline failed 3x today, investigating
  → Performance dept: latency regression detected after yesterday's deploy
```

## Implementation Impact

This mapping doesn't change the phase plan — the architecture already supports it. What it clarifies:

1. **The Dashboard (Phase 5) is agent-os's "Agent View"** — it must feel as powerful as `claude agents` but for everyone
2. **The Orchestrator (Phase 2) is agent-os's "Workflow runtime"** — it must support the same fan-out/barrier/pipeline patterns
3. **The Brain (Phase 1) is agent-os's "Persistent Memory"** — but with semantic search and knowledge graph, not flat files
4. **The Daemon (Phase 3) is agent-os's "Background Sessions"** — but truly autonomous, not human-dispatched
5. **Developer departments get added in Phase 7** alongside business departments — same triad pattern, same registry, same brain

## Developer Departments (add to Phase 7)

| Department | Proposer | Worker | Critic |
|---|---|---|---|
| Code Review | ReviewPlanner | Reviewer | ReviewCritic |
| Testing | TestPlanner | TestWriter | TestCritic |
| Security | SecurityScanner | SecurityAnalyst | SecuritySkeptic |
| Bug Triage | BugClassifier | BugReproducer | BugValidator |
| Dependency | DepScanner | DepUpgrader | DepValidator |
| Documentation | DocDetector | DocWriter | DocReviewer |
| Performance | PerfProfiler | PerfOptimizer | PerfValidator |
| DevOps/CI | CIMonitor | CIFixer | CIValidator |

These follow the exact same pattern as Engineering, Intelligence, etc. — sub-graph + registry line.
