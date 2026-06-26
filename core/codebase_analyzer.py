"""Analyzes an existing codebase to understand its architecture and intent.

Used by the PLAN stage to feed real project context to the LLM so agents
understand what the app does — not just what stack it uses.

Flow:
  1. stack_detector.detect_stack() → language, framework, ORM, etc.
  2. analyze_codebase() → reads key files, extracts models/routes/config,
     builds a structured summary the LLM can reason over.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from agents.llm import call_llm
from core.stack_detector import StackInfo
from infra.telemetry import get_logger

logger = get_logger("core.codebase_analyzer")

MAX_FILE_READ = 8000
MAX_FILES_TO_READ = 30
MAX_TOTAL_CHARS = 80_000


@dataclass
class CodebaseContext:
    project_path: str
    stack: StackInfo
    readme: str = ""
    entry_points: list[dict] = field(default_factory=list)
    models: list[dict] = field(default_factory=list)
    routes: list[dict] = field(default_factory=list)
    config_files: list[dict] = field(default_factory=list)
    directory_tree: str = ""
    key_files: list[dict] = field(default_factory=list)
    summary: str = ""


def analyze_codebase(project_path: str, stack: StackInfo) -> CodebaseContext:
    """Build a structured understanding of an existing codebase."""
    ctx = CodebaseContext(project_path=project_path, stack=stack)

    ctx.directory_tree = _build_tree(project_path, max_depth=3)
    ctx.readme = _read_readme(project_path)
    ctx.entry_points = _find_entry_points(project_path, stack)
    ctx.models = _find_models(project_path, stack)
    ctx.routes = _find_routes(project_path, stack)
    ctx.config_files = _find_config(project_path, stack)
    ctx.key_files = _read_key_files(project_path, stack)

    logger.info(
        "analyzed codebase: %d entry_points, %d models, %d routes, %d config, %d key_files",
        len(ctx.entry_points), len(ctx.models), len(ctx.routes),
        len(ctx.config_files), len(ctx.key_files),
    )
    return ctx


async def summarize_codebase(ctx: CodebaseContext) -> str:
    """Use the LLM to produce a natural-language summary of the codebase."""
    sections = [format_context(ctx)]

    summary = await call_llm(
        task_type="long_docs",
        system=(
            "You are a senior developer joining a new project. Given the codebase "
            "analysis below, produce a concise summary covering:\n"
            "1. What the app does (purpose, domain, users)\n"
            "2. Architecture (monolith/microservices, API style, rendering)\n"
            "3. Data model (key entities and relationships)\n"
            "4. Key patterns and conventions used\n"
            "5. External dependencies and integrations\n"
            "Be specific — name actual files, models, and routes. Under 500 words."
        ),
        user="\n".join(sections),
    )
    ctx.summary = summary
    return summary


def format_context(ctx: CodebaseContext) -> str:
    """Format the codebase context as text for LLM prompts."""
    lines = [
        f"Project: {ctx.project_path}",
        f"Stack: {ctx.stack.language}/{ctx.stack.framework or 'none'}",
        "",
    ]

    if ctx.readme:
        lines.append("=== README (first 2000 chars) ===")
        lines.append(ctx.readme[:2000])
        lines.append("")

    lines.append("=== Directory Structure ===")
    lines.append(ctx.directory_tree)
    lines.append("")

    if ctx.entry_points:
        lines.append("=== Entry Points ===")
        for ep in ctx.entry_points:
            lines.append(f"  {ep['path']}: {ep.get('description', '')}")
        lines.append("")

    if ctx.models:
        lines.append("=== Models / Entities ===")
        for m in ctx.models:
            lines.append(f"  {m['name']} ({m['path']})")
            if m.get("fields"):
                lines.append(f"    fields: {', '.join(m['fields'][:10])}")
        lines.append("")

    if ctx.routes:
        lines.append("=== Routes / Endpoints ===")
        for r in ctx.routes:
            lines.append(f"  {r.get('method', 'GET')} {r['path']} -> {r.get('handler', '?')}")
        lines.append("")

    if ctx.config_files:
        lines.append("=== Configuration ===")
        for cf in ctx.config_files:
            lines.append(f"  {cf['path']}: {cf.get('description', '')}")
        lines.append("")

    if ctx.key_files:
        lines.append("=== Key Source Files ===")
        for kf in ctx.key_files:
            lines.append(f"--- {kf['path']} ---")
            lines.append(kf['content'][:MAX_FILE_READ])
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_file(path: str, max_chars: int = MAX_FILE_READ) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_chars)
    except OSError:
        return ""


def _read_readme(project_path: str) -> str:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        p = os.path.join(project_path, name)
        if os.path.isfile(p):
            return _read_file(p, 4000)
    return ""


def _build_tree(project_path: str, max_depth: int = 3) -> str:
    skip = {
        "node_modules", ".git", "__pycache__", ".next", ".nuxt", "dist",
        "build", ".cache", ".venv", "venv", "vendor", ".idea", ".vscode",
        "coverage", ".pytest_cache", ".mypy_cache", "target",
    }
    lines: list[str] = []

    def walk(path: str, prefix: str, depth: int):
        if depth > max_depth or len(lines) > 200:
            return
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            return
        dirs = [e for e in entries if os.path.isdir(os.path.join(path, e)) and e not in skip and not e.startswith(".")]
        files = [e for e in entries if os.path.isfile(os.path.join(path, e)) and not e.startswith(".")]

        for f in files[:20]:
            lines.append(f"{prefix}{f}")
        if len(files) > 20:
            lines.append(f"{prefix}... and {len(files) - 20} more files")

        for d in dirs[:15]:
            lines.append(f"{prefix}{d}/")
            walk(os.path.join(path, d), prefix + "  ", depth + 1)
        if len(dirs) > 15:
            lines.append(f"{prefix}... and {len(dirs) - 15} more directories")

    walk(project_path, "", 0)
    return "\n".join(lines)


def _find_entry_points(project_path: str, stack: StackInfo) -> list[dict]:
    """Find the main entry points based on framework conventions."""
    entries: list[dict] = []
    patterns: dict[str | None, list[tuple[str, str]]] = {
        "nextjs": [
            ("app/layout.tsx", "Root layout"), ("app/layout.js", "Root layout"),
            ("app/page.tsx", "Home page"), ("app/page.js", "Home page"),
            ("pages/index.tsx", "Home page (pages router)"),
            ("pages/_app.tsx", "App wrapper"),
            ("next.config.js", "Next.js config"), ("next.config.mjs", "Next.js config"),
            ("next.config.ts", "Next.js config"),
        ],
        "django": [
            ("manage.py", "Django management"), ("config/urls.py", "URL routing"),
            ("config/settings.py", "Settings"),
        ],
        "fastapi": [
            ("main.py", "FastAPI entry"), ("app/main.py", "FastAPI entry"),
            ("app/__init__.py", "App init"),
        ],
        "flask": [
            ("app.py", "Flask entry"), ("app/__init__.py", "Flask app factory"),
        ],
        "laravel": [
            ("routes/web.php", "Web routes"), ("routes/api.php", "API routes"),
            ("app/Providers/AppServiceProvider.php", "Service provider"),
        ],
        "rails": [
            ("config/routes.rb", "Rails routes"),
            ("app/controllers/application_controller.rb", "Base controller"),
        ],
        "express": [
            ("index.js", "Express entry"), ("src/index.js", "Express entry"),
            ("app.js", "Express app"), ("src/app.js", "Express app"),
            ("server.js", "Server entry"), ("src/server.ts", "Server entry"),
        ],
        "spring": [
            ("src/main/java/Application.java", "Spring entry"),
        ],
        None: [
            ("main.py", "Python entry"), ("index.js", "JS entry"),
            ("index.ts", "TS entry"), ("src/index.ts", "TS entry"),
            ("src/main.rs", "Rust entry"), ("main.go", "Go entry"),
            ("cmd/main.go", "Go entry"),
        ],
    }

    fw_patterns = patterns.get(stack.framework, []) + patterns.get(None, [])
    for rel_path, desc in fw_patterns:
        full = os.path.join(project_path, rel_path)
        if os.path.isfile(full):
            entries.append({"path": rel_path, "description": desc})

    return entries[:10]


def _find_models(project_path: str, stack: StackInfo) -> list[dict]:
    """Find data models / entities in the project."""
    models: list[dict] = []

    model_dirs = {
        "django": ["*/models.py", "*/models/"],
        "laravel": ["app/Models/"],
        "rails": ["app/models/"],
        "fastapi": ["app/models.py", "models.py", "app/models/"],
        "flask": ["app/models.py", "models.py"],
        "nextjs": ["prisma/schema.prisma"],
        "spring": ["src/main/java/**/model/", "src/main/java/**/entity/"],
    }

    search_patterns = model_dirs.get(stack.framework, [])

    if stack.orm == "prisma":
        prisma_schema = os.path.join(project_path, "prisma", "schema.prisma")
        if os.path.isfile(prisma_schema):
            content = _read_file(prisma_schema)
            for m in re.finditer(r"model\s+(\w+)\s*\{([^}]+)\}", content):
                name = m.group(1)
                body = m.group(2)
                fields = re.findall(r"^\s+(\w+)\s+", body, re.MULTILINE)
                models.append({"name": name, "path": "prisma/schema.prisma", "fields": fields})
            return models

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in {
            "node_modules", ".git", "__pycache__", ".next", "venv", ".venv",
            "vendor", "dist", "build", "target",
        }]
        rel_root = os.path.relpath(root, project_path)

        # Check if this directory is a known model location
        is_model_dir = any(k in rel_root.lower() for k in ("model", "entity", "schema"))

        for f in files:
            if not _is_source_file(f, stack):
                continue
            rel = os.path.join(rel_root, f) if rel_root != "." else f
            full = os.path.join(root, f)

            if is_model_dir or "model" in f.lower() or "entity" in f.lower() or "schema" in f.lower():
                content = _read_file(full, 4000)
                extracted = _extract_model_names(content, stack)
                for name, fields in extracted:
                    models.append({"name": name, "path": rel, "fields": fields})

        if len(models) > 20:
            break

    return models[:20]


def _extract_model_names(content: str, stack: StackInfo) -> list[tuple[str, list[str]]]:
    """Extract class/model names and their fields from source code."""
    results: list[tuple[str, list[str]]] = []

    if stack.language == "python":
        for m in re.finditer(r"class\s+(\w+)\(.*(?:Model|Base|db\.Model).*\):", content):
            name = m.group(1)
            fields = re.findall(r"(\w+)\s*=\s*(?:models\.|Column|db\.Column)", content[m.end():m.end()+1000])
            results.append((name, fields[:15]))

    elif stack.language in ("typescript", "javascript"):
        for m in re.finditer(r"(?:interface|type|class)\s+(\w+)(?:\s+extends|\s*\{)", content):
            name = m.group(1)
            block = content[m.end():m.end()+500]
            fields = re.findall(r"(\w+)\s*[?:]", block)
            results.append((name, fields[:15]))

    elif stack.language == "php":
        for m in re.finditer(r"class\s+(\w+)\s+extends\s+Model", content):
            name = m.group(1)
            fillable = re.findall(r"'(\w+)'", content[m.end():m.end()+500])
            results.append((name, fillable[:15]))

    elif stack.language == "ruby":
        for m in re.finditer(r"class\s+(\w+)\s*<\s*(?:ApplicationRecord|ActiveRecord::Base|ActiveRecord)", content):
            results.append((m.group(1), []))

    elif stack.language == "java" or stack.language == "kotlin":
        for m in re.finditer(r"@Entity.*?class\s+(\w+)", content, re.DOTALL):
            results.append((m.group(1), []))

    return results


def _find_routes(project_path: str, stack: StackInfo) -> list[dict]:
    """Find API routes / endpoints."""
    routes: list[dict] = []

    if stack.framework == "nextjs":
        app_dir = os.path.join(project_path, "app")
        if os.path.isdir(app_dir):
            for root, dirs, files in os.walk(app_dir):
                dirs[:] = [d for d in dirs if d not in {"node_modules", ".next"}]
                for f in files:
                    if f.startswith("route."):
                        rel = os.path.relpath(root, app_dir)
                        api_path = "/" + rel.replace("\\", "/")
                        routes.append({"path": api_path, "handler": os.path.join(root, f), "method": "API"})
                    elif f.startswith("page."):
                        rel = os.path.relpath(root, app_dir)
                        page_path = "/" + rel.replace("\\", "/")
                        if page_path == "/.":
                            page_path = "/"
                        routes.append({"path": page_path, "handler": f, "method": "PAGE"})

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in {
            "node_modules", ".git", "__pycache__", ".next", "venv", ".venv",
            "vendor", "dist", "build", "target",
        }]

        for f in files:
            if not _is_source_file(f, stack):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, project_path)
            # Check filenames AND also scan all source files for route patterns
            is_route_file = any(
                k in f.lower()
                for k in ("route", "controller", "urls", "endpoint", "api", "server", "app", "index")
            )
            if is_route_file:
                content = _read_file(full, 4000)
                extracted = _extract_routes(content, stack)
                for method, path in extracted:
                    routes.append({"method": method, "path": path, "handler": rel})

        if len(routes) > 40:
            break

    return routes[:40]


def _extract_routes(content: str, stack: StackInfo) -> list[tuple[str, str]]:
    """Extract HTTP routes from source code."""
    routes: list[tuple[str, str]] = []

    if stack.language == "python":
        for m in re.finditer(r"@(?:app|router)\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]", content, re.I):
            routes.append((m.group(1).upper(), m.group(2)))
        for m in re.finditer(r"path\(['\"]([^'\"]+)['\"]", content):
            routes.append(("ANY", m.group(1)))

    elif stack.language in ("typescript", "javascript"):
        for m in re.finditer(r"(?:app|router)\.(get|post|put|patch|delete)\(['\"`]([^'\"`]+)['\"`]", content, re.I):
            routes.append((m.group(1).upper(), m.group(2)))

    elif stack.language == "php":
        for m in re.finditer(r"Route::(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]", content, re.I):
            routes.append((m.group(1).upper(), m.group(2)))

    elif stack.language == "ruby":
        for m in re.finditer(r"(get|post|put|patch|delete)\s+['\"]([^'\"]+)['\"]", content, re.I):
            routes.append((m.group(1).upper(), m.group(2)))
        for m in re.finditer(r"resources?\s+:(\w+)", content):
            routes.append(("CRUD", f"/{m.group(1)}"))

    return routes


def _find_config(project_path: str, stack: StackInfo) -> list[dict]:
    """Find configuration files."""
    configs: list[dict] = []
    config_names = [
        (".env", "Environment variables"),
        (".env.example", "Environment template"),
        ("docker-compose.yml", "Docker Compose"),
        ("docker-compose.yaml", "Docker Compose"),
        ("Dockerfile", "Docker build"),
        ("tailwind.config.js", "Tailwind CSS"), ("tailwind.config.ts", "Tailwind CSS"),
        ("tsconfig.json", "TypeScript config"),
        ("eslint.config.js", "ESLint"), (".eslintrc.json", "ESLint"),
        ("prettier.config.js", "Prettier"), (".prettierrc", "Prettier"),
        ("drizzle.config.ts", "Drizzle ORM"),
        ("prisma/schema.prisma", "Prisma schema"),
        ("alembic.ini", "Alembic migrations"),
        ("vercel.json", "Vercel deployment"),
        ("netlify.toml", "Netlify deployment"),
        ("fly.toml", "Fly.io deployment"),
        ("railway.json", "Railway deployment"),
    ]
    for name, desc in config_names:
        if os.path.exists(os.path.join(project_path, name)):
            configs.append({"path": name, "description": desc})

    return configs


def _read_key_files(project_path: str, stack: StackInfo) -> list[dict]:
    """Read the most important source files for understanding the app."""
    key_files: list[dict] = []
    total_chars = 0

    priority_patterns = {
        "nextjs": [
            "app/layout.tsx", "app/page.tsx", "app/api/*/route.ts",
            "lib/db.ts", "lib/auth.ts", "prisma/schema.prisma",
        ],
        "django": [
            "*/models.py", "*/views.py", "*/urls.py", "config/settings.py",
        ],
        "fastapi": [
            "app/main.py", "main.py", "app/routes.py", "app/models.py",
        ],
        "laravel": [
            "routes/api.php", "routes/web.php", "app/Models/*.php",
        ],
        "rails": [
            "config/routes.rb", "app/models/*.rb",
            "app/controllers/application_controller.rb",
        ],
        "express": [
            "src/index.ts", "src/app.ts", "src/routes/*.ts",
        ],
    }

    explicit = priority_patterns.get(stack.framework, [])
    for pattern in explicit:
        if "*" in pattern:
            _glob_read(project_path, pattern, key_files, total_chars)
        else:
            full = os.path.join(project_path, pattern)
            if os.path.isfile(full):
                content = _read_file(full)
                if content:
                    key_files.append({"path": pattern, "content": content})
                    total_chars += len(content)
        if total_chars > MAX_TOTAL_CHARS or len(key_files) >= MAX_FILES_TO_READ:
            break

    return key_files


def _glob_read(project_path: str, pattern: str, key_files: list[dict], total_chars: int):
    """Simple glob-like read for patterns with one *."""
    parts = pattern.split("*")
    if len(parts) != 2:
        return

    prefix = parts[0]
    suffix = parts[1]
    search_dir = os.path.join(project_path, prefix)

    if not os.path.isdir(search_dir):
        search_dir = os.path.dirname(search_dir)
        if not os.path.isdir(search_dir):
            return

    try:
        for name in sorted(os.listdir(search_dir))[:10]:
            if name.endswith(suffix) or (not suffix):
                full = os.path.join(search_dir, name)
                if os.path.isfile(full):
                    content = _read_file(full)
                    if content:
                        rel = os.path.relpath(full, project_path)
                        key_files.append({"path": rel, "content": content})
                        total_chars += len(content)
                        if total_chars > MAX_TOTAL_CHARS:
                            return
    except OSError:
        pass


def _is_source_file(filename: str, stack: StackInfo) -> bool:
    exts = {
        "python": {".py"},
        "typescript": {".ts", ".tsx"},
        "javascript": {".js", ".jsx", ".mjs"},
        "php": {".php"},
        "ruby": {".rb"},
        "go": {".go"},
        "rust": {".rs"},
        "java": {".java"},
        "kotlin": {".kt", ".kts"},
        "csharp": {".cs"},
        "dart": {".dart"},
        "elixir": {".ex", ".exs"},
        "swift": {".swift"},
    }
    valid = exts.get(stack.language, set())
    _, ext = os.path.splitext(filename)
    return ext in valid
