import asyncio
from unittest.mock import MagicMock

import pytest

from agents.guardian import Guardian, _reset_approval_callback_for_testing, is_killed, set_approval_callback
from infra.daemon import Daemon


class TestDaemonBasic:
    def test_init_defaults(self):
        d = Daemon()
        assert d.tick_count == 0
        assert not d.is_running
        assert d.list_jobs() == []

    def test_register_job(self):
        d = Daemon()
        mock_graph = MagicMock()
        d.register_job("test_job", mock_graph, trigger_request="hello")
        assert "test_job" in d.list_jobs()

    def test_list_jobs_multiple(self):
        d = Daemon()
        d.register_job("a", MagicMock())
        d.register_job("b", MagicMock())
        assert sorted(d.list_jobs()) == ["a", "b"]


class TestCheckpoints:
    def test_save_and_load(self):
        d = Daemon()
        d.save_checkpoint("job1", {"result": "ok", "approved": True})
        cp = d.load_checkpoint("job1")
        assert cp is not None
        assert cp["result"] == "ok"

    def test_load_nonexistent(self):
        d = Daemon()
        assert d.load_checkpoint("nonexistent") is None


class TestTick:
    @pytest.mark.asyncio
    async def test_tick_increments_count(self):
        d = Daemon()
        await d.tick()
        assert d.tick_count == 1
        await d.tick()
        assert d.tick_count == 2

    @pytest.mark.asyncio
    async def test_tick_invokes_job(self):
        d = Daemon()
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"result": "done", "approved": True}
        d.register_job("test", mock_graph, trigger_request="do something")
        results = await d.tick()
        assert len(results) == 1
        assert results[0].get("approved") is True
        mock_graph.invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_tick_saves_checkpoint_after_job(self):
        d = Daemon()
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"result": "test", "approved": True}
        d.register_job("j1", mock_graph)
        await d.tick()
        cp = d.load_checkpoint("j1")
        assert cp is not None
        assert cp["result"] == "test"

    @pytest.mark.asyncio
    async def test_tick_handles_job_failure(self):
        d = Daemon()
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = RuntimeError("boom")
        d.register_job("failing", mock_graph)
        results = await d.tick()
        assert len(results) == 1
        assert "error" in results[0]

    @pytest.mark.asyncio
    async def test_tick_respects_wall_clock_budget(self):
        d = Daemon(max_wall_clock_per_tick=0.0)
        d.register_job("a", MagicMock())
        d.register_job("b", MagicMock())
        results = await d.tick()
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_tick_with_multiple_jobs(self):
        d = Daemon()
        g1 = MagicMock()
        g1.invoke.return_value = {"result": "job1", "approved": True}
        g2 = MagicMock()
        g2.invoke.return_value = {"result": "job2", "approved": True}
        d.register_job("a", g1, trigger_request="task a")
        d.register_job("b", g2, trigger_request="task b")
        results = await d.tick()
        assert len(results) == 2


class TestResumeAfterRestart:
    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self):
        d = Daemon()
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"result": "resumed", "approved": True}
        d.register_job("resumable", mock_graph, trigger_request="task")
        d.save_checkpoint("resumable", {"result": "partial", "approved": False})
        results = await d.tick()
        assert len(results) == 1
        call_args = mock_graph.invoke.call_args[0][0]
        assert call_args.get("result") == "partial"


class TestStartStop:
    @pytest.mark.asyncio
    async def test_stop_sets_flag(self):
        d = Daemon(tick_interval=100)
        d.register_job("noop", MagicMock(invoke=MagicMock(return_value={})))

        async def stop_after_one():
            while d.tick_count < 1:
                await asyncio.sleep(0.01)
            await d.stop()

        await asyncio.gather(d.start(), stop_after_one())
        assert not d.is_running
        assert d.tick_count >= 1

    @pytest.mark.asyncio
    async def test_stop_saves_state(self):
        d = Daemon(tick_interval=100)
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"result": "saved", "approved": True}
        d.register_job("saveable", mock_graph)

        async def stop_after_one():
            while d.tick_count < 1:
                await asyncio.sleep(0.01)
            await d.stop()

        await asyncio.gather(d.start(), stop_after_one())
        cp = d.load_checkpoint("saveable")
        assert cp is not None


class TestDaemonKillSwitch:
    @pytest.fixture(autouse=True)
    def _reset_kill(self):
        _reset_approval_callback_for_testing()
        set_approval_callback(lambda a, d: True)
        Guardian(timeout=1.0).reset_kill_switch()
        _reset_approval_callback_for_testing()
        yield
        _reset_approval_callback_for_testing()
        set_approval_callback(lambda a, d: True)
        Guardian(timeout=1.0).reset_kill_switch()
        _reset_approval_callback_for_testing()

    @pytest.mark.asyncio
    async def test_tick_aborted_when_killed(self):
        guardian = Guardian(timeout=1.0)
        guardian.kill()
        d = Daemon()
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"result": "done"}
        d.register_job("test", mock_graph)
        results = await d.tick()
        assert results == []
        mock_graph.invoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_daemon_loop_stops_when_killed(self):
        d = Daemon(tick_interval=100)
        d.register_job("noop", MagicMock(invoke=MagicMock(return_value={})))
        guardian = Guardian(timeout=1.0)

        async def kill_after_one():
            while d.tick_count < 1:
                await asyncio.sleep(0.01)
            guardian.kill()

        await asyncio.gather(d.start(), kill_after_one())
        assert is_killed()
        assert d.tick_count >= 1
