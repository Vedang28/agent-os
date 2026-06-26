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
    stack_info: dict
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


# --------------------------------------------------------------------------- #
# PLAN
# --------------------------------------------------------------------------- #

async def plan_stage(
    state: PipelineState,
    librarian=None,
    obsidian=None,
    tool_registry=None,
) -> dict:
    """Read brain context + playbooks, detect the stack, produce a plan via LLM."""
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
    if info.language == "unknown" and not state.get("stack_info"):
        import os

        info = detect_stack(os.getcwd())

    stack_summary = format_stack_summary(info)
    user_prompt = f"Request: {request}\n\nDetected stack:\n{stack_summary}"
    if brain_context:
        ctx_text = "\n".join(f"- {c['title']}: {c['content'][:200]}" for c in brain_context)
        user_prompt = f"Prior knowledge:\n{ctx_text}\n\n{user_prompt}"

    plan = await call_llm(
        task_type="code",
        system=(
            "You are a software architect creating a build plan. Given a request and "
            "detected tech stack, produce:\n"
            "1. Component/module breakdown with file paths\n"
            "2. Data model and API contracts\n"
            "3. Architecture decisions (framework patterns, data layer)\n"
            "4. Edge cases and failure modes\n"
            "5. Scope estimate (files, complexity)\n"
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

    logger.info("BUILD implemented %d files (debug_count=%d)", len(files), debug_count)
    return {"stage": "build", "result": result}


# --------------------------------------------------------------------------- #
# TEST
# --------------------------------------------------------------------------- #

async def test_stage(state: PipelineState, **_deps) -> dict:
    """Write and evaluate tests via LLM, then determine pass/fail."""
    info = _stack_from_state(state)
    command = info.test_command or "pytest -v"
    files = _files_for(state)
    result = state.get("result", "")
    request = state.get("request", "")

    test_review = await call_llm(
        task_type="code",
        system=(
            "You are a test engineer. Given implementation code:\n"
            "1. Write comprehensive tests (unit + integration)\n"
            "2. Cover happy paths, error paths, and edge cases\n"
            "3. Use the stack's test framework\n"
            "4. Review the implementation for bugs\n"
            "5. At the end, output a verdict line: 'VERDICT: PASS' or 'VERDICT: FAIL'\n"
            "   If FAIL, list specific failures with file, test name, and root cause.\n"
            f"Test framework: {info.test_framework or 'default'}\n"
            f"Test command: {command}"
        ),
        user=f"Implementation to test:\n{result}\n\nRequest: {request}",
    )

    passed = "VERDICT: PASS" in test_review.upper()
    logger.info("TEST command=%r passed=%s", command, passed)
    update: dict = {
        "stage": "test",
        "test_results": test_review,
        "result": test_review,
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
    """Production-readiness gate via LLM across reliability/observability/etc."""
    info = _stack_from_state(state)
    result = state.get("result", "")

    checks_text = "\n".join(f"  - {check}" for check in _PROD_CHECKS)

    prod_output = await call_llm(
        task_type="code",
        system=(
            "You are a production readiness reviewer. Check the implementation for:\n"
            f"{checks_text}\n\n"
            "For each check, assess PASS or FAIL with brief explanation.\n"
            "At the end: 'VERDICT: READY' if all pass, 'VERDICT: NOT READY' if any fail.\n"
            "List actionable fixes for any FAIL items."
        ),
        user=f"Implementation:\n{result}\n\nStack: {info.language}/{info.framework or 'none'}",
    )

    ready = "VERDICT: READY" in prod_output.upper()

    logger.info("PROD-READY verdict=%s", "READY" if ready else "NOT READY")
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
    """Produce commit message + PR description via LLM, stage specific files only."""
    request = state.get("request", "")
    files = _files_for(state)
    info = _stack_from_state(state)
    implementation = state.get("result", "")

    push_output = await call_llm(
        task_type="code",
        system=(
            "You are a release manager. Given the implementation and request:\n"
            "1. Write a conventional commit message (feat:/fix:/refactor:)\n"
            "2. Write a PR description with Summary, Changes, and Test Plan sections\n"
            "3. List the exact files to stage (never 'git add -A')\n"
            "4. Note the git commands to run"
        ),
        user=(
            f"Request: {request}\n\n"
            f"Stack: {info.language}/{info.framework or 'none'}\n"
            f"Files changed: {', '.join(files)}\n\n"
            f"Implementation summary:\n{implementation[:2000]}"
        ),
    )

    logger.info("PUSH prepared commit for request=%r", request[:80])
    return {"stage": "push", "push_result": push_output, "result": push_output, "approved": True}


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
