"""Source manifest: every document in the knowledge base, where it comes from and how to parse it.

Public documents only (see CLAUDE.md data policy). Parser strategies:
- "numbered": sections follow the document's own numbering (1, 2.1, 4.12 ...). Used for EC and ICH texts.
- "headings": an explicit, ordered list of heading patterns. Used where numbering is irregular (FDA texts).
- "articles": "Article N" blocks, filtered to a chosen set. Used for the EU AI Act.
"""
from __future__ import annotations

from dataclasses import dataclass, field

EC = "https://health.ec.europa.eu"


@dataclass(frozen=True)
class Heading:
    section: str  # stable section id used in citations, e.g. "IV.A.3"
    title: str  # human-readable title
    pattern: str  # regex matched against a (joined) line


@dataclass(frozen=True)
class Source:
    doc_id: str
    title: str
    short: str
    status: str  # "draft" | "in force" | "final" | "discussion paper" | "enforcement"
    date: str
    url: str
    filename: str
    parser: str
    start_page: int = 0  # 0-based; skip cover and table of contents
    end_pattern: str | None = None  # stop parsing at the first line matching this
    start_pattern: str | None = None  # start parsing at the first line matching this
    named_headings: tuple[Heading, ...] = ()  # extra unnumbered headings ("numbered" parser)
    headings: tuple[Heading, ...] = ()  # "headings" parser
    articles: tuple[int, ...] = ()  # "articles" parser
    annexes: tuple[str, ...] = ()  # "articles" parser: annexes to keep, e.g. ("III",)
    drop_patterns: tuple[str, ...] = field(default_factory=tuple)  # page headers/footers
    max_top_level: int | None = None  # numbered parser: higher top-level numbers are list items, not sections


