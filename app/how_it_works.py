"""The "How it works" page (/how-it-works): the process flow and the decision tree, as data.

Presentation only. The tree is written out by hand so that it can be checked: tests/test_how_it_works.py
walks it for every combination of classes and compares each leaf with app.rules.decide(). Outcome labels,
tones, rule explanations and source tags are read from the code (VERDICT_LABELS, RULES, decide), never
retyped here, so a renamed label or a changed source shows up on the page without an edit.
"""
from __future__ import annotations

import re

from app.ingest.sources import SOURCES, SOURCES_BY_ID
from app.intake_form import MAX_ROUNDS, QUESTIONS as FORM_QUESTIONS
from app.rules import QUESTIONS, RULES, VERDICT_LABELS, decide
from app.guards import VALUE_TEXT

RULES_BY_ID = {r.id: r for r in RULES}
OUT_OF_SCOPE = decide(False, None)

# Short chip labels on the canvas; the meaning (guards.VALUE_TEXT) goes in the text version.
CHIP_LABELS = {
    "in_scope": {"yes": "Yes", "no": "No"},
    "gmp_relevance": {"critical": "Critical", "non_critical": "Non-critical", "not_gmp": "Not GMP", "unclear": "Unclear"},
    "model_type": {"static": "Frozen trained model", "dynamic": "Self-learning", "generative": "Generative AI / LLM",
                   "probabilistic": "Probabilistic", "non_ml": "Not ML", "unclear": "Unclear"},
    "autonomy": {"informs": "Informs", "recommends": "A person approves each output",
                 "acts_with_oversight": "Acts, people monitor", "acts_autonomously": "Acts, nobody checks", "unclear": "Unclear"},
}
SCOPE_TEXT = {"yes": "the text proposes a concrete AI use", "no": "a question or request, not a concrete AI use"}

NODE_TEXT = {
    "in_scope": ("Concrete AI use?", "First, the AI judges whether the text proposes a concrete AI use. A general "
                                     "question or a request for advice is not assessed."),
    "gmp_relevance": ("GMP relevance", QUESTIONS["gmp_relevance"]),
    "model_type": ("Model type", QUESTIONS["model_type"]),
    "autonomy": ("Autonomy", QUESTIONS["autonomy"] + " It changes the outcome only on this branch: generative AI in "
                                                     "non-critical use."),
}


def _node(id_: str, field: str, branches: list) -> dict:
    return {"id": id_, "field": field, "branches": branches}


def _leaf(rule_id: str) -> dict:
    return {"rule": rule_id}


# The decision tree, in the order of app/rules.py RULES (first match wins). Each branch lists the classes
# that lead to the same place. Checked against decide() for every combination (tests/test_how_it_works.py).
TREE = _node("scope", "in_scope", [
    (["no"], _leaf("R0-out-of-scope")),
    (["yes"], _node("gmp", "gmp_relevance", [
        (["critical"], _node("model-crit", "model_type", [
            (["static"], _leaf("R5-critical-static")),
            (["dynamic", "generative", "probabilistic"], _leaf("R2-critical-nonstatic")),
            (["non_ml"], _leaf("R4-non-ml")),
            (["unclear"], _leaf("R3-unclear")),
        ])),
        (["non_critical"], _node("model-noncrit", "model_type", [
            (["static", "dynamic", "probabilistic"], _leaf("R9-noncritical-ml")),
            (["generative"], _node("autonomy", "autonomy", [
                (["informs", "recommends"], _leaf("R8-genai-hitl")),
                (["acts_with_oversight", "acts_autonomously"], _leaf("R6-genai-no-hitl")),
                (["unclear"], _leaf("R7-genai-autonomy-unclear")),
            ])),
            (["non_ml"], _leaf("R4-non-ml")),
            (["unclear"], _leaf("R3-unclear")),
        ])),
        (["not_gmp"], _leaf("R1-outside-gmp")),
        (["unclear"], _leaf("R3-unclear")),
    ])),
])

# Example paths: the chip that ends each one, and the classification it stands for (tested against decide()).
PRESETS = [
    {"name": "LLM drafts SOPs, QA approves", "chip": "autonomy-recommends",
     "cls": {"gmp_relevance": "non_critical", "model_type": "generative", "autonomy": "recommends"}},
    {"name": "LLM decides batch release", "chip": "model-crit-generative",
     "cls": {"gmp_relevance": "critical", "model_type": "generative", "autonomy": "acts_autonomously"}},
    {"name": "Vision model rejects vials", "chip": "model-crit-static",
     "cls": {"gmp_relevance": "critical", "model_type": "static", "autonomy": "acts_with_oversight"}},
]

