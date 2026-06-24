"""Automated security audit — verifies security invariants across the codebase."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.guardian import (
    Guardian,
    KillSwitchError,
    _reset_approval_callback_for_testing,
    install_guardian,
    set_approval_callback,
)
from tools.base import Permission, Tool, get_permission_checker, set_permission_checker

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

EXCLUDE_DIRS = {
    "__pycache__", ".git", "node_modules", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".eggs", "dist", "build",
    "htmlcov", ".claude", ".codex",
}

EXCLUDE_TEST_STEMS = {"test_", "conftest"}


def _iter_source_files(*extensions: str, include_tests: bool = False) -> list[Path]:
    results: list[Path] = []
    for ext in extensions:
        for path in PROJECT_ROOT.rglob(f"*{ext}"):
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            if not include_tests and any(
                path.stem.startswith(pfx) for pfx in EXCLUDE_TEST_STEMS
            ):
                continue
            results.append(path)
    return results


def _discover_tool_classes() -> list[type[Tool]]:
    tool_classes: list[type[Tool]] = []

    import tools
    for _importer, modname, _ispkg in pkgutil.walk_packages(
        tools.__path__, prefix="tools."
    ):
        try:
            mod = importlib.import_module(modname)
        except ImportError:
            continue
        for _name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, Tool) and obj is not Tool and not inspect.isabstract(obj):
                tool_classes.append(obj)

    try:
        import integrations.tools as int_tools
        for _importer, modname, _ispkg in pkgutil.walk_packages(
            int_tools.__path__, prefix="integrations.tools."
        ):
            try:
                mod = importlib.import_module(modname)
            except ImportError:
                continue
            for _name, obj in inspect.getmembers(mod, inspect.isclass):
                if (
                    issubclass(obj, Tool)
                    and obj is not Tool
                    and not inspect.isabstract(obj)
                ):
                    tool_classes.append(obj)
    except ImportError:
        pass

    return tool_classes


# ---------------------------------------------------------------------------
# Fake tools for Guardian tests
# ---------------------------------------------------------------------------

class _FakeReadTool(Tool):
    name = "audit_read"
    permission = Permission.READ

    async def _run(self, **kwargs) -> str:
        return "ok"


class _FakeWriteTool(Tool):
    name = "audit_write"
    permission = Permission.WRITE

    async def _run(self, **kwargs) -> str:
        return "ok"


class _FakeShellTool(Tool):
    name = "audit_shell"
    permission = Permission.SHELL

    async def _run(self, **kwargs) -> str:
        return "ok"


class _FakeDestructiveTool(Tool):
    name = "audit_destructive"
    permission = Permission.DESTRUCTIVE

    async def _run(self, **kwargs) -> str:
        return "ok"


# ---------------------------------------------------------------------------
# TestToolPermissions
# ---------------------------------------------------------------------------

class TestToolPermissions:
    """Every Tool subclass must declare a Permission level."""

    _tool_classes = _discover_tool_classes()

    def test_at_least_some_tools_discovered(self):
        assert len(self._tool_classes) >= 3, (
            f"Only found {len(self._tool_classes)} tools — discovery may be broken"
        )

    @pytest.mark.parametrize(
        "tool_cls",
        _discover_tool_classes(),
        ids=lambda c: c.__name__,
    )
    def test_all_tools_declare_permission(self, tool_cls: type[Tool]):
        assert hasattr(tool_cls, "permission"), (
            f"{tool_cls.__name__} missing 'permission' attribute"
        )
        assert isinstance(tool_cls.permission, Permission), (
            f"{tool_cls.__name__}.permission is {type(tool_cls.permission)}, "
            f"expected Permission enum"
        )

    def test_at_least_one_tool_per_level(self):
        found: set[Permission] = set()
        for cls in self._tool_classes:
            if hasattr(cls, "permission") and isinstance(cls.permission, Permission):
                found.add(cls.permission)
        for level in Permission:
            assert level in found, f"No tool found with Permission.{level.name}"

    def test_bash_tool_is_shell(self):
        from tools.bash import BashTool
        assert BashTool.permission == Permission.SHELL

    def test_file_tool_is_write(self):
        from tools.file import FileTool
        assert FileTool.permission == Permission.WRITE

    def test_web_tool_is_read(self):
        from tools.web import WebTool
        assert WebTool.permission == Permission.READ


# ---------------------------------------------------------------------------
# TestGuardianInPath
# ---------------------------------------------------------------------------

class TestGuardianInPath:
    """Guardian enforcement works end-to-end on Tool.execute()."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        _reset_approval_callback_for_testing()
        set_approval_callback(lambda a, d: True)
        Guardian(timeout=1.0).reset_kill_switch()
        _reset_approval_callback_for_testing()
        set_permission_checker(None)
        yield
        _reset_approval_callback_for_testing()
        set_approval_callback(lambda a, d: True)
        Guardian(timeout=1.0).reset_kill_switch()
        _reset_approval_callback_for_testing()
        set_permission_checker(None)

    def test_guardian_installs_as_permission_checker(self):
        g = Guardian(timeout=1.0)
        install_guardian(g)
        assert get_permission_checker() is not None

    @pytest.mark.asyncio
    async def test_guardian_blocks_shell_without_approval(self):
        set_approval_callback(lambda a, d: False)
        install_guardian(Guardian(timeout=1.0))
        with pytest.raises(PermissionError):
            await _FakeShellTool().execute()

    @pytest.mark.asyncio
    async def test_guardian_blocks_destructive_without_approval(self):
        set_approval_callback(lambda a, d: False)
        install_guardian(Guardian(timeout=1.0))
        with pytest.raises(PermissionError):
            await _FakeDestructiveTool().execute()

    @pytest.mark.asyncio
    async def test_guardian_allows_read(self):
        install_guardian(Guardian(timeout=1.0))
        result = await _FakeReadTool().execute()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_guardian_allows_write(self):
        install_guardian(Guardian(timeout=1.0))
        result = await _FakeWriteTool().execute()
        assert result == "ok"

    def test_kill_switch_blocks_all(self):
        g = Guardian(timeout=1.0)
        install_guardian(g)
        g.kill()
        with pytest.raises(KillSwitchError):
            g.check_permission(_FakeReadTool())


