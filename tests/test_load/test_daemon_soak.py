import random
import threading
import tracemalloc
from unittest.mock import MagicMock

import pytest

from agents.guardian import (
    Guardian,
    KillSwitchError,
    _reset_approval_callback_for_testing,
    is_killed,
    set_approval_callback,
)
from core.dispatcher import assign_lane
from infra.cost_tracker import CostRecord, CostTracker, reset_cost_tracker
from infra.daemon import Daemon


# ---------------------------------------------------------------------------
# SyntheticRequestGenerator
# ---------------------------------------------------------------------------

class SyntheticRequestGenerator:
    _INSTANT = [
        "hello", "hi", "hey", "ping", "thanks", "bye", "goodbye",
        "good morning", "good evening", "good night", "greetings",
        "what time is it", "what's the time",
    ]
    _FAST = [
        "summarize this document", "translate this text",
        "explain this concept", "what is machine learning",
        "describe the architecture", "list the dependencies",
        "check the status", "review this code",
        "format this data", "compare these options",
    ]
    _DEEP = [
        "build a REST API for user management with CRUD endpoints",
        "create a microservice for payment processing",
        "design a database schema for an e-commerce platform",
        "implement JWT authentication for the API",
        "develop a CI/CD pipeline for this project",
        "refactor the authentication module to use OAuth2",
        "architect a real-time notification system",
        "build a dashboard for monitoring system metrics",
        "generate a daily intelligence briefing on market trends",
        "research and analyze trends in AI agent frameworks",
    ]

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def generate(
        self, n: int, instant_pct: float = 0.7, fast_pct: float = 0.15
    ) -> list[str]:
        requests: list[str] = []
        for _ in range(n):
            r = self._rng.random()
            if r < instant_pct:
                requests.append(self._rng.choice(self._INSTANT))
            elif r < instant_pct + fast_pct:
                requests.append(self._rng.choice(self._FAST))
            else:
                requests.append(self._rng.choice(self._DEEP))
        return requests


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_guardian():
    """Reset guardian state between every test."""
    guardian = Guardian()
    guardian.reset_kill_switch()
    _reset_approval_callback_for_testing()
    yield
    guardian = Guardian()
    set_approval_callback(lambda a, d: True)
    guardian.reset_kill_switch()
    _reset_approval_callback_for_testing()


@pytest.fixture(autouse=True)
def _reset_cost(tmp_path):
    reset_cost_tracker()
    yield
    reset_cost_tracker()


@pytest.fixture
def mock_graph():
    graph = MagicMock()
    graph.invoke.return_value = {"result": "ok", "approved": True, "revisions": 0}
    return graph


# ---------------------------------------------------------------------------
# TestSyntheticRequestGenerator
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestSyntheticRequestGenerator:
    def test_generate_count(self):
        gen = SyntheticRequestGenerator(seed=42)
        reqs = gen.generate(100)
        assert len(reqs) == 100

    def test_deterministic(self):
        a = SyntheticRequestGenerator(seed=99).generate(50)
        b = SyntheticRequestGenerator(seed=99).generate(50)
        assert a == b

    def test_lane_distribution(self):
        gen = SyntheticRequestGenerator(seed=42)
        reqs = gen.generate(1000)
        lanes = [assign_lane({"request": r})["lane"] for r in reqs]
        instant_pct = lanes.count("instant") / len(lanes)
        assert 0.55 <= instant_pct <= 0.85, (
            f"instant lane fraction {instant_pct:.2%} outside tolerance"
        )


# ---------------------------------------------------------------------------
# TestDaemonSoak
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestDaemonSoak:

    @pytest.mark.asyncio
    async def test_soak_100_ticks(self, mock_graph):
        daemon = Daemon(max_wall_clock_per_tick=60.0)
        daemon.register_job("soak", mock_graph, trigger_request="ping")
        for _ in range(100):
            await daemon.tick()
        assert daemon.tick_count == 100
        assert mock_graph.invoke.call_count == 100

    @pytest.mark.asyncio
    async def test_memory_bounded(self, mock_graph):
        daemon = Daemon(max_wall_clock_per_tick=60.0)
        daemon.register_job("mem", mock_graph, trigger_request="ping")

        tracemalloc.start()
        snap_before = tracemalloc.take_snapshot()
        for _ in range(50):
            await daemon.tick()
        snap_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        stats = snap_after.compare_to(snap_before, "lineno")
        growth_bytes = sum(s.size_diff for s in stats if s.size_diff > 0)
        growth_mb = growth_bytes / (1024 * 1024)
        assert growth_mb < 50, f"memory grew {growth_mb:.1f} MB over 50 ticks"

    @pytest.mark.asyncio
    async def test_checkpoint_bounded(self):
        g1 = MagicMock()
        g1.invoke.return_value = {"result": "a", "approved": True}
        g2 = MagicMock()
        g2.invoke.return_value = {"result": "b", "approved": True}

        daemon = Daemon(max_wall_clock_per_tick=60.0)
        daemon.register_job("job_a", g1, trigger_request="ping")
        daemon.register_job("job_b", g2, trigger_request="ping")

        for _ in range(50):
            await daemon.tick()

        assert len(daemon._checkpoints) == 2, (
            f"expected 2 checkpoint keys, got {len(daemon._checkpoints)}"
        )

    @pytest.mark.asyncio
    async def test_no_concurrent_tick_overlap(self, mock_graph):
        lock = threading.Lock()
        overlap_detected = False

        original_invoke = mock_graph.invoke

        def guarded_invoke(*args, **kwargs):
            nonlocal overlap_detected
            acquired = lock.acquire(blocking=False)
            if not acquired:
                overlap_detected = True
                return original_invoke.return_value
            try:
                return original_invoke.return_value
            finally:
                lock.release()

        mock_graph.invoke.side_effect = guarded_invoke

        daemon = Daemon(max_wall_clock_per_tick=60.0)
        daemon.register_job("overlap", mock_graph, trigger_request="ping")

        for _ in range(20):
            await daemon.tick()

        assert not overlap_detected, "concurrent tick overlap detected"

    @pytest.mark.asyncio
    async def test_recovery_after_kill(self):
        guardian = Guardian()
        set_approval_callback(lambda a, d: True)

        call_count = 0

        def counting_invoke(*args, **kwargs):
            nonlocal call_count
            if is_killed():
                raise KillSwitchError("kill switch active")
            call_count += 1
            return {"result": "ok", "approved": True}

        graph = MagicMock()
        graph.invoke.side_effect = counting_invoke

        daemon = Daemon(max_wall_clock_per_tick=60.0)
        daemon.register_job("killtest", graph, trigger_request="ping")

        for _ in range(5):
            await daemon.tick()
        assert call_count == 5

        guardian.kill()
        assert is_killed()

        results = await daemon.tick()
        assert any("error" in r for r in results)

        guardian.reset_kill_switch()
        assert not is_killed()

        pre = call_count
        await daemon.tick()
        assert call_count == pre + 1

    @pytest.mark.asyncio
    async def test_cost_ceiling_enforcement(self, tmp_path):
        tracker = CostTracker(storage_path=tmp_path / "costs.json")
        guardian = Guardian()
        set_approval_callback(lambda a, d: True)

        for i in range(10):
            tracker.record(CostRecord(
                task_id=f"t{i}",
                department="engineering",
                model="claude",
                tokens_input=5000,
                tokens_output=5000,
                cost_usd=10.0,
            ))

        total_tokens = sum(
            r.tokens_input + r.tokens_output for r in tracker._records
        )
        ceiling = 50_000

        guardian.cost_ceiling_breach(total_tokens, ceiling)
        assert is_killed()