# Small source tags on the leaves: "Annex 22 §1". The full document name goes in the (i).
TAG_DOC = {"A22": "Annex 22", "A11": "Annex 11", "A11D": "Annex 11 draft", "CH4D": "Chapter 4 draft", "Q9": "ICH Q9",
           "AIA": "AI Act", "FDA-CRED": "FDA credibility", "FDA-DP": "FDA paper", "FDA-WL": "FDA warning letter"}


def _section(section: str) -> str:
    if re.fullmatch(r"[0-9][0-9.]*", section):
        return f"§{section}"
    if m := re.fullmatch(r"art-(\d+)", section):
        return f"Art. {m.group(1)}"
    if section in ("principle", "glossary"):
        return section.capitalize()
    return ""  # e.g. the warning letter's "ai-use" passage: the document name says enough


def source_tags(sources) -> list[dict]:
    out = []
    for doc, section in sources:
        sec = _section(section)
        short = SOURCES_BY_ID[doc].short if doc in SOURCES_BY_ID else doc
        out.append({"tag": " ".join(filter(None, [TAG_DOC.get(doc, doc), sec])),
                    "detail": " ".join(filter(None, [short, sec]))})
    return out


def _first_sentence(text: str) -> str:
    return re.split(r"(?<=[.])\s+(?=[A-Z])", text.strip(), maxsplit=1)[0]


def verdict_tone(verdict: str) -> str:
    from app.main import _verdict_tone  # the tone the result page uses

    return _verdict_tone(verdict)


def _leaf_view(rule_id: str) -> dict:
    if rule_id == OUT_OF_SCOPE.rule_id:
        verdict, explanation, sources = OUT_OF_SCOPE.verdict, OUT_OF_SCOPE.explanation, OUT_OF_SCOPE.sources
        # "It does not answer general questions ... To screen a specific AI use, describe ..."
        why = re.split(r"(?<=[.])\s+(?=[A-Z])", explanation.strip(), maxsplit=1)[-1]
    else:
        rule = RULES_BY_ID[rule_id]
        verdict, explanation, sources = rule.verdict, rule.explanation, rule.sources
        why = _first_sentence(explanation)
    label = VERDICT_LABELS[verdict]
    head, _, tail = label.partition(": ")
    if verdict == "needs_more_information":
        why += f" The proposer answers the questions and resubmits, up to {MAX_ROUNDS} rounds."
    return {"rule": rule_id, "rule_short": rule_id.split("-", 1)[0], "verdict": verdict, "label": label,
            "head": head, "tail": tail, "tone": verdict_tone(verdict), "why": why, "tags": source_tags(sources)}


def build() -> dict:
    """The page data: nodes, chips and leaves (with grid positions) in DOM order, plus the JSON for the script."""
    nodes, chips, leaves, items = {}, {}, {}, []
    leaf_count = [0]

    def count(n: dict) -> int:
        return sum(1 if "rule" in t else count(t) for _, t in n["branches"])

    def add_leaf(rule_id: str, row: int, parent_chips: list[str]) -> str:
        leaf_count[0] += 1
        lid = f"leaf-{leaf_count[0]}"
        leaves[lid] = {"id": lid, **_leaf_view(rule_id)}
        items.append({"kind": "leaf", "col": 7, "row": row, "span": 1, **leaves[lid]})
        return lid

    def add_node(n: dict, col: int, row: int, span: int, path: list[str]) -> None:
        title, info = NODE_TEXT[n["field"]]
        nodes[n["id"]] = {"id": n["id"], "field": n["field"], "title": title, "info": info, "path": path,
                          "branches": [], "chips": []}
        items.append({"kind": "node", "col": col, "row": row, "span": span, **nodes[n["id"]]})

    def add_group(n: dict, values: list[str], col: int, row: int, span: int, path: list[str], down: bool = False):
        ids = [f"{n['id']}-{v}" for v in values]
        group = {"kind": "group", "col": col, "row": row, "span": span, "down": down, "chips": []}
        items.append(group)
        for v, cid in zip(values, ids):
            chips[cid] = {"id": cid, "node": n["id"], "value": v, "label": CHIP_LABELS[n["field"]][v],
                          "meaning": SCOPE_TEXT[v] if n["field"] == "in_scope" else VALUE_TEXT.get(v, "not stated in the proposal"),
                          "path": path + [cid], "to": None}
            group["chips"].append(chips[cid])
            nodes[n["id"]]["chips"].append(cid)  # display order (the JSON for the page has sorted keys)
        return ids

    def place(n: dict, depth: int, row: int, path: list[str]) -> None:
        add_node(n, 1 + 2 * depth, row, count(n), path)
        r = row
        for values, target in n["branches"]:
            span = 1 if "rule" in target else count(target)
            ids = add_group(n, values, 2 + 2 * depth, r, span, path)
            if "rule" in target:
                to = add_leaf(target["rule"], r, ids)
            else:
                place(target, depth + 1, r, path + [ids[0]])  # the subtree's path runs through its first chip
                to = target["id"]
                for extra in ids[1:]:  # (never happens today: a node is reached by one class)
                    chips[extra]["path"] = path + [extra]
            for cid in ids:
                chips[cid]["to"] = to
            nodes[n["id"]]["branches"].append({"values": values, "to": to})
            r += span

    # The scope gate sits above the tree: "No" runs right to "Not assessed", "Yes" runs down into GMP relevance.
    gate = TREE
    no_values, no_leaf = gate["branches"][0]
    yes_values, gmp = gate["branches"][1]
    add_node(gate, 1, 1, 1, [])
    no_ids = add_group(gate, no_values, 2, 1, 1, [])
    no_to = add_leaf(no_leaf["rule"], 1, no_ids)
    chips[no_ids[0]]["to"] = no_to
    yes_ids = add_group(gate, yes_values, 1, 2, 1, [], down=True)
    chips[yes_ids[0]]["to"] = gmp["id"]
    nodes["scope"]["branches"] = [{"values": no_values, "to": no_to}, {"values": yes_values, "to": gmp["id"]}]
    place(gmp, 0, 3, yes_ids)

    # The node a chip lives in, for drawing the connector into it; the chip path ends at the chip itself.
    data = {"root": "scope", "nodes": nodes, "chips": chips, "leaves": leaves,
            "presets": [{"name": p["name"], "chip": p["chip"]} for p in PRESETS]}
    rows = 2 + count(gmp)
    return {"items": items, "data": data, "rows": rows, "tree": _text_tree(TREE, chips, leaves, nodes)}


