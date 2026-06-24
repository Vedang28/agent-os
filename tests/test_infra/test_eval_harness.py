import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from infra.eval_harness import EvalCase, EvalResult, EvalHarness


class TestEvalCase:
    def test_required_fields(self):
        case = EvalCase(
            name="test.case",
            department="engineering",
            input_request="do something",
        )
        assert case.name == "test.case"
        assert case.department == "engineering"
        assert case.input_request == "do something"

    def test_defaults(self):
        case = EvalCase(
            name="test.case",
            department="engineering",
            input_request="do something",
        )
        assert case.expected_approved is True
        assert case.expected_department is None
        assert case.expected_lane is None
        assert case.max_tokens == 100_000
        assert case.max_seconds == 60.0

    def test_missing_required_field_raises(self):
        with pytest.raises(Exception):
            EvalCase(name="test.case", department="engineering")


class TestEvalResult:
    def test_required_fields(self):
        result = EvalResult(
            case_name="test.case",
            department="engineering",
            passed=True,
        )
        assert result.case_name == "test.case"
        assert result.passed is True

    def test_defaults(self):
        result = EvalResult(
            case_name="test.case",
            department="engineering",
            passed=False,
        )
        assert result.actual_approved is False
        assert result.actual_revisions == 0
        assert result.tokens_used == 0
        assert result.seconds_elapsed == 0.0
        assert result.within_budget is True
        assert result.error is None


class TestEvalHarness:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_graph = MagicMock()
        self.mock_graph.invoke.return_value = {
            "approved": True,
            "department": "engineering",
            "lane": "deep",
            "revisions": 1,
            "result": "done",
        }
        self.harness = EvalHarness(graph_factory=lambda: self.mock_graph)

    def _make_case(self, **overrides) -> EvalCase:
        defaults = {
            "name": "engineering.test",
            "department": "engineering",
            "input_request": "build something",
            "expected_approved": True,
            "expected_department": "engineering",
            "expected_lane": "deep",
        }
        defaults.update(overrides)
        return EvalCase(**defaults)

    def test_register_eval(self):
        case = self._make_case()
        self.harness.register_eval(case)
        assert "engineering.test" in self.harness._evals

    def test_run_eval_passes(self):
        case = self._make_case()
        self.harness.register_eval(case)
        result = self.harness.run_eval("engineering.test")
        assert result.passed is True
        assert result.actual_approved is True
        assert result.actual_revisions == 1

    def test_run_eval_fails_on_approval_mismatch(self):
        case = self._make_case(expected_approved=True)
        self.harness.register_eval(case)
        self.mock_graph.invoke.return_value = {
            "approved": False,
            "department": "engineering",
            "lane": "deep",
        }
        result = self.harness.run_eval("engineering.test")
        assert result.passed is False

    def test_run_eval_fails_on_department_mismatch(self):
        case = self._make_case(expected_department="engineering")
        self.harness.register_eval(case)
        self.mock_graph.invoke.return_value = {
            "approved": True,
            "department": "intelligence",
            "lane": "deep",
        }
        result = self.harness.run_eval("engineering.test")
        assert result.passed is False

    def test_run_all(self):
        for i in range(3):
            case = self._make_case(name=f"test.case_{i}")
            self.harness.register_eval(case)
        results = self.harness.run_all()
        assert len(results) == 3

    def test_run_department(self):
        self.harness.register_eval(self._make_case(name="eng.a", department="engineering"))
        self.harness.register_eval(self._make_case(name="eng.b", department="engineering"))
        self.harness.register_eval(
            self._make_case(name="intel.a", department="intelligence")
        )
        eng_results = self.harness.run_department("engineering")
        assert len(eng_results) == 2
        assert all(r.department == "engineering" for r in eng_results)

    def test_load_from_yaml(self, tmp_path: Path):
        yaml_content = (
            "- name: yaml.test\n"
            "  department: engineering\n"
            '  input_request: "build it"\n'
            "  expected_approved: true\n"
        )
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)
        self.harness.load_from_yaml(yaml_file)
        assert "yaml.test" in self.harness._evals

    def test_eval_captures_error(self):
        case = self._make_case()
        self.harness.register_eval(case)
        self.mock_graph.invoke.side_effect = RuntimeError("model unavailable")
        result = self.harness.run_eval("engineering.test")
        assert result.passed is False
        assert result.error == "model unavailable"

    def test_within_budget_false_on_slow_eval(self):
        case = self._make_case(max_seconds=1.0)
        self.harness.register_eval(case)
        call_count = 0

        def mock_monotonic():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return 0.0
            return 5.0

        with patch("infra.eval_harness.time.monotonic", side_effect=mock_monotonic):
            result = self.harness.run_eval("engineering.test")
        assert result.within_budget is False
