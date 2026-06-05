import asyncio

from infra.telemetry import get_logger

from tools.base import Permission, Tool

logger = get_logger("tools.bash")

MAX_OUTPUT = 10240
MAX_TIMEOUT = 120.0


class BashTool(Tool):
    name = "bash"
    permission = Permission.SHELL

    def __init__(self, timeout: float = 30.0):
        self._timeout = timeout

    async def _run(self, *, command: str, timeout: float | None = None) -> str:
        t = min(timeout if timeout is not None else self._timeout, MAX_TIMEOUT)
        logger.info("executing: %s (timeout=%.1fs)", command[:200], t)
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=t)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.warning("command timed out after %.1fs: %s", t, command[:200])
            return f"error: command timed out after {t}s"

        out = stdout.decode(errors="replace")[:MAX_OUTPUT]
        err = stderr.decode(errors="replace")[:MAX_OUTPUT]
        logger.info("command exit_code=%d: %s", proc.returncode, command[:200])
        return f"stdout:\n{out}\nstderr:\n{err}\nexit_code: {proc.returncode}"
