# Security Architecture

> How agent-os secures every piece of code it produces and every action it takes — for the end user, at runtime.

## The Problem

Agent-os produces code, executes tools, and interacts with external services autonomously. Without a security layer wired into the core pipeline, it could:
- Generate code with SQL injection, XSS, command injection
- Expose API keys or credentials in code or brain notes
- Allow path traversal through FileTool
- Make SSRF requests through WebTool
- Execute destructive actions without approval
- Produce dependencies with known CVEs

## The Solution: Three Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1: TOOL GATES                       │
│              (prevents bad actions in real-time)             │
│                                                             │
│  Every tool call flows through Guardian BEFORE execution:    │
│                                                             │
│  Agent wants to call BashTool("rm -rf /")                   │
│    → Guardian checks Permission level (DESTRUCTIVE)         │
│    → BLOCKED — requires explicit approval                   │
│                                                             │
│  Agent wants to call FileTool.write("/etc/passwd")          │
│    → Guardian checks path validation                        │
│    → BLOCKED — outside allowed directories                  │
│                                                             │
│  Agent wants to call WebTool.get("http://169.254.169.254")  │
│    → Guardian checks SSRF blocklist                         │
│    → BLOCKED — internal IP / metadata endpoint              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  LAYER 2: CODE REVIEW GATE                   │
│          (catches vulnerabilities in generated code)         │
│                                                             │
│  Every department that outputs code must pass through        │
│  the Security Gate before the result is approved:            │
│                                                             │
│  Department triad finishes:                                  │
│    Proposer → Worker → Critic (approves) →                  │
│    → SECURITY GATE (mandatory, not optional)                │
│    → Security Scanner checks output for:                    │
│       ✓ Injection vulnerabilities (SQL, cmd, XSS, LDAP)    │
│       ✓ Hardcoded secrets / API keys / tokens               │
│       ✓ Unsafe deserialization (pickle, yaml.load)          │
│       ✓ Missing input validation                            │
│       ✓ Missing output encoding                             │
│       ✓ Insecure crypto (MD5, SHA1 for passwords)           │
│       ✓ Race conditions / TOCTOU                            │
│       ✓ Missing auth/authz checks                           │
│       ✓ Unsafe file operations                              │
│       ✓ Dependency vulnerabilities (CVE check)              │
│    → PASS: result ships                                     │
│    → FAIL: sent back to Worker with security fix required   │
│            (counts toward max_revisions cap)                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                LAYER 3: CONTINUOUS SCANNING                  │
│            (catches issues that slip through)                │
│                                                             │
│  Daemon tick (every 15-20 min):                              │
│    → Security dept scans ALL code in the project            │
│    → Dependency dept checks ALL deps for new CVEs           │
│    → Finds issues that slipped past Layer 2                 │
│    → Opens fix PRs automatically                            │
│    → Reflector: "this vuln pattern slipped through —        │
│       add it to Security Gate checklist"                    │
│       → Layer 2 gets smarter over time                     │
└─────────────────────────────────────────────────────────────┘
```

## Layer 1: Tool Gates (Guardian — real-time)

The Guardian sits between every agent and every tool. No tool executes without Guardian checking it first.

### Permission Matrix

| Permission Level | Examples | Guardian Action |
|---|---|---|
| `READ` | FileTool.read, WebTool.get, brain.query | Allow with logging |
| `WRITE` | FileTool.write, brain.write_note | Allow with logging + audit trail |
| `SHELL` | BashTool.execute | **Pause for approval** (human-in-the-loop or policy) |
| `DESTRUCTIVE` | FileTool.delete, BashTool("rm"), database drops | **Pause for explicit approval + confirmation** |

### Tool-Specific Security Rules

**BashTool:**
- Input sanitization: escape all shell metacharacters (`;`, `|`, `&`, `` ` ``, `$()`, etc.)
- Command allowlist: only approved commands execute (configurable per department)
- Timeout: max 60 seconds per execution
- No root access: runs as unprivileged user
- Output size limit: truncate after 10KB

**FileTool:**
- Path validation: resolve symlinks, reject traversal (`../`), enforce allowed directories
- No writes to: `.git/`, `.env`, system directories, other project boundaries
- File size limit: reject writes over configurable max
- Content scanning: reject files containing secrets patterns before write

**WebTool:**
- SSRF prevention: block requests to:
  - `127.0.0.1`, `localhost`, `0.0.0.0`
  - `169.254.169.254` (cloud metadata)
  - `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x` (private ranges)
  - `::1`, `fc00::/7` (IPv6 private)