# ---------------------------------------------------------------------------
# TestNoSecretsInCodebase
# ---------------------------------------------------------------------------

SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "Anthropic/OpenAI API key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub personal access token"),
    (re.compile(r"gho_[a-zA-Z0-9]{36}"), "GitHub OAuth token"),
    (re.compile(r"xoxb-[0-9]+-[a-zA-Z0-9]+"), "Slack bot token"),
    (re.compile(r"xoxp-[0-9]+-[a-zA-Z0-9]+"), "Slack user token"),
    (re.compile(r"password\s*=\s*[\"'][^\"']{4,}[\"']"), "Hardcoded password"),
    (re.compile(r"secret\s*=\s*[\"'][^\"']{4,}[\"']"), "Hardcoded secret"),
]


class TestNoSecretsInCodebase:
    def _scan_files(self, paths: list[Path]) -> list[str]:
        violations: list[str] = []
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue
            for pattern, label in SECRET_PATTERNS:
                for match in pattern.finditer(text):
                    violations.append(
                        f"{path.relative_to(PROJECT_ROOT)}:"
                        f" matched {label} ({match.group()[:30]}...)"
                    )
        return violations

    def test_no_secrets_in_python_files(self):
        files = _iter_source_files(".py", include_tests=False)
        violations = self._scan_files(files)
        assert not violations, (
            f"Secrets found in source:\n" + "\n".join(violations)
        )

    def test_no_secrets_in_config_files(self):
        files = _iter_source_files(".yaml", ".yml", ".toml", ".json", include_tests=False)
        violations = self._scan_files(files)
        assert not violations, (
            f"Secrets found in config:\n" + "\n".join(violations)
        )

    def test_gitignore_covers_env(self):
        gitignore = PROJECT_ROOT / ".gitignore"
        assert gitignore.exists(), ".gitignore missing"
        text = gitignore.read_text()
        assert ".env" in text, ".gitignore does not contain .env"

    def test_token_store_uses_encryption(self):
        from integrations.token_store import TokenStore
        src = inspect.getsource(TokenStore)
        assert "Fernet" in src, "TokenStore should use Fernet encryption"