def _text_tree(n: dict, chips: dict, leaves: dict, nodes: dict) -> dict:
    """The same tree for the nested text list (screen readers, no JavaScript)."""
    node = nodes[n["id"]]
    out = {"title": node["title"], "branches": []}
    for values, target in n["branches"]:
        labels = [chips[f"{n['id']}-{v}"] for v in values]
        if "rule" in target:
            to = leaves[chips[f"{n['id']}-{values[0]}"]["to"]]
            out["branches"].append({"chips": labels, "leaf": to})
        else:
            out["branches"].append({"chips": labels, "node": _text_tree(target, chips, leaves, nodes)})
    return out


def flow() -> list[dict]:
    """The process flow (app/pipeline.py run_assessment), with counts read from the code."""
    return [
        {"icon": "clipboard-text", "label": "Intake form", "sub": f"{len(FORM_QUESTIONS)} questions",
         "info": f"The proposer answers {len(FORM_QUESTIONS)} questions about the task, its output and who checks it. "
                 "Only the task description is required."},
        {"icon": "file-search", "label": "Find passages", "sub": f"{len(SOURCES)} public documents",
         "info": f"Hybrid search (keywords plus meaning, fused) finds the relevant passages in {len(SOURCES)} public "
                 "regulatory documents. Fixed queries make sure the deciding passages are always included."},
        {"icon": "list-check", "label": "AI classifies", "sub": "3 axes, each cited",
         "info": "The AI labels GMP relevance, model type and autonomy, and cites a source for each answer, only from "
                 "an approved list per class. Output that fails the format check is rejected and logged, never shown. "
                 "A text that is not a concrete AI use is Not assessed."},
        {"icon": "books", "label": "Citation check", "sub": "Unsupported dropped",
         "info": "Each citation must be a passage that was actually found and that the approved list allows for that "
                 "class. Other citations are dropped; an answer left without a source is flagged as not covered."},
        {"icon": "scale", "label": "Rules decide", "sub": f"{len(RULES)} fixed rules", "key": True,
         "info": f"{len(RULES)} fixed rules, checked in order (the first match wins), turn the three classes into one "
                 "outcome. QA can read them line by line. The tree below shows every path."},
        {"icon": "shield-check", "label": "Safety checks", "sub": "Only stricter",
         "info": "They can only make the outcome stricter. A review step that is not described is not assumed. Form "
                 "answers that contradict the description are explained and asked about."},
        {"icon": "user-check", "label": "Result", "sub": "Outcome, controls, questions",
         "info": "The outcome with its source, the required controls, open questions and a draft intake record. "
                 "QA decides."},
    ]


LOOP_INFO = (f"Pending clarification: the proposer answers the questions and resubmits. Up to {MAX_ROUNDS} rounds, "
             "the first submission included; after that, a new proposal with a clearer scope.")
AUDIT = {"icon": "file-text", "label": "Audit log", "sub": "Hash-chained",
         "info": "Every request, including rejected model output, is appended to the audit log. Each entry stores the "
                 "hash of the one before, so editing or deleting a line breaks the chain."}
