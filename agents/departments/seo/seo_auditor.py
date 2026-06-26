import json

from agents.llm import call_llm
from agents.prompts import SEO_AUDITOR
from core.state import AgentState
from infra.telemetry import get_logger

logger = get_logger("seo.auditor")

META_TITLE_MAX = 60
META_DESC_MIN = 70
META_DESC_MAX = 160
MIN_WORD_COUNT = 300
DENSITY_MIN = 0.5
DENSITY_MAX = 3.0


class SeoAuditor:
    """Critic: audits the optimized page against on-page SEO rules.

    Flags missing/duplicate meta, H1 problems, missing internal links,
    absent schema, alt-text gaps, missing canonical / social cards, keyword
    stuffing, thin content and non-SEO-friendly URLs.
    """

    name = "seo.auditor"
    role = "critic"

    SYSTEM_PROMPT = SEO_AUDITOR

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)

        llm_review = await call_llm(
            task_type="long_docs",
            system=self.SYSTEM_PROMPT,
            user=f"Draft/Plan:\n{draft}\n\nOutput to review:\n{result}",
        )
        if "APPROVED" not in llm_review.upper() and llm_review.strip():
            for line in llm_review.strip().split("\n"):
                line = line.strip().lstrip("-•*123456789. ")
                if line and line not in issues:
                    issues.append(line)

        if issues:
            logger.info(
                "seo auditor rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("seo auditor approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        if not result or not result.strip():
            return ["Result is empty — no page produced"]
        try:
            page = json.loads(result)
        except json.JSONDecodeError:
            return ["Result is not valid JSON; cannot audit page"]

        issues: list[str] = []
        issues.extend(self._meta_checks(page))
        issues.extend(self._heading_checks(page))
        issues.extend(self._link_and_schema_checks(page))
        issues.extend(self._image_checks(page))
        issues.extend(self._social_checks(page))
        issues.extend(self._content_checks(page))
        issues.extend(self._url_checks(page))
        return issues

    def _meta_checks(self, page: dict) -> list[str]:
        issues: list[str] = []
        title = page.get("meta_title", "")
        desc = page.get("meta_description", "")
        if not title:
            issues.append("Missing meta title")
        elif len(title) > META_TITLE_MAX:
            issues.append(f"Meta title too long ({len(title)} > {META_TITLE_MAX})")
        if not desc:
            issues.append("Missing meta description")
        elif not (META_DESC_MIN <= len(desc) <= META_DESC_MAX):
            issues.append(
                f"Meta description length {len(desc)} outside {META_DESC_MIN}-{META_DESC_MAX}"
            )
        if title and desc and title.strip() == desc.strip():
            issues.append("Duplicate meta title and description")
        return issues

    def _heading_checks(self, page: dict) -> list[str]:
        headings = page.get("heading_structure", [])
        h1_count = sum(1 for h in headings if str(h.get("level", "")).lower() == "h1")
        if h1_count == 0:
            return ["Missing H1 tag"]
        if h1_count > 1:
            return [f"Multiple H1 tags ({h1_count}); only one allowed"]
        return []

    def _link_and_schema_checks(self, page: dict) -> list[str]:
        issues: list[str] = []
        if not page.get("internal_links"):
            issues.append("No internal links to related content")
        if not page.get("schema_jsonld"):
            issues.append("Missing schema / structured-data markup")
        if not page.get("canonical_url"):
            issues.append("Missing canonical URL")
        if not page.get("robots"):
            issues.append("Missing robots directive")
        return issues

    def _image_checks(self, page: dict) -> list[str]:
        for img in page.get("images", []):
            if not img.get("alt"):
                return [f"Image missing alt text: {img.get('src', 'unknown')}"]
        return []

    def _social_checks(self, page: dict) -> list[str]:
        issues: list[str] = []
        if not page.get("open_graph"):
            issues.append("Missing Open Graph meta tags")
        if not page.get("twitter_card"):
            issues.append("Missing Twitter Card meta tags")
        return issues

    def _content_checks(self, page: dict) -> list[str]:
        issues: list[str] = []
        words = page.get("word_count", 0)
        if words < MIN_WORD_COUNT:
            issues.append(f"Thin content ({words} words < {MIN_WORD_COUNT})")
        density = page.get("keyword", {}).get("density_pct")
        if density is None:
            issues.append("Keyword density not measured")
        elif density > DENSITY_MAX:
            issues.append(f"Keyword stuffing: density {density}% > {DENSITY_MAX}%")
        elif density < DENSITY_MIN:
            issues.append(f"Keyword density too low: {density}% < {DENSITY_MIN}%")
        return issues

    def _url_checks(self, page: dict) -> list[str]:
        slug = page.get("url_slug", "")
        if not slug:
            return ["Missing URL slug"]
        if len(slug) > 75:
            return [f"URL slug too long ({len(slug)} chars)"]
        if any(c.isspace() or (not c.isalnum() and c != "-") for c in slug):
            return ["URL not SEO-friendly (spaces or special characters in slug)"]
        return []
