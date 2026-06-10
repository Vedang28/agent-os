import pytest

from agents.departments.intelligence.graph import build_intelligence_graph
from core.graph import (
    _department_graphs,
    _department_keywords,
    build_company_graph,
    register_department_graph,
)
from core.checkpointer import reset_checkpointer
from agents.departments.engineering.graph import build_engineering_graph
from infra.daemon import Daemon


@pytest.fixture(autouse=True)
def _clean():
    _department_graphs.clear()
    _department_keywords.clear()
    reset_checkpointer()
    eng = build_engineering_graph()
    register_department_graph("engineering", eng, keywords=[
        "build", "create", "design", "implement", "code", "api",
    ])
    intel = build_intelligence_graph()
    register_department_graph("intelligence", intel, keywords=[
        "briefing", "intelligence", "research", "trends", "news", "analyze",
    ])
    yield
    _department_graphs.clear()
    _department_keywords.clear()
    reset_checkpointer()


class TestDaemonIntelligenceFlow:
    @pytest.mark.asyncio
    async def test_daemon_tick_triggers_intelligence(self):
        company = build_company_graph()
        daemon = Daemon(tick_interval=1.0)
        daemon.register_job(
            "intelligence",
            company,
            trigger_request="Generate daily intelligence briefing",
        )
        results = await daemon.tick()
        assert len(results) == 1
        assert results[0].get("approved") is True
        assert results[0].get("result") is not None

    @pytest.mark.asyncio
    async def test_daemon_saves_checkpoint_after_tick(self):
        company = build_company_graph()
        daemon = Daemon()
        daemon.register_job(
            "intelligence",
            company,
            trigger_request="Generate daily intelligence briefing",
        )
        await daemon.tick()
        cp = daemon.load_checkpoint("intelligence")
        assert cp is not None
        assert cp.get("result") is not None

    @pytest.mark.asyncio
    async def test_daemon_resume_after_restart(self):
        company = build_company_graph()
        d1 = Daemon()
        d1.register_job("intelligence", company, trigger_request="Generate briefing")
        await d1.tick()
        cp = d1.load_checkpoint("intelligence")
        assert cp is not None

        d2 = Daemon()
        d2.register_job("intelligence", company, trigger_request="Generate briefing")
        d2.save_checkpoint("intelligence", cp)
        results = await d2.tick()
        assert len(results) == 1


class TestIntelligenceInCompanyGraph:
    def test_intelligence_request_routes_correctly(self):
        company = build_company_graph()
        result = company.invoke(
            {"request": "Generate daily intelligence briefing"},
            config={"configurable": {"thread_id": "intel_test_1"}},
        )
        assert result.get("department") == "intelligence"
        assert result.get("approved") is True

    def test_engineering_request_still_works(self):
        company = build_company_graph()
        result = company.invoke(
            {"request": "Build a REST API for user management"},
            config={"configurable": {"thread_id": "eng_test_1"}},
        )
        assert result.get("department") == "engineering"
        assert result.get("approved") is True

    def test_instant_request_skips_departments(self):
        company = build_company_graph()
        result = company.invoke(
            {"request": "hello"},
            config={"configurable": {"thread_id": "instant_test_1"}},
        )
        assert result.get("lane") == "instant"
        assert result.get("approved") is True
