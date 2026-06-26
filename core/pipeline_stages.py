"""Stage implementations for the 9-stage code pipeline.

PLAN → SCAFFOLD → BUILD → TEST → DEBUG → REVIEW → AUDIT → PROD-READY → PUSH

Each stage is a function that takes the current ``PipelineState`` and returns a
dict update. Stages are stack-agnostic: they read ``stack_info`` (produced by
``core.stack_detector``) and adapt their commands, test frameworks, and checks
to whatever the user is running.

The graph in ``core.pipeline`` binds the brain/tool dependencies into these
functions; on their own they are pure functions of state plus optional deps,
which keeps them easy to unit test.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from agents.llm import call_llm
from core.stack_detector import StackInfo, detect_stack, format_stack_summary
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("core.pipeline.stages")


class PipelineState(AgentState, total=False):
    stage: str
    project_path: str | None
    stack_info: dict
    codebase_context: str
    debug_source: str
    debug_count: int
    test_results: str | None
    review_findings: list[str]
    audit_findings: list[str]
    prod_ready_verdict: str | None
    files_changed: list[str]
    push_result: str | None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _stack_from_state(state: PipelineState) -> StackInfo:
    """Reconstruct a StackInfo from the dict stored in state.

    The pipeline stores stack info as a plain dict so it stays serializable in
    the checkpointer. We rebuild the dataclass for ergonomic access.
    """
    raw = state.get("stack_info") or {}
    if not raw:
        return StackInfo(language="unknown")
    known = {f for f in StackInfo.__dataclass_fields__}
    return StackInfo(**{k: v for k, v in raw.items() if k in known})


def _stack_to_dict(info: StackInfo) -> dict:
    from dataclasses import asdict

    return asdict(info)


def _files_for(state: PipelineState) -> list[str]:
    return list(state.get("files_changed") or [])


async def _run_shell(command: str, cwd: str | None = None) -> str:
    """Run a shell command and return combined output. Does NOT go through
    Guardian/BashTool permission — this is the pipeline's internal execution
    layer. All commands here are deterministic build tools (test runners,
    linters, git), not arbitrary user input.
    """
    import asyncio
    import os

    env = os.environ.copy()
    if cwd:
        env["PWD"] = cwd

    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return f"error: command timed out after 120s\nexit_code: -1"

    out = stdout.decode(errors="replace")[:10240]
    err = stderr.decode(errors="replace")[:10240]
    return f"stdout:\n{out}\nstderr:\n{err}\nexit_code: {proc.returncode}"


def _parse_exit_code(output: str) -> int:
    import re
    m = re.search(r"exit_code:\s*(-?\d+)", output)
    return int(m.group(1)) if m else -1


def _shell_quote(s: str) -> str:
    import shlex
    return shlex.quote(s)


def _write_files_from_output(output: str, project_path: str | None) -> list[str]:
    """Parse '--- path/to/file ---' markers from LLM output and write files to disk."""
    import re
    import os

    if not project_path:
        return []

    blocks = re.split(r"---\s*(.+?)\s*---", output)
    written: list[str] = []

    # blocks[0] is preamble, then alternating: path, content, path, content...
    i = 1
    while i < len(blocks) - 1:
        rel_path = blocks[i].strip()
        content = blocks[i + 1]
        i += 2

        if not rel_path or "/" not in rel_path and "." not in rel_path:
            continue

        # Strip leading/trailing markdown code fences if present
        content = re.sub(r"^```\w*\n?", "", content.strip())
        content = re.sub(r"\n?```$", "", content.strip())

        full_path = os.path.join(project_path, rel_path)

        # Safety: don't write outside the project
        real_project = os.path.realpath(project_path)
        real_target = os.path.realpath(full_path)
        if not real_target.startswith(real_project):
            logger.warning("path traversal blocked: %s", rel_path)
            continue

        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            written.append(rel_path)
        except OSError as e:
            logger.warning("failed to write %s: %s", rel_path, e)

    return written


def _prod_check_commands(info: StackInfo) -> list[tuple[str, str | None]]:
    """Return (name, command) pairs for production checks based on stack."""
    checks: list[tuple[str, str | None]] = []

    if info.language == "python":
        checks.append(("lint", "ruff check . --no-fix 2>&1 || flake8 . 2>&1 || true"))
        checks.append(("typecheck", "mypy . --ignore-missing-imports 2>&1 || true"))
    elif info.language == "typescript":
        checks.append(("typecheck", "npx tsc --noEmit 2>&1"))
        checks.append(("lint", "npx eslint . 2>&1 || true"))
    elif info.language == "javascript":
        checks.append(("lint", "npx eslint . 2>&1 || true"))
    elif info.language == "go":
        checks.append(("vet", "go vet ./... 2>&1"))
        checks.append(("lint", "golangci-lint run 2>&1 || true"))
    elif info.language == "rust":
        checks.append(("check", "cargo check 2>&1"))
        checks.append(("clippy", "cargo clippy 2>&1 || true"))

    if info.package_manager == "npm":
        checks.append(("audit", "npm audit --production 2>&1 || true"))
    elif info.package_manager == "pip":
        checks.append(("audit", "pip-audit 2>&1 || safety check 2>&1 || true"))

    return checks


# --------------------------------------------------------------------------- #
# PLAN
# --------------------------------------------------------------------------- #

async def plan_stage(
    state: PipelineState,
    librarian=None,
    obsidian=None,
    tool_registry=None,
) -> dict:
    """Read brain + codebase context, detect the stack, produce a plan via LLM."""
    request = state.get("request", "")

    brain_context: list[dict] = list(state.get("brain_context") or [])
    if librarian:
        for note in librarian.query(request):
            brain_context.append({"title": note.title, "content": note.content})
    if obsidian:
        from brain.playbook import get_playbooks

        for pb in get_playbooks("engineering", obsidian):
            brain_context.append({"title": pb.title, "content": pb.content})

    info = _stack_from_state(state)
    project_path = state.get("project_path")
    if info.language == "unknown" and not state.get("stack_info"):
        import os

        project_path = project_path or os.getcwd()
        info = detect_stack(project_path)

    # Analyze the existing codebase to understand its architecture
    codebase_context = ""
    if project_path:
        try:
            from core.codebase_analyzer import analyze_codebase, format_context
            ctx = analyze_codebase(project_path, info)
            codebase_context = format_context(ctx)
        except Exception as e:
            logger.warning("codebase analysis failed: %s", e)

    stack_summary = format_stack_summary(info)
    user_prompt = f"Request: {request}\n\nDetected stack:\n{stack_summary}"

    if codebase_context:
        user_prompt += f"\n\n=== EXISTING CODEBASE ANALYSIS ===\n{codebase_context}"

    if brain_context:
        ctx_text = "\n".join(f"- {c['title']}: {c['content'][:200]}" for c in brain_context)
        user_prompt += f"\n\nPrior knowledge from brain:\n{ctx_text}"

    plan = await call_llm(
        task_type="code",
        system=(
            "You are a software architect planning changes to an EXISTING codebase. "
            "You have been given a full analysis of the current project — its directory "
            "structure, models, routes, config, and key source files. Use this to:\n"
            "1. Understand what the app already does and how it's structured\n"
            "2. Follow existing patterns and conventions (naming, file layout, imports)\n"
            "3. Identify which existing files to modify vs which new files to create\n"
            "4. Preserve existing functionality — don't break what works\n\n"
            "Produce a build plan with:\n"
            "- Files to modify (with what changes)\n"
            "- Files to create (with paths matching existing conventions)\n"
            "- Data model changes (new tables/columns, migrations)\n"
            "- API contracts (endpoints, request/response shapes)\n"
            "- How the new code integrates with existing code\n"
            "- Edge cases and failure modes\n"
            "Be specific — name every file, function signature, and data shape."
        ),
        user=user_prompt,
    )

    logger.info("PLAN produced for request=%r stack=%s", request[:80], info.language)
    return {
        "stage": "plan",
        "draft": plan,
        "brain_context": brain_context,
        "stack_info": _stack_to_dict(info),
    }


# --------------------------------------------------------------------------- #
# SCAFFOLD
# --------------------------------------------------------------------------- #

async def scaffold_stage(state: PipelineState, **_deps) -> dict:
    """Turn the plan into a concrete file list + scaffold commands via LLM."""
    request = state.get("request", "")
    draft = state.get("draft", "")
    info = _stack_from_state(state)

    fallback_files = _scaffold_files(info, request)

    scaffold_output = await call_llm(
        task_type="code",
        system=(
            "You are a code scaffolder. Given an architect's plan and tech stack:\n"
            "1. List every file to create with full paths\n"
            "2. Write type definitions, interfaces, and class signatures\n"
            "3. Create empty test files alongside source files\n"
            "4. Use the stack's native patterns (e.g. Rails generators, Next.js app dir)\n"
            "5. Output the full file contents for each file\n"
            "Mark each file with its path on a '--- path/to/file ---' line."
        ),
        user=f"Plan:\n{draft}\n\nStack: {info.language}/{info.framework or 'none'}\n\nRequest: {request}",
    )

    files = _extract_file_paths(scaffold_output) or fallback_files

    logger.info("SCAFFOLD listed %d files for stack=%s", len(files), info.language)
    return {
        "stage": "scaffold",
        "result": scaffold_output,
        "files_changed": files,
    }


def _extract_file_paths(text: str) -> list[str]:
    """Pull file paths from scaffold output (lines like '--- path/to/file ---')."""
    import re
    paths = re.findall(r"---\s*(.+?)\s*---", text)
    return [p.strip() for p in paths if "/" in p or "." in p]


def _scaffold_files(info: StackInfo, request: str) -> list[str]:
    fw = info.framework
    lang = info.language
    if fw == "laravel":
        return [
            "app/Models/Resource.php",
            "app/Http/Controllers/ResourceController.php",
            "database/migrations/0001_create_resources_table.php",
            "routes/api.php",
            "tests/Feature/ResourceTest.php",
        ]
    if fw == "django":
        return [
            "app/models.py",
            "app/views.py",
            "app/urls.py",
            "app/migrations/0001_initial.py",
            "app/tests.py",
        ]
    if fw in ("fastapi", "flask"):
        return ["app/routes.py", "app/models.py", "app/schemas.py", "tests/test_app.py"]
    if fw in ("nextjs", "react", "nuxt", "svelte", "astro", "vue", "angular"):
        ext = "tsx" if lang == "typescript" else "jsx"
        return [
            f"src/components/Feature.{ext}",
            "src/lib/api.ts" if lang == "typescript" else "src/lib/api.js",
            f"src/__tests__/Feature.test.{ext}",
        ]
    if fw == "rails":
        return [
            "app/models/resource.rb",
            "app/controllers/resources_controller.rb",
            "db/migrate/0001_create_resources.rb",
            "spec/models/resource_spec.rb",
        ]
    # Language-level fallback
    suffix = {
        "python": ("src/feature.py", "tests/test_feature.py"),
        "go": ("feature.go", "feature_test.go"),
        "rust": ("src/feature.rs", "tests/feature_test.rs"),
        "java": ("src/main/java/Feature.java", "src/test/java/FeatureTest.java"),
        "csharp": ("Feature.cs", "FeatureTests.cs"),
    }.get(lang, ("src/feature", "tests/test_feature"))
    return list(suffix)


def _scaffold_commands(info: StackInfo, files: list[str]) -> list[str]:
    if not info.scaffold_commands:
        return []
    cmds: list[str] = []
    for kind, base in info.scaffold_commands.items():
        cmds.append(f"{base} Resource  # {kind}")
    return cmds


# --------------------------------------------------------------------------- #
# BUILD
# --------------------------------------------------------------------------- #

async def build_stage(state: PipelineState, **_deps) -> dict:
    """Produce the implementation via LLM. Honors DEBUG feedback on revision loops."""
    info = _stack_from_state(state)
    files = _files_for(state)
    critique = state.get("critique")
    debug_count = state.get("debug_count", 0)
    draft = state.get("draft", "")
    scaffold = state.get("result", "")
    request = state.get("request", "")

    user_prompt = (
        f"Plan:\n{draft}\n\n"
        f"Scaffold (file structure + signatures):\n{scaffold}\n\n"
        f"Original request: {request}\n\n"
        f"Stack: {info.language}/{info.framework or 'none'}\n"
        f"Files to implement: {', '.join(files)}"
    )

    if critique and debug_count > 0:
        fixes = (critique or {}).get("fixes") if isinstance(critique, dict) else None
        user_prompt += f"\n\nThis is revision {debug_count}/3. Fix these issues:\n"
        if fixes:
            user_prompt += "\n".join(f"- {f}" for f in fixes)
        else:
            suggestions = (critique or {}).get("suggestions", [])
            user_prompt += "\n".join(f"- {s}" for s in suggestions)

    result = await call_llm(
        task_type="code",
        system=(
            "You are a senior developer. Given a plan and scaffold, write the full "
            "implementation for every file. Write production-quality code:\n"
            "- Real business logic, not stubs or TODOs\n"
            "- Input validation on all external boundaries\n"
            "- Proper error handling\n"
            "- Type annotations where the language supports them\n"
            "- No hardcoded secrets or credentials\n"
            "Output each file with '--- path/to/file ---' markers."
        ),
        user=user_prompt,
    )

    # Write files to disk
    project_path = state.get("project_path")
    written = _write_files_from_output(result, project_path)
    if written:
        files = written
        logger.info("BUILD wrote %d files to disk", len(written))

    logger.info("BUILD implemented %d files (debug_count=%d)", len(files), debug_count)
    return {"stage": "build", "result": result, "files_changed": files}


# --------------------------------------------------------------------------- #
# TEST
# --------------------------------------------------------------------------- #

async def test_stage(state: PipelineState, **_deps) -> dict:
    """Run the actual test command. Only calls LLM to analyze failures."""
    info = _stack_from_state(state)
    command = info.test_command or "pytest -v"
    project_path = state.get("project_path")

    # Run the real test command via BashTool
    test_output = await _run_shell(command, cwd=project_path)
    exit_code = _parse_exit_code(test_output)
    passed = exit_code == 0

    test_results = test_output
    if not passed:
        # Only call LLM to analyze failures — don't waste tokens on green runs
        analysis = await call_llm(
            task_type="code",
            system=(
                "You are a test engineer. Given failing test output, analyze:\n"
                "1. Which tests failed and why\n"
                "2. Whether failures are in new code or regressions\n"
                "3. Root cause for each failure\n"
                "Output as bullet points."
            ),
            user=f"Test command: {command}\n\nTest output:\n{test_output}",
        )
        test_results = f"Test output:\n{test_output}\n\nAnalysis:\n{analysis}"

    logger.info("TEST command=%r exit_code=%d passed=%s", command, exit_code, passed)
    update: dict = {
        "stage": "test",
        "test_results": test_results,
        "result": test_results,
        "approved": passed,
    }
    if not passed:
        update["debug_source"] = "test"
    return update


# --------------------------------------------------------------------------- #
# DEBUG
# --------------------------------------------------------------------------- #

async def debug_stage(state: PipelineState, **_deps) -> dict:
    """Read the failing stage output, use LLM to find root cause and produce fixes."""
    source = state.get("debug_source", "test")
    count = state.get("debug_count", 0) + 1
    result = state.get("result", "")

    source_output = {
        "test": state.get("test_results"),
        "review": _join(state.get("review_findings")),
        "audit": _join(state.get("audit_findings")),
        "prod_ready": state.get("prod_ready_verdict"),
    }.get(source)

    debug_analysis = await call_llm(
        task_type="code",
        system=(
            "You are a debugger. Given a failing stage's output and the implementation:\n"
            "1. Identify the exact root cause of each failure\n"
            "2. Produce specific, actionable fixes (file, line, what to change)\n"
            "3. Do NOT rewrite the code — describe the fixes precisely\n"
            "Output each fix as a bullet point starting with '- '"
        ),
        user=(
            f"Failing stage: {source} (debug loop {count}/3)\n\n"
            f"Stage output:\n{source_output or 'no diagnostic captured'}\n\n"
            f"Current implementation:\n{result}"
        ),
    )

    fixes = [
        line.strip().lstrip("-•* ")
        for line in debug_analysis.strip().split("\n")
        if line.strip().startswith(("-", "•", "*"))
    ]
    if not fixes:
        fixes = _derive_fixes(source, source_output)

    logger.info("DEBUG source=%s loop=%d fixes=%d", source, count, len(fixes))
    return {
        "stage": "debug",
        "result": debug_analysis,
        "debug_count": count,
        "critique": {"source": source, "fixes": fixes},
    }


def _derive_fixes(source: str, output: str | None) -> list[str]:
    text = (output or "").lower()
    fixes: list[str] = []
    if "null" in text or "500" in text or source == "test":
        fixes.append("Add validation/null-guard on the request payload before use.")
    if source == "review":
        fixes.append("Address review findings: error handling + naming + DRY.")
    if source == "audit":
        fixes.append("Remediate security findings before re-running the gate.")
    if source == "prod_ready":
        fixes.append("Add observability + rollback hooks flagged by prod-ready.")
    if not fixes:
        fixes.append("Re-derive the failing assertion and correct the logic.")
    return fixes


def _join(items) -> str | None:
    if not items:
        return None
    return "; ".join(items)


# --------------------------------------------------------------------------- #
# REVIEW
# --------------------------------------------------------------------------- #

async def review_stage(state: PipelineState, **_deps) -> dict:
    """Code review via LLM: architecture, quality, correctness, DRY, error handling."""
    info = _stack_from_state(state)
    result = state.get("result", "")
    draft = state.get("draft", "")

    review_output = await call_llm(
        task_type="code",
        system=(
            "You are a senior code reviewer. Review the implementation against the plan:\n"
            "- Architecture compliance (correct patterns for the stack)\n"
            "- Code quality (naming, DRY, complexity)\n"
            "- Correctness (logic errors, off-by-one, race conditions)\n"
            "- Error handling (unhandled exceptions, missing try/catch)\n"
            "- N+1 queries (DB calls in loops)\n"
            "- Performance (unnecessary re-renders, blocking I/O)\n\n"
            "If everything is good, say 'APPROVED — no blocking findings.'\n"
            "Otherwise, list each finding as a bullet starting with '- '.\n"
            "Only flag real issues, not style preferences."
        ),
        user=f"Plan:\n{draft}\n\nImplementation to review:\n{result}\n\nStack: {info.language}/{info.framework or 'none'}",
    )

    findings = []
    if "APPROVED" not in review_output.upper():
        findings = [
            line.strip().lstrip("-•* ")
            for line in review_output.strip().split("\n")
            if line.strip().startswith(("-", "•", "*")) and len(line.strip()) > 5
        ]

    logger.info("REVIEW findings=%d", len(findings))
    update: dict = {
        "stage": "review",
        "review_findings": findings,
        "result": review_output,
        "approved": not findings,
    }
    if findings:
        update["debug_source"] = "review"
    return update


# --------------------------------------------------------------------------- #
# AUDIT
# --------------------------------------------------------------------------- #

_SECURITY_CHECKLIST = [
    "SQL queries parameterized (no string concatenation)",
    "Shell commands use argument lists (no string interpolation)",
    "HTML output encoded/escaped (no XSS)",
    "XML parsing disables external entities (XXE)",
    "JSON/YAML parsing uses safe loaders (no unsafe deserialization)",
    "All endpoints require authentication",
    "Authorization checks on protected resources",
    "No hardcoded credentials/API keys/tokens",
    "Passwords hashed with bcrypt/scrypt/argon2",
    "Secrets read from env, not source",
    "All external inputs validated (type/length/range/format)",
    "URLs validated before use (no SSRF)",
    "No file/path traversal on user-supplied paths",
    "No dependencies with known critical/high CVEs",
    "Security headers + restrictive CORS configured",
]


async def audit_stage(state: PipelineState, **_deps) -> dict:
    """Run the 15-point security checklist via LLM against the build output."""
    result = state.get("result", "")

    checklist_text = "\n".join(f"  {i}. {item}" for i, item in enumerate(_SECURITY_CHECKLIST, 1))

    audit_output = await call_llm(
        task_type="code",
        system=(
            "You are a security auditor. Review the implementation against this "
            "15-point security checklist:\n"
            f"{checklist_text}\n\n"
            "For each item, output '[PASS]' or '[FAIL]' with explanation.\n"
            "At the end, if ALL items pass, say 'VERDICT: PASS'.\n"
            "If any item fails, say 'VERDICT: FAIL' and list each finding "
            "as a bullet starting with '- '."
        ),
        user=f"Implementation to audit:\n{result}",
    )

    findings = []
    if "VERDICT: FAIL" in audit_output.upper() or "[FAIL]" in audit_output.upper():
        findings = [
            line.strip().lstrip("-•* ")
            for line in audit_output.strip().split("\n")
            if line.strip().startswith(("-", "•", "*")) and len(line.strip()) > 5
        ]
        if not findings:
            findings = ["Security audit flagged issues — see full output."]

    logger.info("AUDIT findings=%d", len(findings))
    update: dict = {
        "stage": "audit",
        "audit_findings": findings,
        "result": audit_output,
        "approved": not findings,
    }
    if findings:
        update["debug_source"] = "audit"
    return update


# --------------------------------------------------------------------------- #
# PROD-READY
# --------------------------------------------------------------------------- #

_PROD_CHECKS = [
    "reliability (retries, timeouts, graceful degradation)",
    "observability (structured logs, metrics, tracing)",
    "performance (no obvious hot-path regressions)",
    "config (env-driven, no hardcoded hosts)",
    "documentation (README / changelog updated)",
    "rollback (migration is reversible, deploy revertible)",
]


async def prod_ready_stage(state: PipelineState, **_deps) -> dict:
    """Run real linter/type-checker/dep-audit, then LLM reviews remaining concerns."""
    info = _stack_from_state(state)
    result = state.get("result", "")
    project_path = state.get("project_path")

    # Run real checks — no LLM needed for these
    check_results: list[tuple[str, bool, str]] = []
    for name, cmd in _prod_check_commands(info):
        if cmd:
            output = await _run_shell(cmd, cwd=project_path)
            passed = _parse_exit_code(output) == 0
            check_results.append((name, passed, output))

    # LLM reviews the code for things tools can't check (architecture, rollback plan, etc.)
    checks_text = "\n".join(f"  - {check}" for check in _PROD_CHECKS)
    tool_summary = "\n".join(
        f"  {name}: {'PASS' if ok else 'FAIL'}" for name, ok, _ in check_results
    )

    prod_output = await call_llm(
        task_type="code",
        system=(
            "You are a production readiness reviewer. Automated tool checks "
            "have already run (results below). Review the implementation for:\n"
            f"{checks_text}\n\n"
            "Focus on things the tools can't catch: architecture, observability, "
            "rollback strategy, config management.\n"
            "At the end: 'VERDICT: READY' if acceptable, 'VERDICT: NOT READY' if not."
        ),
        user=(
            f"Automated check results:\n{tool_summary}\n\n"
            f"Implementation:\n{result}\n\n"
            f"Stack: {info.language}/{info.framework or 'none'}"
        ),
    )

    tool_failures = [name for name, ok, _ in check_results if not ok]
    ready = "VERDICT: READY" in prod_output.upper() and not tool_failures

    logger.info("PROD-READY verdict=%s tool_failures=%s", "READY" if ready else "NOT READY", tool_failures)
    update: dict = {
        "stage": "prod_ready",
        "prod_ready_verdict": "READY" if ready else "NOT READY",
        "result": prod_output,
        "approved": ready,
    }
    if not ready:
        update["debug_source"] = "prod_ready"
    return update


# --------------------------------------------------------------------------- #
# PUSH
# --------------------------------------------------------------------------- #

async def push_stage(state: PipelineState, **_deps) -> dict:
    """Stage files, commit, and push. LLM writes the commit message only."""
    request = state.get("request", "")
    files = _files_for(state)
    project_path = state.get("project_path")
    implementation = state.get("result", "")

    # LLM writes a good commit message — this is a reasoning task
    commit_msg = await call_llm(
        task_type="code",
        system=(
            "Write a conventional commit message for these changes. "
            "First line: type(scope): summary (under 72 chars). "
            "Blank line, then 2-3 bullet points of what changed. "
            "Types: feat, fix, refactor, docs, test, chore. "
            "Output ONLY the commit message, nothing else."
        ),
        user=f"Request: {request}\n\nFiles changed: {', '.join(files)}\n\nSummary:\n{implementation[:1500]}",
    )

    # Run real git commands
    results: list[str] = []
    if files:
        file_args = " ".join(f'"{f}"' for f in files)
        add_out = await _run_shell(f"git add {file_args}", cwd=project_path)
        results.append(f"git add: {add_out}")
    else:
        add_out = await _run_shell("git add -A", cwd=project_path)
        results.append(f"git add -A: {add_out}")

    commit_out = await _run_shell(
        f"git commit -m {_shell_quote(commit_msg)}", cwd=project_path
    )
    results.append(f"git commit: {commit_out}")

    push_output = "\n".join(results)
    committed = "exit_code: 0" in commit_out

    logger.info("PUSH committed=%s for request=%r", committed, request[:80])
    return {
        "stage": "push",
        "push_result": push_output,
        "result": push_output,
        "approved": committed,
    }


def _commit_subject(request: str) -> str:
    first = (request or "change").strip().splitlines()[0]
    first = first[0].lower() + first[1:] if first else "change"
    return f"feat: {first[:60]}"


# --------------------------------------------------------------------------- #
# ESCALATE
# --------------------------------------------------------------------------- #

async def escalate_stage(state: PipelineState, **_deps) -> dict:
    """Max debug loops exceeded — hand off to a human."""
    count = state.get("debug_count", 0)
    source = state.get("debug_source", "unknown")
    logger.warning("pipeline escalating after %d debug loops (last source=%s)", count, source)
    return {
        "stage": "escalate",
        "result": (
            f"ESCALATION: pipeline exceeded {count} debug loops "
            f"(last failing stage: {source}). Requires human review."
        ),
        "approved": False,
    }
