import shutil
from pathlib import Path

from agents.departments.generator import create_department


def test_create_department_tmpdir(tmp_path):
    base = tmp_path / "departments"
    base.mkdir()

    dept = create_department("marketing", base_path=base)

    assert dept.exists()
    expected_files = ["__init__.py", "graph.py", "proposer.py", "worker.py", "critic.py"]
    for f in expected_files:
        p = dept / f
        assert p.exists(), f"{f} should exist"
        content = p.read_text(encoding="utf-8")
        # per-file content checks
        if f == "__init__.py":
            assert "from .graph import Graph" in content
        elif f == "graph.py":
            assert "class Graph" in content and "marketing" in content
        elif f == "proposer.py":
            assert "Proposal for" in content or "marketing" in content
        elif f == "worker.py":
            assert "Work result" in content or "marketing" in content
        elif f == "critic.py":
            assert "Critic" in content

    # cleanup
    shutil.rmtree(str(base))