# ---------------------------------------------------------------------------
# TestNoUnsafeImports
# ---------------------------------------------------------------------------

class TestNoUnsafeImports:
    """The agent/core layers must not use dangerous primitives directly."""

    _agent_dirs = [PROJECT_ROOT / "agents", PROJECT_ROOT / "core"]

    def _scan_for_pattern(
        self,
        pattern: re.Pattern[str],
        dirs: list[Path] | None = None,
        exclude_files: set[str] | None = None,
    ) -> list[str]:
        dirs = dirs or [PROJECT_ROOT]
        exclude_files = exclude_files or set()
        violations: list[str] = []
        for d in dirs:
            if not d.exists():
                continue
            for path in d.rglob("*.py"):
                if any(part in EXCLUDE_DIRS for part in path.parts):
                    continue
                if path.name in exclude_files:
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for lineno, line in enumerate(text.splitlines(), 1):
                    if pattern.search(line):
                        violations.append(
                            f"{path.relative_to(PROJECT_ROOT)}:{lineno}: {line.strip()}"
                        )
        return violations

    def test_no_subprocess_in_agents(self):
        pat = re.compile(r"(?:^|\s)(?:import subprocess|from subprocess)")
        violations = self._scan_for_pattern(pat, dirs=self._agent_dirs)
        assert not violations, (
            "subprocess used in agent layer:\n" + "\n".join(violations)
        )

    def test_no_os_system(self):
        pat = re.compile(r"os\.system\s*\(")
        violations = self._scan_for_pattern(pat, dirs=self._agent_dirs)
        assert not violations, (
            "os.system() used in agent/core layer:\n" + "\n".join(violations)
        )

    def test_no_eval_exec(self):
        pat = re.compile(r"(?<!\w)(?:eval|exec)\s*\(")
        all_dirs = [
            d for d in PROJECT_ROOT.iterdir()
            if d.is_dir()
            and d.name not in EXCLUDE_DIRS
            and d.name != "tests"
            and not d.name.startswith(".")
        ]
        violations = self._scan_for_pattern(
            pat,
            dirs=all_dirs,
            exclude_files={"test_full_audit.py"},
        )
        assert not violations, (
            "eval/exec found in source:\n" + "\n".join(violations)
        )

    def test_no_pickle(self):
        pat = re.compile(r"(?:import pickle|pickle\.load)")
        all_dirs = [
            d for d in PROJECT_ROOT.iterdir()
            if d.is_dir()
            and d.name not in EXCLUDE_DIRS
            and d.name != "tests"
            and not d.name.startswith(".")
        ]
        violations = self._scan_for_pattern(pat, dirs=all_dirs)
        assert not violations, (
            "pickle usage found in source:\n" + "\n".join(violations)
        )

    def test_no_yaml_unsafe_load(self):
        pat = re.compile(r"yaml\.load\s*\([^)]*\)\s*(?!.*Loader)")
        all_dirs = [
            d for d in PROJECT_ROOT.iterdir()
            if d.is_dir()
            and d.name not in EXCLUDE_DIRS
            and not d.name.startswith(".")
        ]
        violations = self._scan_for_pattern(pat, dirs=all_dirs)
        assert not violations, (
            "yaml.load without Loader= found:\n" + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# TestSSRFProtection
# ---------------------------------------------------------------------------

class TestSSRFProtection:
    """URL validation blocks internal/private networks."""

    def _make_web_tool(self):
        from tools.web import WebTool
        return WebTool(timeout=5.0)

    def _check_blocked(self, url: str):
        tool = self._make_web_tool()
        with pytest.raises(ValueError, match="(?i)block"):
            tool._check_url(url)

    def test_web_tool_blocks_localhost(self):
        self._check_blocked("http://127.0.0.1/admin")

    def test_web_tool_blocks_localhost_name(self):
        self._check_blocked("http://localhost/admin")

    def test_web_tool_blocks_metadata(self):
        self._check_blocked("http://169.254.169.254/latest/meta-data/")

    def test_web_tool_blocks_private_10(self):
        self._check_blocked("http://10.0.0.1/")

    def test_web_tool_blocks_private_192(self):
        self._check_blocked("http://192.168.1.1/")

    def test_web_tool_allows_public(self):
        tool = self._make_web_tool()
        tool._check_url("http://example.com")

    def test_web_tool_blocks_non_http_scheme(self):
        tool = self._make_web_tool()
        with pytest.raises(ValueError, match="(?i)scheme"):
            tool._check_url("file:///etc/passwd")

    def test_mcp_bridge_blocks_localhost(self):
        from integrations.mcp import MCPBridge
        bridge = MCPBridge()
        with pytest.raises(ValueError, match="(?i)block"):
            bridge._check_url("http://127.0.0.1:8080/tools")


# ---------------------------------------------------------------------------
# TestPathTraversal
# ---------------------------------------------------------------------------

class TestPathTraversal:
    """File operations block directory traversal attacks."""

    def test_file_tool_blocks_dot_dot(self, tmp_path: Path):
        from tools.file import FileTool
        ft = FileTool(allowed_root=tmp_path)
        with pytest.raises(PermissionError, match="(?i)traversal"):
            ft._validate_path("../../etc/passwd")

    def test_file_tool_blocks_escape(self, tmp_path: Path):
        from tools.file import FileTool
        ft = FileTool(allowed_root=tmp_path)
        target = "/etc/passwd"
        rel = Path(target).relative_to("/")
        with pytest.raises(PermissionError):
            ft._validate_path(f"../{rel}")

    def test_file_tool_allows_normal_path(self, tmp_path: Path):
        from tools.file import FileTool
        ft = FileTool(allowed_root=tmp_path)
        result = ft._validate_path("subdir/file.txt")
        assert result.is_relative_to(tmp_path)

    def test_obsidian_blocks_traversal(self, tmp_path: Path):
        from brain.obsidian import ObsidianVault
        vault = ObsidianVault(vault_path=tmp_path)
        with pytest.raises(PermissionError, match="(?i)traversal"):
            vault._title_to_path("../../etc/passwd")

    def test_obsidian_allows_normal_title(self, tmp_path: Path):
        from brain.obsidian import ObsidianVault
        vault = ObsidianVault(vault_path=tmp_path)
        result = vault._title_to_path("My Note Title")
        assert result.is_relative_to(tmp_path)

    def test_token_store_blocks_traversal(self, tmp_path: Path):
        from cryptography.fernet import Fernet
        from integrations.token_store import TokenStore
        key = Fernet.generate_key().decode()
        ts = TokenStore(store_dir=tmp_path, key=key)
        with pytest.raises(ValueError):
            ts._safe_path("../../../etc/passwd")


# ---------------------------------------------------------------------------
# TestSecurityGateContract
# ---------------------------------------------------------------------------

class TestSecurityGateContract:
    """SecurityGate ABC enforces the review interface."""

    def test_security_gate_is_abstract(self):
        from agents.security_gate import SecurityGate
        with pytest.raises(TypeError):
            SecurityGate()  # type: ignore[abstract]

    def test_security_gate_has_review_method(self):
        from agents.security_gate import SecurityGate
        assert hasattr(SecurityGate, "review")
        assert getattr(SecurityGate.review, "__isabstractmethod__", False)

    @pytest.mark.asyncio
    async def test_concrete_security_gate_works(self):
        from agents.security_gate import SecurityGate
        from core.state import AgentState

        class PassthroughGate(SecurityGate):
            async def review(self, state: AgentState) -> AgentState:
                return {**state, "approved": True}

        gate = PassthroughGate()
        result = await gate.review(AgentState(request="test", approved=False))
        assert result["approved"] is True
