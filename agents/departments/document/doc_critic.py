import json

from core.state import AgentState
from infra.telemetry import get_logger
from agents.llm import call_llm
from agents.prompts import DOCUMENT_CRITIC

logger = get_logger("document.doc_critic")


class DocCritic:
    name = "document.doc_critic"
    role = "critic"

    SYSTEM_PROMPT = DOCUMENT_CRITIC

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
                "doc_critic rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("doc_critic approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []

        if not result or not result.strip():
            return ["Document extraction is empty"]

        try:
            extraction = json.loads(result)
        except json.JSONDecodeError:
            return ["Document extraction is not valid structured output"]

        try:
            plan = json.loads(draft) if draft else {}
        except json.JSONDecodeError:
            plan = {}
        strategies = plan.get("extraction_strategy", [])

        if "tables" in strategies:
            tables = extraction.get("tables", [])
            if not tables:
                issues.append("Table data missing: no tables extracted")
            for table in tables:
                headers = table.get("headers", [])
                rows = table.get("rows", [])
                if not headers:
                    issues.append("Table missing columns (no headers)")
                    break
                if not rows:
                    issues.append("Table missing rows")
                    break
                if any(len(row) != len(headers) for row in rows):
                    issues.append("Table rows missing cells (column count mismatch)")
                    break

        if "form_fields" in strategies:
            fields = extraction.get("fields", [])
            if not fields:
                issues.append("Field mappings missing (no form fields extracted)")
            for field in fields:
                if not field.get("key") or field.get("value") is None:
                    issues.append("Field mapping incorrect (missing key or value)")
                    break

        if "hierarchy" in strategies:
            hierarchy = extraction.get("hierarchy", [])
            if not hierarchy:
                issues.append("Document hierarchy missing (no headings extracted)")
            else:
                levels = [h.get("level", 0) for h in hierarchy]
                for prev, cur in zip(levels, levels[1:]):
                    if cur > prev + 1:
                        issues.append("Document hierarchy broken (heading levels skipped)")
                        break

        if "metadata" in strategies:
            metadata = extraction.get("metadata", {})
            if not metadata:
                issues.append("Metadata not extracted (author, date, version)")
            elif metadata.get("created_date") and not self._is_date(metadata["created_date"]):
                issues.append("Incorrect data type: date extracted as string")

        if "images" in strategies and not extraction.get("embedded_content"):
            issues.append("Embedded images/charts not described")

        if "cross_references" in strategies:
            refs = extraction.get("cross_references", [])
            if any(not r.get("resolved_to") for r in refs):
                issues.append("Cross-references unresolved")

        text = extraction.get("text", "")
        if text and any(artifact in text for artifact in ("\x0c", "  \n", "\t\t")):
            issues.append("Formatting artifacts present in extracted text")

        if not extraction.get("section_references"):
            issues.append("Missing page numbers or section references")

        return issues

    def _is_date(self, value) -> bool:
        if not isinstance(value, str):
            return True
        from datetime import datetime

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
        return False
