from unittest.mock import AsyncMock, patch

from agents.departments.ml.graph import MAX_REVISIONS, build_ml_graph
from agents.departments.ml.ml_critic import MLCritic

_RICH_ML_OUTPUT = (
    "Pipeline with split before fit, no leakage risk. Validation set held out. "
    "Baseline comparison: logistic regression. Dropout and weight decay regularization. "
    "DVC data versioning. Bias detection on protected attributes. "
    "Model registry with versioning. Inference latency benchmark. "
    "A/B canary rollout. Drift monitoring with distribution tests."
)


def _mock_llm(**kwargs):
    return AsyncMock(return_value=_RICH_ML_OUTPUT)


def test_happy_path_approves():
    with patch("agents.departments.ml.data_curator.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ml.embedding_engineer.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ml.trainer.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ml.ml_critic.call_llm", new_callable=lambda: AsyncMock(return_value="APPROVED")):
        graph = build_ml_graph()
        result = graph.invoke({"request": "train a churn classifier"})
        assert result["approved"] is True
        assert result["result"]
        assert result.get("revisions", 0) == 0


def test_output_carries_domain_signal():
    with patch("agents.departments.ml.data_curator.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ml.embedding_engineer.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ml.trainer.call_llm", new_callable=_mock_llm), \
         patch("agents.departments.ml.ml_critic.call_llm", new_callable=lambda: AsyncMock(return_value="APPROVED")):
        graph = build_ml_graph()
        out = graph.invoke({"request": "fine-tune a ranking model"})
        text = (out["result"] + out.get("draft", "")).lower()
        assert "baseline" in text
        assert "leakage" in text
        assert "drift" in text


def test_bounded_loop_escalates():
    with patch(
        "agents.departments.ml.ml_critic.MLCritic._review",
        return_value=["forced failure"],
    ), patch("agents.departments.ml.ml_critic.call_llm", new_callable=lambda: AsyncMock(return_value="issues found")), \
       patch("agents.departments.ml.data_curator.call_llm", new_callable=_mock_llm), \
       patch("agents.departments.ml.embedding_engineer.call_llm", new_callable=_mock_llm), \
       patch("agents.departments.ml.trainer.call_llm", new_callable=_mock_llm):
        graph = build_ml_graph()
        result = graph.invoke({"request": "build something", "revisions": MAX_REVISIONS - 1})
        assert result.get("revisions", 0) <= MAX_REVISIONS + 1
        if not result.get("approved"):
            assert "ESCALATION" in result.get("result", "")


def test_max_revisions_constant():
    assert MAX_REVISIONS == 3


def test_ml_critic_flags_leakage_and_baseline():
    weak = "trained a model with dropout, weight decay, dvc versioning, bias check, registry, latency, a/b, drift"
    issues = MLCritic()._review(weak, "")
    joined = " ".join(issues).lower()
    # missing: leakage handling, validation set, baseline
    assert "leakage" in joined
    assert "baseline" in joined


def test_ml_critic_empty_result():
    assert MLCritic()._review("", "") == ["ML pipeline result is empty"]


def test_ml_critic_clean_passes():
    strong = (
        "split before fit, no leakage; validation set; baseline comparison; dropout weight decay "
        "regularization; dvc data versioning; bias detection; model registry; inference latency "
        "benchmark; a/b canary rollout; drift monitoring"
    )
    assert MLCritic()._review(strong, "") == []
