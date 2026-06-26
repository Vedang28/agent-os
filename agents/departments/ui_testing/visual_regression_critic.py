import re

from agents.llm import call_llm
from agents.prompts import UI_TESTING_VISUAL_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("ui_testing.visual_regression_critic")


class VisualRegressionCritic:
    name = "ui_testing.visual_regression_critic"
    role = "critic"

    SYSTEM_PROMPT = UI_TESTING_VISUAL_CRITIC

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
            logger.info(
                "visual_regression_critic rejected, revisions=%d, reason=%s",
                revisions + 1, issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("visual_regression_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []

        if not result or not result.strip():
            return ["Result is empty — no Playwright script to review"]

        lowered = result.lower()

        if re.search(r"page\.waitfortimeout\(", lowered) or re.search(r"time\.sleep\(", lowered):
            issues.append("Hardcoded wait (waitForTimeout/sleep) — use waitFor/expect on a locator instead")

        if re.search(r"\.click\(\s*\{\s*position", lowered) or re.search(r"mouse\.click\(\s*\d", lowered):
            issues.append("Hardcoded click coordinates — target a locator (getByRole/getByTestId)")

        has_mobile = "375" in result or "iphone" in lowered or "mobile" in lowered
        has_tablet = "768" in result or "ipad" in lowered or "tablet" in lowered
        if not (has_mobile and has_tablet):
            issues.append("Missing mobile/tablet viewport tests — add 375 and 768 width snapshots")

        if "page.route(" not in lowered and "fulfill(" not in lowered:
            issues.append("No network interception — screenshots will be non-deterministic; mock /api/ routes")

        if "500" not in result and "alert" not in lowered and "error" not in lowered:
            issues.append("Missing error-state visual test — capture the failure/error UI")

        if re.search(r"nth-child\(", lowered) or re.search(r"locator\(['\"][.#][\w >]+['\"]\)", result):
            issues.append("Fragile CSS/nth-child selectors — prefer getByRole/getByTestId")

        if "colorscheme" not in lowered and "dark" not in lowered:
            issues.append("Missing dark mode visual test — add emulateMedia colorScheme: 'dark'")

        if "axe" not in lowered and "accessibility" not in lowered:
            issues.append("No accessibility audit — integrate axe-core (AxeBuilder.analyze)")

        if "tohavescreenshot" not in lowered and "tomatchsnapshot" not in lowered:
            issues.append("No screenshot assertions — add toHaveScreenshot baselines")

        return issues
