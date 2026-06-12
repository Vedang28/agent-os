import asyncio
import signal
import time
from dataclasses import dataclass, field

from agents.guardian import is_killed
from infra.telemetry import get_logger

logger = get_logger("infra.daemon")


@dataclass
class JobRecord:
    name: str
    graph: object
    trigger_request: str


class Daemon:
    def __init__(
        self,
        tick_interval: float = 900.0,
        max_tokens_per_tick: int = 100_000,
        max_wall_clock_per_tick: float = 300.0,
    ):
        self._tick_interval = tick_interval
        self._max_tokens_per_tick = max_tokens_per_tick
        self._max_wall_clock_per_tick = max_wall_clock_per_tick
        self._running = False
        self._jobs: dict[str, JobRecord] = {}
        self._tick_count = 0
        self._checkpoints: dict[str, dict] = {}
        self._last_tick_results: list[dict] = []

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def is_running(self) -> bool:
        return self._running

    def register_job(
        self, name: str, graph: object, trigger_request: str = ""
    ) -> None:
        self._jobs[name] = JobRecord(
            name=name, graph=graph, trigger_request=trigger_request
        )
        logger.info("registered job: %s", name)

    def list_jobs(self) -> list[str]:
        return list(self._jobs.keys())

    def save_checkpoint(self, job_name: str, state: dict) -> None:
        self._checkpoints[job_name] = dict(state)
        logger.info("saved checkpoint for job=%s", job_name)

    def load_checkpoint(self, job_name: str) -> dict | None:
        cp = self._checkpoints.get(job_name)
        if cp:
            logger.info("loaded checkpoint for job=%s", job_name)
        return cp

    async def tick(self) -> list[dict]:
        if is_killed():
            logger.warning("tick aborted: kill switch is active")
            return []

        self._tick_count += 1
        tick_start = time.monotonic()
        logger.info("tick %d starting, jobs=%d", self._tick_count, len(self._jobs))

        results = []
        for job_name, job in self._jobs.items():
            if is_killed():
                logger.warning("tick %d: kill switch activated mid-tick, stopping", self._tick_count)
                break

            elapsed = time.monotonic() - tick_start
            if elapsed >= self._max_wall_clock_per_tick:
                logger.warning(
                    "tick %d: wall-clock budget exhausted (%.1fs), skipping remaining jobs",
                    self._tick_count,
                    elapsed,
                )
                break

            try:
                result = await self._run_job(job)
                self.save_checkpoint(job_name, result)
                results.append(result)
            except Exception as e:
                logger.error("tick %d: job=%s failed: %s", self._tick_count, job_name, e)
                results.append({"error": str(e), "job": job_name})

        elapsed = time.monotonic() - tick_start
        logger.info(
            "tick %d complete in %.1fs, results=%d",
            self._tick_count,
            elapsed,
            len(results),
        )
        self._last_tick_results = results
        return results

    async def _run_job(self, job: JobRecord) -> dict:
        graph = job.graph
        input_state = {"request": job.trigger_request}

        checkpoint = self.load_checkpoint(job.name)
        if checkpoint and not checkpoint.get("approved", False):
            input_state.update(checkpoint)

        config = {"configurable": {"thread_id": f"daemon_{job.name}"}}

        if hasattr(graph, "invoke"):
            result = graph.invoke(input_state, config=config)
        else:
            raise TypeError(f"Job graph for {job.name} has no invoke method")

        return dict(result) if result else {}

    async def start(self) -> None:
        self._running = True
        logger.info("daemon starting, tick_interval=%.0fs", self._tick_interval)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        while self._running and not is_killed():
            await self.tick()
            if self._running and not is_killed():
                await asyncio.sleep(self._tick_interval)

        if is_killed():
            logger.warning("daemon stopped by kill switch")

    async def stop(self) -> None:
        logger.info("daemon stopping, saving state")
        self._running = False
        for job_name in self._jobs:
            cp = self._checkpoints.get(job_name)
            if cp:
                self.save_checkpoint(job_name, cp)
        logger.info("daemon stopped after %d ticks", self._tick_count)
