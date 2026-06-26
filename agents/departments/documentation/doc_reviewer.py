import json

from core.state import AgentState
from infra.telemetry import get_logger
from agents.prompts import DOCUMENTATION_REVIEWER

logger = get_logger("documentation.doc_reviewer")


class DocReviewer:
    name = "documentation.doc_reviewer"
    role = "critic"

    SYSTEM_PROMPT = DOCUMENTATION_REVIEWER

    async def run(self, state: AgentState) -> AgentState:
        result = state.get("result", "")
        draft = state.get("draft", "")
        revisions = state.get("revisions", 0)

        issues = self._review(result, draft)


        if issues:
            logger.info(
                "doc_reviewer rejected, revisions=%d, reason=%s",
                revisions + 1,
                issues[0],
            )
            return {
                "approved": False,
                "critique": {"reason": issues[0], "suggestions": issues},
                "revisions": revisions + 1,
            }

        logger.info("doc_reviewer approved after %d revisions", revisions)
        return {"approved": True}

    def _review(self, result: str, draft: str) -> list[str]:
        issues: list[str] = []

        if not result or not result.strip():
            return ["Documentation output is empty"]

        try:
            output = json.loads(result)
        except json.JSONDecodeError:
            return ["Documentation output is not valid structured output"]

        try:
            plan = json.loads(draft) if draft else {}
        except json.JSONDecodeError:
            plan = {}

        doc_types = plan.get("doc_types", [])
        required = set(plan.get("required_sections", []))
        documents = output.get("documents", [])

        if not documents:
            issues.append("No documents were produced")
            return issues

        produced_types = {d.get("type") for d in documents}
        for dtype in doc_types:
            if dtype not in produced_types:
                issues.append(f"Missing document for requested type: {dtype}")

        written = set(output.get("sections_written", []))
        missing_sections = required - written
        if missing_sections:
            issues.append(
                f"Missing required sections: {', '.join(sorted(missing_sections))}"
            )

        if ("api_reference" in doc_types or "guide" in doc_types) and not output.get(
            "code_examples"
        ):
            issues.append("Missing code examples for API/guide documentation")

        if "api_reference" in doc_types:
            symbols = output.get("documented_symbols", [])
            if not symbols:
                issues.append("API reference documents no symbols")
            for sym in symbols:
                if sym.get("parameters") != "documented" or sym.get("returns") != "documented":
                    issues.append(
                        f"Symbol {sym.get('name', 'unknown')} missing parameter/return docs"
                    )
                    break

        for example in output.get("code_examples", []):
            code = example.get("code", "")
            if not code.strip() or "(" not in code:
                issues.append("Incomplete code example (not runnable)")
                break

        return issues
