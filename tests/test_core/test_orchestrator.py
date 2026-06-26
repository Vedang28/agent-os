import pytest

from core.graph import _department_keywords, register_department_graph, _department_graphs
from core.orchestrator import _score_departments, _select_departments, orchestrate


@pytest.fixture(autouse=True)
def _setup_keywords():
    _department_graphs.clear()
    _department_keywords.clear()
    _department_keywords.update({
        "engineering": ["build", "create", "design", "implement", "code", "api"],
        "backend": ["backend", "endpoint", "controller", "route", "rest", "server"],
        "database": ["database", "schema", "migration", "sql", "query", "table", "postgres"],
        "auth": ["auth", "login", "signup", "jwt", "oauth", "session", "permission"],
        "frontend": ["frontend", "react", "next", "component", "ui", "page"],
        "testing": ["test", "pytest", "jest", "coverage", "unit test"],
        "security_dev": ["security", "vulnerability", "injection", "xss", "owasp"],
        "dependency": ["dependency", "package", "npm", "pip", "upgrade", "outdated"],
        "pipeline": ["build project", "create project", "new project", "build app"],
    })
    yield
    _department_graphs.clear()
    _department_keywords.clear()


def test_deep_routes_to_engineering():
    result = orchestrate({"request": "build a REST API", "lane": "deep"})
    assert result["department"] == "engineering"


def test_plan_is_list():
    result = orchestrate({"request": "build a REST API", "lane": "deep"})
    assert isinstance(result["plan"], list)
    assert len(result["plan"]) >= 1


def test_code_keyword_routes_engineering():
    result = orchestrate({"request": "write code for the login page", "lane": "deep"})
    assert result["department"] == "engineering"


def test_default_department():
    result = orchestrate({"request": "do something vague", "lane": "fast"})
    assert result["department"] == "engineering"


def test_departments_field_present():
    result = orchestrate({"request": "build an API", "lane": "deep"})
    assert "departments" in result
    assert isinstance(result["departments"], list)
    assert result["department"] == result["departments"][0]


def test_single_department_database():
    depts = _select_departments("write a SQL migration for the table")
    assert "database" in depts


def test_multi_department_auth_plus_backend():
    depts = _select_departments("add JWT auth to the REST backend endpoint")
    assert "auth" in depts
    assert "backend" in depts


def test_pipeline_for_full_project():
    depts = _select_departments("build project from scratch")
    assert depts == ["pipeline"]


def test_max_four_departments():
    depts = _select_departments(
        "add auth login to the backend REST endpoint with database "
        "migration and security test coverage plus dependency upgrade"
    )
    assert len(depts) <= 4


def test_scoring_ranks_correctly():
    scores = _score_departments("database schema migration for postgres table")
    score_dict = dict(scores)
    assert score_dict.get("database", 0) > 0
    # Database should score highest for a database-specific request
    if score_dict:
        top_dept = max(score_dict, key=score_dict.get)
        assert top_dept == "database"


def test_fallback_when_no_match():
    depts = _select_departments("do something completely unrelated to anything")
    assert depts == ["engineering"]
