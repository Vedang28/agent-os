from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from infra.telemetry import get_logger

logger = get_logger("infra.eval_harness")


class EvalCase(BaseModel):
    name: str
    department: str
    input_request: str
    expected_approved: bool = True
    expected_department: str | None = None
    expected_lane: str | None = None
    max_tokens: int = 100_000
    max_seconds: float = 60.0


class EvalResult(BaseModel):
    case_name: str
    department: str
    passed: bool
    actual_approved: bool = False
    actual_revisions: int = 0
    tokens_used: int = 0
    seconds_elapsed: float = 0.0
    within_budget: bool = True
    error: str | None = None


class EvalHarness:
    def __init__(self, graph_factory: Callable[[], Any]) -> None:
        self._graph_factory = graph_factory
        self._evals: dict[str, EvalCase] = {}

    def register_eval(self, case: EvalCase) -> None:
        self._evals[case.name] = case
        logger.info("registered eval case=%s dept=%s", case.name, case.department)

    def load_from_yaml(self, path: Path) -> None:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, list):
            raise ValueError(f"Expected list in {path}, got {type(data).__name__}")
        for entry in data:
            case = EvalCase(**entry)
            self.register_eval(case)

    def run_eval(self, name: str) -> EvalResult:
        case = self._evals[name]
        try:
            graph = self._graph_factory()
            start = time.monotonic()
            result = graph.invoke(
                {"request": case.input_request},
                config={"configurable": {"thread_id": f"eval_{name}"}},
            )
            elapsed = time.monotonic() - start

            actual_approved = result.get("approved", False)
            actual_dept = result.get("department", "")
            actual_lane = result.get("lane", "")
            actual_revisions = result.get("revisions", 0)
            tokens = result.get("tokens_used", 0)

            passed = True
            if actual_approved != case.expected_approved:
                passed = False
            if case.expected_department and actual_dept != case.expected_department:
                passed = False
            if case.expected_lane and actual_lane != case.expected_lane:
                passed = False
            within_budget = elapsed <= case.max_seconds

            return EvalResult(
                case_name=case.name,
                department=case.department,
                passed=passed,
                actual_approved=actual_approved,
                actual_revisions=actual_revisions,
                tokens_used=tokens,
                seconds_elapsed=elapsed,
                within_budget=within_budget,
            )
        except Exception as e:
            logger.error("eval %s failed: %s", name, e)
            return EvalResult(
                case_name=case.name,
                department=case.department,
                passed=False,
                error=str(e),
            )

    def run_all(self) -> list[EvalResult]:
        results = []
        for name in self._evals:
            results.append(self.run_eval(name))
        return results

    def run_department(self, department: str) -> list[EvalResult]:
        results = []
        for name, case in self._evals.items():
            if case.department == department:
                results.append(self.run_eval(name))
        return results
