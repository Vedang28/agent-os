import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.host_detector import HostTool
from agents.llm import call_llm, reset_host


@pytest.fixture(autouse=True)
def _reset():
    reset_host()
    yield
    reset_host()


class TestCallLlmHostRouting:
    def test_uses_host_tool_when_available(self):
        host = HostTool(name="claude_code", cli="/usr/bin/claude", available=True)

        async def mock_call_host(h, system, user):
            return "host tool response"

        with patch("agents.llm._get_host", return_value=host), \
             patch("agents.llm._call_host_tool", side_effect=mock_call_host):
            result = asyncio.get_event_loop().run_until_complete(
                call_llm(system="test system", user="test user")
            )
            assert result == "host tool response"

    def test_falls_back_to_api_when_host_fails(self):
        host = HostTool(name="claude_code", cli="/usr/bin/claude", available=True)

        async def failing_host(h, system, user):
            return None

        async def mock_anthropic(config, system, user, max_tokens, temp):
            return "api response"

        with patch("agents.llm._get_host", return_value=host), \
             patch("agents.llm._call_host_tool", side_effect=failing_host), \
             patch("agents.llm._call_anthropic", side_effect=mock_anthropic):
            result = asyncio.get_event_loop().run_until_complete(
                call_llm(system="test", user="test")
            )
            assert result == "api response"

    def test_uses_api_directly_when_no_host(self):
        host = HostTool(name="none", cli=None, available=False)

        async def mock_anthropic(config, system, user, max_tokens, temp):
            return "direct api"

        with patch("agents.llm._get_host", return_value=host), \
             patch("agents.llm._call_anthropic", side_effect=mock_anthropic):
            result = asyncio.get_event_loop().run_until_complete(
                call_llm(system="test", user="test")
            )
            assert result == "direct api"

    def test_placeholder_when_nothing_available(self):
        host = HostTool(name="none", cli=None, available=False)

        with patch("agents.llm._get_host", return_value=host), \
             patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            result = asyncio.get_event_loop().run_until_complete(
                call_llm(system="architect", user="design a schema")
            )
            assert "LLM_PLACEHOLDER" in result
            assert "no AI coding tool" in result


class TestHostToolCalls:
    def test_claude_code_cli_args(self):
        """Verify Claude Code is called with -p and --output-format text."""
        async def mock_exec(*args, **kwargs):
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"response text", b""))
            mock_proc.returncode = 0
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec) as mock:
            from agents.llm import _call_claude_code
            result = asyncio.get_event_loop().run_until_complete(
                _call_claude_code("/usr/bin/claude", "test prompt")
            )
            assert result == "response text"
            call_args = mock.call_args[0]
            assert call_args[0] == "/usr/bin/claude"
            assert "-p" in call_args
            assert "--output-format" in call_args

    def test_codex_cli_args(self):
        async def mock_exec(*args, **kwargs):
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"codex output", b""))
            mock_proc.returncode = 0
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec) as mock:
            from agents.llm import _call_codex
            result = asyncio.get_event_loop().run_until_complete(
                _call_codex("/usr/bin/codex", "test prompt")
            )
            assert result == "codex output"
            call_args = mock.call_args[0]
            assert "-q" in call_args

    def test_host_tool_error_returns_none(self):
        async def mock_exec(*args, **kwargs):
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
            mock_proc.returncode = 1
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            from agents.llm import _call_claude_code
            result = asyncio.get_event_loop().run_until_complete(
                _call_claude_code("/usr/bin/claude", "test prompt")
            )
            assert result is None
