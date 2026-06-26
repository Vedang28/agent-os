from unittest.mock import patch

from agents.departments.ml.graph import MAX_REVISIONS, build_ml_graph
from agents.departments.ml.ml_critic import MLCritic


def test_happy_path_approves():
    """Agents are pure prompt containers — patch _review to simulate approval."""
    with patch.object(MLCritic, "_review", return_value=[]):
        graph = build_ml_graph()
        result = graph.invoke({"request": "train a churn classifier"})
        assert result["approved"] is True
        assert result["result"]
        assert result.get("revisions", 0) == 0


def test_output_contains_prompt_and_request():
    """Agents embed their system prompt + request in the output."""
    with patch.object(MLCritic, "_review", return_value=[]):
        graph = build_ml_graph()
        out = graph.invoke({"request": "fine-tune a ranking model"})
        text = (out["result"] + out.get("draft", "")).lower()
        assert "ranking" in text or "fine-tune" in text or "model" in text


def test_bounded_loop_escalates():
    with patch.object(MLCritic, "_review", return_value=["forced failure"]):
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