- TLS required: reject plain HTTP unless explicitly allowed
- Response size limit: max 5MB
- Timeout: max 30 seconds
- No redirect following to blocked IPs

## Layer 2: Code Review Gate (Security Gate — per output)

This is the critical addition. Every department's output pipeline gets a security review step AFTER the critic approves but BEFORE the result ships.

### How it works in the triad

```
BEFORE (current design):
  Proposer → Worker → Critic → [approve → END]

AFTER (with Security Gate):
  Proposer → Worker → Critic → [approve → Security Gate → END]
                                              │
                                         FAIL → back to Worker
                                         (security fix required)
```

### What the Security Gate checks

For EVERY piece of code agent-os generates:

**Injection Prevention:**
- [ ] SQL queries use parameterized statements, never string concatenation
- [ ] Shell commands use argument lists, never string interpolation
- [ ] HTML output is properly encoded/escaped
- [ ] LDAP queries use proper escaping
- [ ] XML parsing disables external entities (XXE)
- [ ] JSON/YAML parsing uses safe loaders

**Authentication & Authorization:**
- [ ] All endpoints require authentication
- [ ] Authorization checks on every protected resource
- [ ] No hardcoded credentials, API keys, or tokens
- [ ] Passwords hashed with bcrypt/scrypt/argon2, never MD5/SHA1
- [ ] Session tokens are cryptographically random
- [ ] Token expiry configured

**Data Protection:**
- [ ] PII is not logged or stored in plaintext
- [ ] Secrets not in source code, environment properly used
- [ ] Sensitive data encrypted at rest and in transit
- [ ] No sensitive data in error messages or stack traces

**Input Validation:**
- [ ] All external inputs validated (type, length, range, format)
- [ ] File uploads checked (type, size, content)
- [ ] URLs validated before use
- [ ] Numbers checked for overflow/underflow

**Dependency Security:**
- [ ] No dependencies with known CVEs (critical/high)
- [ ] Dependencies pinned to specific versions
- [ ] No unnecessary dependencies added

**Infrastructure:**
- [ ] CORS configured restrictively
- [ ] Security headers set (CSP, HSTS, X-Frame-Options, etc.)
- [ ] Debug mode disabled in production configuration
- [ ] Rate limiting on public endpoints

### Security Gate implementation

```python
class SecurityGate:
    """Mandatory security review on all code-producing department outputs.
    
    Wired as a conditional edge after the Critic node in every
    department sub-graph that produces code.
    """
    
    checks: list[SecurityCheck] = [
        InjectionCheck(),
        SecretsCheck(),
        AuthCheck(),
        InputValidationCheck(),
        DependencyCheck(),
        SSRFCheck(),
        PathTraversalCheck(),
        DeserializationCheck(),
    ]
    
    async def review(self, state: AgentState) -> AgentState:
        """Review the Worker's output for security vulnerabilities."""
        findings = []
        for check in self.checks:
            result = await check.scan(state["result"])
            if result.has_issues:
                findings.extend(result.issues)
        
        if findings:
            # Send back to Worker with security fix requirement
            state["critique"] = {
                "approved": False,
                "reason": "Security Gate failed",
                "findings": findings,
                "fix_required": True,
            }
            state["approved"] = False
            # This counts toward max_revisions
        else:
            state["approved"] = True
        
        return state
```

### Which departments get the Security Gate

| Department | Has Security Gate? | Why |
|---|---|---|
| Engineering | YES | Produces code |
| Backend (all) | YES | Produces code, handles auth, touches DB |
| Frontend (all) | YES | Produces code, XSS risk |
| DevOps | YES | Produces configs, infra-as-code |
| AI/ML | YES | Produces code, model configs |
| Dev Experience (all) | YES | Produces code, tests, CI configs |
| Intelligence | NO | Produces text briefings, not code |
| Growth / Marketing | NO | Produces text content, not code |
| Sales / Support | NO | Produces text, not code |
| Perception | NO | Reads/analyzes, doesn't produce code |

Non-code departments still go through Guardian's tool gates (Layer 1) for any tool calls they make.

## Layer 3: Continuous Scanning (Daemon — proactive)

Even with Layers 1 and 2, some issues will slip through. Layer 3 catches them.

### Every daemon tick

