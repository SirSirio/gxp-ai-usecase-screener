"""Tools the assessor may call (agent pattern).

get_section(document, section): fetch a full section when a retrieved chunk is not enough, e.g.
the whole of Annex 22 §10 (Operation) instead of one chunk of §10.1. Every call is recorded and
the fetched chunk ids become citable.
"""
from __future__ import annotations

from app.retrieval.index import KnowledgeIndex

GET_SECTION_SPEC = {
    "name": "get_section",
    "description": (
        "Fetch the full text of one section of a source document, including its subsections. "
        "Use it when a retrieved passage is cut off or you need the surrounding requirements. "
        "Documents: A22 (Annex 22 draft), A11 (Annex 11 2011), A11D (Annex 11 draft), CH4D (Chapter 4 draft), "
        "Q9 (ICH Q9(R1)), AIA (EU AI Act, sections like 'art-50'), FDA-CRED (FDA AI credibility guidance, e.g. 'IV.A.3'), "
        "FDA-DP (FDA 2023 discussion paper, e.g. 'area-5'), FDA-WL (FDA warning letter 320-26-58, e.g. 'ai-use')."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "document": {"type": "string", "description": "Document id, e.g. A22"},
            "section": {"type": "string", "description": "Section id, e.g. 3.3 or art-50 or ai-use"},
        },
        "required": ["document", "section"],
    },
}


class ToolBox:
    MAX_CALLS = 4

    def __init__(self, index: KnowledgeIndex):
        self.index = index
        self.calls: list[dict] = []
        self.fetched_ids: set[str] = set()

    def get_section(self, document: str, section: str) -> dict:
        if len(self.calls) >= self.MAX_CALLS:
            result = {"error": f"tool call limit ({self.MAX_CALLS}) reached"}
        else:
            sec = self.index.get_section(document.strip(), section.strip().lstrip("§"))
            if sec is None:
                result = {"error": f"section {section!r} not found in {document!r}"}
            else:
                self.fetched_ids.update(sec.chunk_ids)
                result = {"document": sec.doc_short, "section": sec.section, "title": sec.title,
                          "chunk_ids": sec.chunk_ids, "text": sec.text}
        self.calls.append({"tool": "get_section", "args": {"document": document, "section": section},
                           "ok": "error" not in result, "chunk_ids": result.get("chunk_ids", [])})
        return result

    def run(self, name: str, args: dict) -> dict:
        if name == "get_section":
            return self.get_section(str(args.get("document", "")), str(args.get("section", "")))
        self.calls.append({"tool": name, "args": args, "ok": False})
        return {"error": f"unknown tool {name!r}"}
