from agents.llm import call_llm
from agents.prompts import ML_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ml.ml_critic")


class MLCritic:
    name = "ml.ml_critic"
    role = "critic"

    SYSTEM_PROMPT = ML_CRITIC

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)

        llm_review = await call_llm(
            task_type="code",
            system=self.SYSTEM_PROMPT,
            user=f"Draft/Plan:\n{draft}\n\nImplementation to review:\n{result}",
        )
        if "APPROVED" not in llm_review.upper() and llm_review.strip():
            for line in llm_review.strip().split("\n"):
                line = line.strip().lstrip("-•*123456789. ")
                if line and line not in issues:
                    issues.append(line)

        if issues:
            logger.info("ml_critic rejected, revisions=%d, reason=%s", revisions + 1, issues[0])
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }
        logger.info("ml_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        if not result or not result.strip():
            return ["ML pipeline result is empty"]

        # Judge the whole pipeline: data plan (draft) + embedding + training (result).
        text = (result + "\n" + draft).lower()
        issues: list[str] = []

        if "leakage" not in text and "fit on train" not in text:
            issues.append(
                "Possible data leakage: no evidence the split happens before fitting "
                "transforms / test isolated from train"
            )

        if "validation" not in text and "val set" not in text and "val_loader" not in text:
            issues.append("No validation set — only train/test, nothing to tune/early-stop on")

        if "baseline" not in text:
            issues.append("No baseline model for comparison")

        if not any(k in text for k in ("dropout", "weight decay", "weight_decay", "regulariz")):
            issues.append("Missing regularization (dropout / weight decay) — overfitting risk")

        if not any(k in text for k in ("dvc", "mlflow", "data version", "data_version", "versioning")):
            issues.append("No data versioning (DVC / MLflow) — runs not reproducible")

        if "bias" not in text:
            issues.append("Training-data bias not addressed")

        if "registry" not in text and "model version" not in text:
            issues.append("No model versioning / model registry")

        if "latency" not in text:
            issues.append("Missing inference latency benchmark")

        if not any(k in text for k in ("a/b", "ab test", "canary")):
            issues.append("No A/B testing / canary rollout strategy")

        if "drift" not in text:
            issues.append("No monitoring for data / model drift")

        return issues