```
Security Department:
  ├─ Full codebase scan (not just new changes)
  ├─ Dependency CVE check (against live vulnerability databases)
  ├─ Secret scanning (git history, environment, brain notes)
  ├─ Configuration audit (debug flags, open endpoints, weak crypto)
  └─ Report: findings → auto-fix PRs for low-risk, alerts for high-risk

Dependency Department:
  ├─ Check all deps against CVE databases
  ├─ Check for outdated packages with known issues
  ├─ Auto-open upgrade PRs for safe updates
  └─ Alert for breaking changes requiring manual review
```

### The learning loop makes security get better over time

```
Week 1:  Security Gate catches SQL injection in generated code
         → Reflector: "Backend department produced SQL injection"
         → Playbook updated: "Always use parameterized queries"
         
Week 2:  Backend Architect reads playbook before drafting
         → Proposer's draft already uses parameterized queries
         → Worker implements correctly from the start
         → Security Gate passes on first try

Week 4:  Same pattern. Backend department hasn't produced a
         SQL injection in 2 weeks. Playbook working.

Week 8:  Security Gate finds a NEW pattern: SSRF in webhook handler
         → Reflector: "Validate webhook URLs against SSRF blocklist"
         → Playbook updated → next run catches it at draft stage

The Security Gate checklist GROWS over time based on what it catches.
```

## Attack Vector Coverage

| Attack Vector | Layer 1 (Tools) | Layer 2 (Code Gate) | Layer 3 (Scanning) |
|---|---|---|---|
| SQL Injection | — | Parameterized query check | Full codebase scan |
| Command Injection | BashTool sanitization | Shell command check | Pattern scan |
| XSS | — | Output encoding check | Frontend scan |
| SSRF | WebTool IP blocklist | URL validation check | Network config audit |
| Path Traversal | FileTool path validation | File operation check | Permission scan |
| Secrets in Code | — | Secrets pattern check | Git history scan |
| Insecure Deserialization | — | Pickle/YAML check | Import scan |
| Broken Auth | — | Auth/authz check | Endpoint audit |
| Broken Access Control | Guardian permissions | Authorization check | Permission scan |
| Security Misconfiguration | — | Config check | Full config audit |
| Vulnerable Dependencies | — | Dep version check | CVE database scan |
| XXE | — | XML parser check | Parser config scan |
| CSRF | — | Token check | Form/API audit |
| Open Redirect | WebTool URL validation | Redirect check | URL pattern scan |
| Race Conditions | — | TOCTOU check | Concurrency audit |
| Privilege Escalation | Guardian permission levels | Role check | Permission scan |
| Data Exposure | — | PII/logging check | Log/output scan |
| DDoS/Rate Limiting | — | Rate limit check | Endpoint audit |
| Man-in-the-Middle | WebTool TLS requirement | TLS config check | Certificate audit |
| Cryptographic Failures | — | Crypto algorithm check | Crypto usage scan |

## Implementation Impact on Phases

| Phase | What to add |
|---|---|
| Phase 0 | SecurityGate base class in `/agents/security_gate.py` |
| Phase 1 | Brain: no PII/secrets in notes. Tools: SSRF blocklist, path validation, input sanitization |
| Phase 2 | Wire SecurityGate as conditional edge after Critic in Engineering sub-graph |
| Phase 3 | SecurityGate on Intelligence outputs (validate URLs, no credential logging) |
| Phase 4 | Guardian + SecurityGate integration. Reflector feeds findings back to gate |
| Phase 5 | Dashboard: auth on all endpoints, CORS, CSP headers, WebSocket auth |
| Phase 6 | Composio: OAuth token security, minimal scopes, secure storage |
| Phase 7 | SecurityGate wired into every code-producing department |
| Phase 8 | Full security audit validates all three layers work end-to-end |

## Non-Negotiable Security Rules

1. **No code ships without Security Gate** — every code-producing department's sub-graph includes the gate.
2. **No tool executes without Guardian** — permission check on every single tool call.
3. **No secrets in source** — secrets scanner runs on every output and every daemon tick.
4. **No internal network access** — WebTool blocks private IPs and metadata endpoints.
5. **No arbitrary file access** — FileTool enforces directory boundaries.
6. **No unsanitized shell commands** — BashTool escapes all metacharacters.
7. **Security Gate grows** — Reflector adds new checks based on what it catches. The gate is never "done."
8. **Defense in depth** — three layers so no single point of failure. Layer 2 catches what Layer 1 misses. Layer 3 catches what Layer 2 misses. Reflector teaches Layer 2 what Layer 3 found.
