import os
from unittest.mock import patch

from agents.host_detector import HostTool, detect_host


class TestHostDetector:
    def test_claude_code_detected_via_env(self):
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}, clear=False), \
             patch("shutil.which", return_value="/usr/local/bin/claude"):
            host = detect_host()
            assert host.name == "claude_code"
            assert host.cli == "/usr/local/bin/claude"
            assert host.available is True

    def test_codex_detected_via_env(self):
        env = {"CODEX_HOME": "/home/user/.codex", "CLAUDE_CODE": "", "CLAUDE_SESSION_ID": "", "CLAUDE_PROJECT_DIR": ""}
        with patch.dict(os.environ, env, clear=False), \
             patch("shutil.which", side_effect=lambda cmd: "/usr/local/bin/codex" if cmd == "codex" else None):
            host = detect_host()
            assert host.name == "codex"
            assert host.available is True

    def test_no_tool_detected(self):
        env_clear = {
            "CLAUDE_CODE": "", "CLAUDE_SESSION_ID": "", "CLAUDE_PROJECT_DIR": "",
            "CODEX_HOME": "", "CODEX_SESSION": "",
            "CURSOR_SESSION": "", "CURSOR_WORKSPACE": "",
            "WINDSURF_SESSION": "",
            "KIMI_SESSION": "", "KIMI_API_KEY": "",
            "AGENT_OS_HOST": "",
        }
        with patch.dict(os.environ, env_clear, clear=False), \
             patch("shutil.which", return_value=None):
            host = detect_host()
            assert host.name == "none"
            assert host.available is False

    def test_explicit_override(self):
        with patch.dict(os.environ, {"AGENT_OS_HOST": "claude_code"}, clear=False), \
             patch("shutil.which", return_value="/usr/bin/claude"):
            host = detect_host()
            assert host.name == "claude_code"
            assert host.available is True

    def test_override_unknown_tool(self):
        with patch.dict(os.environ, {"AGENT_OS_HOST": "my_custom_tool"}, clear=False):
            host = detect_host()
            assert host.name == "my_custom_tool"
            assert host.available is True

    def test_claude_code_detected_via_cli_only(self):
        env_clear = {
            "CLAUDE_CODE": "", "CLAUDE_SESSION_ID": "", "CLAUDE_PROJECT_DIR": "",
            "AGENT_OS_HOST": "",
        }
        with patch.dict(os.environ, env_clear, clear=False), \
             patch("shutil.which", side_effect=lambda cmd: "/usr/bin/claude" if cmd == "claude" else None):
            host = detect_host()
            assert host.name == "claude_code"
            assert host.available is True

    def test_priority_order(self):
        """Claude Code takes priority over Codex if both are present."""
        with patch.dict(os.environ, {"CLAUDE_CODE": "1", "CODEX_HOME": "/codex"}, clear=False), \
             patch("shutil.which", return_value="/usr/bin/claude"):
            host = detect_host()
            assert host.name == "claude_code"

    def test_aider_detected(self):
        env_clear = {
            "CLAUDE_CODE": "", "CLAUDE_SESSION_ID": "", "CLAUDE_PROJECT_DIR": "",
            "CODEX_HOME": "", "CODEX_SESSION": "",
            "CURSOR_SESSION": "", "CURSOR_WORKSPACE": "",
            "WINDSURF_SESSION": "",
            "KIMI_SESSION": "", "KIMI_API_KEY": "",
            "AGENT_OS_HOST": "",
        }
        with patch.dict(os.environ, env_clear, clear=False), \
             patch("shutil.which", side_effect=lambda cmd: "/usr/bin/aider" if cmd == "aider" else None):
            host = detect_host()
            assert host.name == "aider"
            assert host.available is True
