import json

from agents.prompts import MARKETING_CRITIC
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("marketing.critic")

SUBJECT_MAX = 60
TWEET_MAX = 280


class MarketingCritic:
    """Critic: reviews marketing copy for brand, compliance and conversion.

    Checks for missing CTAs, off-brand tone, unsupported claims, CAN-SPAM
    gaps, missing UTM tracking, absent A/B variants, channel length limits,
    mobile and segmentation gaps.
    """

    name = "marketing.critic"
    role = "critic"

    SYSTEM_PROMPT = MARKETING_CRITIC

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info(
                "marketing critic rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("marketing critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []
        if not result or not result.strip():
            return ["Result is empty — no copy produced"]

        low = result.lower()
        try:
            content = json.loads(result)
        except json.JSONDecodeError:
            content = {}

        if "cta" not in low and "call to action" not in low:
            issues.append("No clear call-to-action in any asset")
        if "utm_" not in low:
            issues.append("Missing UTM tracking parameters on links")
        if "unsubscribe" not in low:
            issues.append("CAN-SPAM violation: email missing unsubscribe link")
        if "94105" not in result and "address" not in low and "st," not in low:
            issues.append("CAN-SPAM violation: email missing physical mailing address")
        if "variant" not in low:
            issues.append("No A/B test variants provided")
        if "mobile" not in low:
            issues.append("Missing mobile optimization consideration")
        if "segment" not in low:
            issues.append("Missing audience segmentation")
        if not self._has_supporting_data(low):
            issues.append("Claims made without supporting data (no metrics cited)")

        issues.extend(self._length_checks(content))
        issues.extend(self._voice_checks(low))
        return issues

    def _has_supporting_data(self, low: str) -> bool:
        return any(ch.isdigit() for ch in low) and (
            "%" in low or "hrs" in low or "mql" in low or "x " in low
        )

    def _length_checks(self, content: dict) -> list[str]:
        issues: list[str] = []
        for email in content.get("email_sequence", []):
            for key in ("subject_variant_a", "subject_variant_b"):
                subject = email.get(key, "")
                if len(subject) > SUBJECT_MAX:
                    issues.append(
                        f"Subject line too long ({len(subject)} > {SUBJECT_MAX}): {subject[:40]}…"
                    )
        for post in content.get("social_posts", []):
            if post.get("channel") == "x":
                for key in ("variant_a", "variant_b"):
                    text = post.get(key, "")
                    if len(text) > TWEET_MAX:
                        issues.append(
                            f"Tweet exceeds {TWEET_MAX} chars ({len(text)})"
                        )
        return issues

    def _voice_checks(self, low: str) -> list[str]:
        casual = any(w in low for w in (" gonna ", " wanna ", " lol ", "!!!"))
        formal = "heretofore" in low or "pursuant to" in low
        if casual and formal:
            return ["Brand voice inconsistency: mixes casual and formal tone"]
        return []