SOURCES: tuple[Source, ...] = (
    Source(
        doc_id="A22",
        title="EU GMP Annex 22: Artificial Intelligence (draft for consultation)",
        short="Annex 22 (draft)",
        status="draft",
        date="2025-07-07",
        url=f"{EC}/document/download/5f38a92d-bb8e-4264-8898-ea076e926db6_en?filename=mp_vol4_chap4_annex22_consultation_guideline_en.pdf",
        filename="annex22_draft_2025.pdf",
        parser="numbered",
        start_page=1,
        named_headings=(Heading("glossary", "Glossary", r"^Glossary$"),),
    ),
    Source(
        doc_id="A11",
        title="EU GMP Annex 11: Computerised Systems (2011, in force)",
        short="Annex 11 (2011)",
        status="in force",
        date="2011-06-30",
        url=f"{EC}/system/files/2016-11/annex11_01-2011_en_0.pdf",
        filename="annex11_2011.pdf",
        parser="numbered",
        start_page=1,
        named_headings=(
            Heading("principle", "Principle", r"^Principle$"),
            Heading("glossary", "Glossary", r"^Glossary$"),
        ),
        drop_patterns=(
            r"^Commission Européenne", r"^B-1049 Brussel", r"^Telephone: \(32-2\)",
            r"^General$", r"^Project Phase$", r"^Operational Phase$",
        ),
    ),
    Source(
        doc_id="A11D",
        title="EU GMP Annex 11: Computerised Systems (draft revision for consultation)",
        short="Annex 11 (draft)",
        status="draft",
        date="2025-07-07",
        url=f"{EC}/document/download/40231f18-e564-4043-94de-c031f813d38b_en?filename=mp_vol4_chap4_annex11_consultation_guideline_en.pdf",
        filename="annex11_draft_2025.pdf",
        parser="numbered",
        start_page=1,
        named_headings=(
            Heading("introduction", "Introduction", r"^Introduction$"),
            Heading("glossary", "Glossary", r"^Glossary$"),
        ),
    ),
    Source(
        doc_id="CH4D",
        title="EU GMP Chapter 4: Documentation (draft revision for consultation)",
        short="Chapter 4 (draft)",
        status="draft",
        date="2025-07-07",
        url=f"{EC}/document/download/fa336a6e-753b-46fc-b53b-9178bacd8878_en?filename=mp_vol4_chap4_consultation_guideline_en.pdf",
        filename="chapter4_draft_2025.pdf",
        parser="numbered",
        start_page=1,
        named_headings=(Heading("glossary", "Glossary", r"^GLOSSARY$"),),
    ),
    Source(
        doc_id="Q9",
        title="ICH Q9(R1) Quality Risk Management",
        short="ICH Q9(R1)",
        status="final",
        date="2023-01-18",
        url="https://database.ich.org/sites/default/files/ICH_Q9%28R1%29_Guideline_Step4_2022_1219.pdf",
        filename="ich_q9r1.pdf",
        parser="numbered",
        start_page=4,
        max_top_level=8,  # the reference list after section 8 is numbered 1..25
        named_headings=(
            Heading("annex-I", "Annex I: Methods and Tools", r"^ANNEX I[:.]"),
            Heading("annex-II", "Annex II: Potential Applications", r"^ANNEX II[:.]"),
            Heading("I.{n}", "Annex I.{n}", r"^I\.(\d{1,2})\b"),
            Heading("II.{n}", "Annex II.{n}", r"^II\.(\d{1,2})\b"),
        ),
        drop_patterns=(r"^ICH Q9\(R1\) Guideline$",),
    ),
    Source(
        doc_id="AIA",
        title="EU Artificial Intelligence Act, Regulation (EU) 2024/1689 (selected articles)",
        short="EU AI Act",
        status="in force",
        date="2024-07-12",
        url="https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401689",
        filename="eu_ai_act_2024_1689.pdf",
        parser="articles",
        articles=(1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 26, 50),
        annexes=("III",),  # list of high-risk use areas (e.g. employment), referenced by Art. 6(2)
        drop_patterns=(r"^EN$", r"^OJ L, ", r"^ELI: ", r"^\d+/144$", r"^CHAPTER [IVX]+$", r"^SECTION \d+$"),
    ),
    Source(
        doc_id="FDA-CRED",
        title="FDA draft guidance: Considerations for the Use of AI to Support Regulatory Decision-Making for Drug and Biological Products",
        short="FDA AI credibility guidance (draft)",
        status="draft",
        date="2025-01-07",
        url="https://www.fda.gov/media/184830/download",
        filename="fda_ai_regulatory_decision_2025.pdf",
        parser="headings",
        start_page=3,
        drop_patterns=(r"^Contains Nonbinding Recommendations$", r"^Draft — Not for Implementation$"),
        headings=(
            Heading("I", "Introduction", r"^I\. INTRODUCTION"),
            Heading("II", "Scope", r"^II\. SCOPE"),
            Heading("III", "Background", r"^III\. BACKGROUND"),
            Heading("IV", "Considerations for AI use in the drug product life cycle", r"^IV\. CONSIDERATIONS FOR AI USE"),
            Heading("IV.A", "A risk-based credibility assessment framework", r"^A\. A Risk-Based Credibility Assessment Framework"),
            Heading("IV.A.1", "Step 1: Define the question of interest", r"^1\. Step 1:"),
            Heading("IV.A.2", "Step 2: Define the context of use for the AI model", r"^2\. Step 2:"),
            Heading("IV.A.3", "Step 3: Assess the AI model risk", r"^3\. Step 3:"),
            Heading("IV.A.4", "Step 4: Develop a plan to establish AI model credibility", r"^4\. Step 4:"),
            Heading("IV.A.4.a", "Describe the model and the model development process", r"^a\. Describe the model and the model development process"),
            Heading("IV.A.4.b", "Describe the model evaluation process", r"^b\. Describe the model evaluation process"),
            Heading("IV.A.5", "Step 5: Execute the plan", r"^5\. Step 5:"),
            Heading("IV.A.6", "Step 6: Document the results of the credibility assessment plan", r"^6\. Step 6:"),
            Heading("IV.A.7", "Step 7: Determine the adequacy of the AI model for the context of use", r"^7\. Step 7:"),
            Heading("IV.B", "Special consideration: life cycle maintenance of the credibility of AI model outputs", r"^B\. Special Consideration"),
            Heading("IV.C", "Early engagement", r"^C\. Early Engagement"),
        ),
    ),
    Source(
        doc_id="FDA-DP",
        title="FDA discussion paper: Artificial Intelligence in Drug Manufacturing",
        short="FDA AI in manufacturing (2023 paper)",
        status="discussion paper",
        date="2023-03-01",
        url="https://www.fda.gov/media/165743/download",
        filename="fda_ai_drug_manufacturing_2023.pdf",
        parser="headings",
        start_page=1,
        end_pattern=r"^Appendix A: Related Guidance",
        drop_patterns=(r"^Discussion Paper: Artificial Intelligence in Drug Manufacturing$",),
        headings=(
            Heading("introduction", "Introduction", r"^Introduction$"),
            Heading("scope", "Scope", r"^Scope$"),
            Heading("background", "Background", r"^Background$"),
            Heading("terminology", "Terminology", r"^Terminology$"),
            Heading("areas", "Areas of consideration associated with AI", r"^Areas of Consideration Associated with AI"),
            Heading("area-1", "Cloud applications may affect oversight of pharmaceutical manufacturing data and records", r"^1\. Cloud applications"),
            # The PDF draws the first line of this heading as an image; anchor on its second line.
            Heading("area-2", "The Internet of Things (IoT) may increase the amount of data generated during drug manufacturing", r"^manufacturing, affecting existing data management practices"),
            Heading("area-3", "Applicants may need clarity about whether and how the application of AI is subject to regulatory oversight", r"^3\. Applicants may need clarity"),
            Heading("area-4", "Applicants may need standards for developing and validating AI models", r"^4\. Applicants may need standards"),
            Heading("area-5", "Continuously learning AI systems that adapt to real-time data may challenge regulatory assessment and oversight", r"^5\. Continuously learning"),
            Heading("questions", "AI questions and feedback", r"^AI Questions & Feedback Section"),
            Heading("conclusion", "Conclusion", r"^Conclusion$"),
        ),
    ),
    Source(
        doc_id="FDA-WL",
        title="FDA Warning Letter 320-26-58 (Purolea Cosmetics Lab), 2 April 2026, with a section on inappropriate use of AI in pharmaceutical manufacturing",
        short="FDA warning letter 320-26-58",
        status="enforcement",
        date="2026-04-02",
        url="https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/purolea-cosmetics-lab-722591-04022026",
        filename="fda_warning_letter_purolea_2026.txt",
        parser="headings",
        start_pattern=r"^The United States Food and Drug Administration \(FDA\) inspected",
        end_pattern=r"^Owner’s Responsibilities",
        headings=(
            Heading("intro", "Inspection and summary of violations", r"^The United States Food and Drug Administration \(FDA\) inspected"),
            Heading("insanitary", "Insanitary conditions", r"^Insanitary Conditions$"),
            Heading("violation-1", "Violation 1: microbiological testing of each batch (21 CFR 211.165(b))", r"^1\. Your firm failed to conduct"),
            Heading("violation-2", "Violation 2: component testing (21 CFR 211.84)", r"^2\. Your firm failed to test"),
            Heading("violation-3", "Violation 3: quality unit responsibilities (21 CFR 211.22)", r"^3\. Your firm’s quality control unit"),
            Heading("ai-use", "Inappropriate use of artificial intelligence in pharmaceutical manufacturing", r"^Inappropriate Use of Artificial Intelligence"),
            Heading("production-ceased", "Drug production ceased", r"^Drug Production Ceased$"),
        ),
    ),
)

SOURCES_BY_ID = {s.doc_id: s for s in SOURCES}
