"""Detects the tech stack of a project by reading its root directory.

Used by the 9-stage code pipeline at the PLAN stage so downstream agents know
which test command, dev server, scaffold commands, and ORM apply.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field


@dataclass
class StackInfo:
    language: str
    framework: str | None = None
    package_manager: str | None = None
    test_framework: str | None = None
    test_command: str = ""
    dev_server_command: str | None = None
    scaffold_commands: dict[str, str] = field(default_factory=dict)
    database: str | None = None
    orm: str | None = None
    has_ci: bool = False
    ci_platform: str | None = None
    has_docker: bool = False
    detected_files: list[str] = field(default_factory=list)


def _read_text(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def _read_json(path: str) -> dict | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _glob_suffix(entries: list[str], suffix: str) -> str | None:
    for name in entries:
        if name.endswith(suffix):
            return name
    return None


def _has_config(entries: list[str], stem: str) -> bool:
    for name in entries:
        if name == stem or name.startswith(stem + "."):
            return True
    return False


def detect_stack(project_path: str) -> StackInfo:
    """Detect the tech stack of a project by reading its root directory.

    Fills in what it can and leaves the rest as None. Never raises on a
    project it cannot fully classify.
    """
    info = StackInfo(language="unknown")

    def path(*parts: str) -> str:
        return os.path.join(project_path, *parts)

    def found(name: str) -> bool:
        if os.path.exists(path(name)):
            info.detected_files.append(name)
            return True
        return False

    try:
        entries = os.listdir(project_path)
    except OSError:
        entries = []

    _detect_language_and_framework(project_path, path, found, entries, info)
    _detect_database(project_path, path, found, entries, info)
    _detect_ci(found, info)
    _detect_docker(path, found, entries, info)
    _apply_stack_defaults(info)

    return info


def _detect_language_and_framework(project_path, path, found, entries, info: StackInfo) -> None:
    # JavaScript / TypeScript
    if found("package.json"):
        pkg = _read_json(path("package.json")) or {}
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        info.language = "typescript" if found("tsconfig.json") else "javascript"
        info.package_manager = _detect_js_package_manager(found)

        if "next" in deps or _has_config(entries, "next.config"):
            info.framework = "nextjs"
        elif "nuxt" in deps or _has_config(entries, "nuxt.config"):
            info.framework = "nuxt"
        elif "@angular/core" in deps or found("angular.json"):
            info.framework = "angular"
        elif "@sveltejs/kit" in deps or _has_config(entries, "svelte.config"):
            info.framework = "svelte"
        elif "astro" in deps or _has_config(entries, "astro.config"):
            info.framework = "astro"
        elif "vue" in deps:
            info.framework = "vue"
        elif "react" in deps:
            info.framework = "react"
        elif "express" in deps:
            info.framework = "express"

        info.test_framework = _detect_js_test_framework(deps)
        return

    # Python
    if found("pyproject.toml") or found("requirements.txt"):
        info.language = "python"
        info.package_manager = "pip"
        text = (_read_text(path("pyproject.toml")) or "") + "\n" + (
            _read_text(path("requirements.txt")) or ""
        )
        lowered = text.lower()
        if found("manage.py") or "django" in lowered:
            info.framework = "django"
        elif "fastapi" in lowered:
            info.framework = "fastapi"
        elif "flask" in lowered:
            info.framework = "flask"
        if "pytest" in lowered:
            info.test_framework = "pytest"
        return

    # PHP
    if found("composer.json"):
        info.language = "php"
        info.package_manager = "composer"
        composer = _read_json(path("composer.json")) or {}
        require = {**composer.get("require", {}), **composer.get("require-dev", {})}
        if found("artisan") or "laravel/framework" in require:
            info.framework = "laravel"
        if "pestphp/pest" in require:
            info.test_framework = "pest"
        elif "phpunit/phpunit" in require:
            info.test_framework = "phpunit"
        return

    # Ruby
    if found("Gemfile"):
        info.language = "ruby"
        info.package_manager = "bundler"
        gemfile = (_read_text(path("Gemfile")) or "").lower()
        if "rails" in gemfile or found("config/application.rb"):
            info.framework = "rails"
        if "rspec" in gemfile:
            info.test_framework = "rspec"
        else:
            info.test_framework = "minitest"
        return

    # Go
    if found("go.mod"):
        info.language = "go"
        info.package_manager = "go"
        info.test_framework = "go_test"
        return

    # Rust
    if found("Cargo.toml"):
        info.language = "rust"
        info.package_manager = "cargo"
        info.test_framework = "cargo_test"
        return

    # Java / Maven
    if found("pom.xml"):
        info.language = "java"
        info.package_manager = "maven"
        info.test_framework = "junit"
        pom = (_read_text(path("pom.xml")) or "").lower()
        if "springframework" in pom or "spring-boot" in pom:
            info.framework = "spring"
        return

    # Java / Kotlin via Gradle
    gradle = _has_config(entries, "build.gradle")
    if gradle:
        if any(name.startswith("build.gradle.kts") for name in entries):
            info.language = "kotlin"
            found("build.gradle.kts")
        else:
            info.language = "java"
            found("build.gradle")
        info.package_manager = "gradle"
        info.test_framework = "junit"
        gradle_text = (
            (_read_text(path("build.gradle")) or "")
            + (_read_text(path("build.gradle.kts")) or "")
        ).lower()
        if "spring" in gradle_text:
            info.framework = "spring"
        return

    # .NET
    csproj = _glob_suffix(entries, ".csproj") or _glob_suffix(entries, ".sln")
    if csproj:
        info.language = "csharp"
        info.package_manager = "dotnet"
        info.test_framework = "xunit"
        found(csproj)
        return

    # Flutter / Dart
    if found("pubspec.yaml"):
        info.package_manager = "pub"
        pubspec = (_read_text(path("pubspec.yaml")) or "").lower()
        if "flutter" in pubspec:
            info.language = "dart"
            info.framework = "flutter"
            info.test_framework = "flutter_test"
        else:
            info.language = "dart"
        return

    # Elixir / Phoenix
    if found("mix.exs"):
        info.language = "elixir"
        info.package_manager = "mix"
        mix = (_read_text(path("mix.exs")) or "").lower()
        if "phoenix" in mix:
            info.framework = "phoenix"
        return

    # Swift
    if found("Package.swift"):
        info.language = "swift"
        info.package_manager = "spm"
        return


def _detect_js_package_manager(found) -> str:
    if found("pnpm-lock.yaml"):
        return "pnpm"
    if found("yarn.lock"):
        return "yarn"
    found("package-lock.json")
    return "npm"


def _detect_js_test_framework(deps: dict) -> str | None:
    if "vitest" in deps:
        return "vitest"
    if "jest" in deps:
        return "jest"
    return None


def _detect_database(project_path, path, found, entries, info: StackInfo) -> None:
    env_text = _read_text(path(".env"))
    if env_text:
        info.detected_files.append(".env")
        info.database = _database_from_env(env_text)

    if os.path.isdir(path("prisma")):
        info.detected_files.append("prisma/")
        info.orm = "prisma"

    if found("schema.rb") or os.path.isfile(path("db", "schema.rb")):
        info.orm = "activerecord"


def _database_from_env(env_text: str) -> str | None:
    db_url_match = re.search(r"^\s*DATABASE_URL\s*=\s*(.+)$", env_text, re.MULTILINE)
    if db_url_match:
        url = db_url_match.group(1).strip().strip('"').strip("'").lower()
        for scheme, name in (
            ("postgres", "postgres"),
            ("postgresql", "postgres"),
            ("mysql", "mysql"),
            ("sqlite", "sqlite"),
            ("mongodb", "mongo"),
            ("redis", "redis"),
        ):
            if url.startswith(scheme):
                return name

    conn_match = re.search(r"^\s*DB_CONNECTION\s*=\s*(.+)$", env_text, re.MULTILINE)
    if conn_match:
        conn = conn_match.group(1).strip().strip('"').strip("'").lower()
        mapping = {
            "pgsql": "postgres",
            "postgres": "postgres",
            "mysql": "mysql",
            "mariadb": "mysql",
            "sqlite": "sqlite",
            "mongodb": "mongo",
        }
        if conn in mapping:
            return mapping[conn]

    if re.search(r"^\s*MONGODB_URI\s*=", env_text, re.MULTILINE):
        return "mongo"

    return None


def _detect_ci(found, info: StackInfo) -> None:
    if found(os.path.join(".github", "workflows")):
        info.has_ci = True
        info.ci_platform = "github_actions"
    elif found(".gitlab-ci.yml"):
        info.has_ci = True
        info.ci_platform = "gitlab_ci"
    elif found(".circleci"):
        info.has_ci = True
        info.ci_platform = "circleci"


def _detect_docker(path, found, entries, info: StackInfo) -> None:
    if found("Dockerfile") or _has_config(entries, "docker-compose"):
        info.has_docker = True
        if "Dockerfile" not in info.detected_files:
            compose = _has_config(entries, "docker-compose")
            if compose:
                for name in entries:
                    if name.startswith("docker-compose"):
                        info.detected_files.append(name)
                        break


_DEFAULTS: dict[str, dict] = {
    "laravel": {
        "test_command": "php artisan test",
        "dev_server_command": "php artisan serve",
        "orm": "eloquent",
        "scaffold_commands": {
            "model": "php artisan make:model",
            "controller": "php artisan make:controller",
            "migration": "php artisan make:migration",
            "test": "php artisan make:test",
        },
    },
    "django": {
        "test_command": "pytest -v",
        "dev_server_command": "python manage.py runserver",
        "orm": "django_orm",
        "scaffold_commands": {
            "app": "python manage.py startapp",
            "migration": "python manage.py makemigrations",
        },
    },
    "fastapi": {
        "test_command": "pytest -v",
        "dev_server_command": "uvicorn main:app --reload",
        "orm": "sqlalchemy",
        "scaffold_commands": {},
    },
    "flask": {
        "test_command": "pytest -v",
        "dev_server_command": "flask run",
        "orm": "sqlalchemy",
        "scaffold_commands": {},
    },
    "nextjs": {
        "test_command": "npm test",
        "dev_server_command": "npm run dev",
        "orm": "prisma",
        "scaffold_commands": {},
    },
    "nuxt": {
        "test_command": "npm test",
        "dev_server_command": "npm run dev",
        "orm": None,
        "scaffold_commands": {},
    },
    "angular": {
        "test_command": "ng test",
        "dev_server_command": "ng serve",
        "orm": None,
        "scaffold_commands": {
            "component": "ng generate component",
            "service": "ng generate service",
        },
    },
    "svelte": {
        "test_command": "npm test",
        "dev_server_command": "npm run dev",
        "orm": None,
        "scaffold_commands": {},
    },
    "astro": {
        "test_command": "npm test",
        "dev_server_command": "npm run dev",
        "orm": None,
        "scaffold_commands": {},
    },
    "express": {
        "test_command": "npm test",
        "dev_server_command": "npm run dev",
        "orm": "sequelize",
        "scaffold_commands": {},
    },
    "rails": {
        "test_command": "bin/rails test",
        "dev_server_command": "bin/rails server",
        "orm": "activerecord",
        "scaffold_commands": {
            "model": "rails generate model",
            "controller": "rails generate controller",
            "scaffold": "rails generate scaffold",
            "migration": "rails generate migration",
        },
    },
    "spring": {
        "test_command": "./mvnw test",
        "dev_server_command": "./mvnw spring-boot:run",
        "orm": "jpa",
        "scaffold_commands": {},
    },
    "phoenix": {
        "test_command": "mix test",
        "dev_server_command": "mix phx.server",
        "orm": "ecto",
        "scaffold_commands": {
            "context": "mix phx.gen.context",
            "schema": "mix phx.gen.schema",
            "html": "mix phx.gen.html",
        },
    },
    "flutter": {
        "test_command": "flutter test",
        "dev_server_command": "flutter run",
        "orm": None,
        "scaffold_commands": {},
    },
}

_LANGUAGE_DEFAULTS: dict[str, dict] = {
    "python": {"test_command": "pytest -v", "dev_server_command": None},
    "javascript": {"test_command": "npm test", "dev_server_command": "npm run dev"},
    "typescript": {"test_command": "npm test", "dev_server_command": "npm run dev"},
    "php": {"test_command": "vendor/bin/phpunit", "dev_server_command": "php -S localhost:8000"},
    "ruby": {"test_command": "bundle exec rspec", "dev_server_command": None},
    "go": {"test_command": "go test ./...", "dev_server_command": "go run ."},
    "rust": {"test_command": "cargo test", "dev_server_command": "cargo run"},
    "java": {"test_command": "mvn test", "dev_server_command": None},
    "kotlin": {"test_command": "./gradlew test", "dev_server_command": None},
    "csharp": {"test_command": "dotnet test", "dev_server_command": "dotnet run"},
    "dart": {"test_command": "dart test", "dev_server_command": None},
    "elixir": {"test_command": "mix test", "dev_server_command": None},
    "swift": {"test_command": "swift test", "dev_server_command": "swift run"},
}


def _apply_stack_defaults(info: StackInfo) -> None:
    if info.framework and info.framework in _DEFAULTS:
        defaults = _DEFAULTS[info.framework]
        info.test_command = defaults["test_command"]
        info.dev_server_command = defaults["dev_server_command"]
        if info.orm is None and defaults.get("orm"):
            info.orm = defaults["orm"]
        if not info.scaffold_commands:
            info.scaffold_commands = dict(defaults["scaffold_commands"])
        return

    lang_defaults = _LANGUAGE_DEFAULTS.get(info.language)
    if lang_defaults:
        if not info.test_command:
            info.test_command = lang_defaults["test_command"]
        if info.dev_server_command is None:
            info.dev_server_command = lang_defaults["dev_server_command"]


_ORM_LABELS = {
    "eloquent": "Eloquent",
    "django_orm": "Django ORM",
    "prisma": "Prisma",
    "activerecord": "ActiveRecord",
    "sqlalchemy": "SQLAlchemy",
    "sequelize": "Sequelize",
    "gorm": "GORM",
    "jpa": "JPA",
    "ecto": "Ecto",
}

_LANGUAGE_LABELS = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "php": "PHP",
    "ruby": "Ruby",
    "go": "Go",
    "rust": "Rust",
    "java": "Java",
    "kotlin": "Kotlin",
    "csharp": "C#",
    "dart": "Dart",
    "elixir": "Elixir",
    "swift": "Swift",
    "unknown": "Unknown",
}

_FRAMEWORK_LABELS = {
    "laravel": "Laravel",
    "django": "Django",
    "nextjs": "Next.js",
    "nuxt": "Nuxt",
    "rails": "Rails",
    "spring": "Spring",
    "express": "Express",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "angular": "Angular",
    "svelte": "SvelteKit",
    "astro": "Astro",
    "flutter": "Flutter",
    "phoenix": "Phoenix",
    "vue": "Vue",
    "react": "React",
}

_CI_LABELS = {
    "github_actions": "GitHub Actions",
    "gitlab_ci": "GitLab CI",
    "circleci": "CircleCI",
}


def format_stack_summary(info: StackInfo) -> str:
    """Format stack info as a human-readable summary for prompts."""
    lines: list[str] = []

    language = _LANGUAGE_LABELS.get(info.language, info.language.title())
    if info.framework:
        framework = _FRAMEWORK_LABELS.get(info.framework, info.framework.title())
        lines.append(f"Stack: {language} / {framework}")
    else:
        lines.append(f"Stack: {language}")

    if info.package_manager:
        lines.append(f"Package Manager: {info.package_manager}")

    if info.database or info.orm:
        orm_label = _ORM_LABELS.get(info.orm, info.orm) if info.orm else None
        if info.database and orm_label:
            lines.append(f"Database: {info.database} ({orm_label})")
        elif info.database:
            lines.append(f"Database: {info.database}")
        else:
            lines.append(f"ORM: {orm_label}")

    if info.test_command:
        lines.append(f"Test: {info.test_command}")

    if info.dev_server_command:
        lines.append(f"Dev Server: {info.dev_server_command}")

    if info.has_ci and info.ci_platform:
        lines.append(f"CI: {_CI_LABELS.get(info.ci_platform, info.ci_platform)}")

    if info.has_docker:
        lines.append("Docker: yes")

    return "\n".join(lines)
