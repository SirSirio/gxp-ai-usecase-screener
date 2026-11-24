"""Controls catalogue: what a use case must put in place, and the exact passages that require it.

Each control lists (doc_id, section) references. They are resolved against the index at runtime,
so a control can only cite a section that really exists in the corpus (tested in test_controls.py).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControlDef:
    id: str
    title: str
    what: str
    refs: tuple[tuple[str, str], ...]
    # Words that steer which sentence of each referenced section is quoted (as Rule.quote_hint in app/rules.py).
    # Empty: `what` steers it. Set where rewording `what` (plain-language pass, 2026-11-24) moved the quote.
    quote_hint: str = ""


CONTROLS: dict[str, ControlDef] = {c.id: c for c in (
    # ---- Annex 22 lifecycle (critical, static models) ----
    ControlDef("INTENDED_USE", "Intended use and input sample space",
               "Describe the task, the input data with common and rare variations, subgroups and known limitations. A process SME approves this description before acceptance testing begins.",
               (("A22", "3.1"), ("A22", "3.2")),
               quote_hint="Describe the task, the input data with common and rare variations, subgroups and known limitations. A process SME approves it before acceptance testing."),
    ControlDef("ACCEPTANCE", "Test metrics and acceptance criteria",
               "Define case-dependent metrics (such as confusion matrix, sensitivity and specificity) and acceptance criteria approved by an SME, with performance at least as good as the process it replaces.",
               (("A22", "4.1"), ("A22", "4.2"), ("A22", "4.3"))),
    ControlDef("TEST_DATA", "Representative, correctly labelled test data",
               "Ensure test data covers the full sample space and subgroups, is large enough for statistical confidence and has independently verified labels. Do not use generative-AI-generated test data without justification.",
               (("A22", "5.1"), ("A22", "5.3"), ("A22", "5.6"))),
    ControlDef("TEST_INDEPENDENCE", "Test-data independence",
               "Put technical and procedural controls in place so test data is never used in training or validation. Apply access control and an audit trail to the test set.",
               (("A22", "6.1"), ("A22", "6.2"), ("A22", "6.5"))),
    ControlDef("TEST_PLAN", "Approved test plan and documented execution",
               "Have an approved test plan before testing begins. Document and justify any deviations, and retain test documentation as GMP documentation.",
               (("A22", "7.2"), ("A22", "7.3"), ("A22", "7.4"))),
    ControlDef("EXPLAINABILITY", "Explainability and feature review",
               "Record which features drove each classification during testing (using methods such as SHAP, LIME or heat maps) and review them when approving the results.",
               (("A22", "8.1"), ("A22", "8.2"))),
    ControlDef("CONFIDENCE", "Confidence scores and 'undecided' threshold",
               "Log a confidence score for each prediction during testing (§9.1). Set an operational threshold below which the outcome is flagged as 'undecided' (§9.2).",
               (("A22", "9.1"), ("A22", "9.2"))),
    ControlDef("CHANGE_CONTROL_AI", "Change and configuration control of the model",
               "Place the tested model, its system and the process under change and configuration control. Evaluate every change to determine if retesting is needed, and detect any unauthorised changes.",
               (("A22", "10.1"), ("A22", "10.2"))),
    ControlDef("MONITORING", "Performance and input-drift monitoring",
               "Monitor model performance and check whether inputs stay within the tested sample space using defined drift metrics.",
               (("A22", "10.3"), ("A22", "10.4"))),
    ControlDef("HUMAN_REVIEW", "Human-in-the-loop responsibilities and records",
               "Where a human makes decisions based on model input and testing was reduced, define the operator's responsibility. Monitor operator performance and keep review records.",
               (("A22", "3.3"), ("A22", "10.5"))),
    # ---- generative AI in non-critical GMP use ----
    ControlDef("HITL_GENAI", "Trained, qualified staff responsible for every output",
               "Ensure personnel with adequate qualification and training check that each output is suitable for its intended use before it is used.",
               (("A22", "1"),)),
    ControlDef("QU_REVIEW", "Quality-unit review of AI-generated GMP content",
               "An authorised quality-unit representative reviews and clears any AI-drafted procedures, specifications or records before use. Do not rely on the AI to identify regulatory requirements.",
               (("FDA-WL", "ai-use"), ("FDA-WL", "violation-3")),
               quote_hint="AI-drafted procedures, specifications or records are reviewed and cleared by an authorised quality-unit representative before use; the AI is not relied on to identify regulatory requirements."),
    ControlDef("PQS_ACCOUNTABILITY", "AI use inside the pharmaceutical quality system",
               "Include the AI support within the PQS, whether on premise or hosted. The regulated user remains accountable for the integrity of records produced with AI.",
               (("CH4D", "4.24"), ("CH4D", "4.25"))),
    # ---- general computerised-system controls ----
    ControlDef("RISK_ASSESSMENT", "Documented quality risk assessment",
               "Use a justified, documented risk assessment to set the extent of validation and data-integrity controls, keeping formality proportional to risk.",
               (("A11", "1"), ("Q9", "4.3"), ("Q9", "5.1")),
               quote_hint="A justified, documented risk assessment sets the extent of validation and data-integrity controls; formality proportional to risk."),
    ControlDef("CSV", "Computerised system validation",
               "Validate the application and qualify the infrastructure, scaling the effort to risk. Keep the system in a validated state throughout its lifecycle.",
               (("A11", "4"), ("A11D", "2.1"), ("A11D", "9"))),
    ControlDef("AUDIT_TRAIL", "Audit trail",
               "Record GMP-relevant user interactions, including the creation, change and deletion of data with the user, time and reason (Annex 11). This tool's recommendation for AI systems is to also log inputs, model and prompt versions and outputs.",
               (("A11", "9"), ("A11D", "12"))),
    ControlDef("CHANGE_CONTROL", "Change and configuration management",
               "Make changes to the system (including the model, prompt or configuration) in a controlled manner under a defined procedure.",
               (("A11", "10"), ("A11D", "3.1"))),
    ControlDef("PERSONNEL", "Roles, qualification and training",
               "Define responsibilities and provide adequate training for everyone using or maintaining the system. Ensure AI literacy for staff who use AI.",
               (("A22", "2.1"), ("A11D", "5.2"), ("AIA", "art-4"))),
    ControlDef("SUPPLIER", "Supplier and service-provider oversight",
               "Maintain formal agreements, supplier audits and ongoing oversight, and review supplier documentation for externally provided models. For hosted AI services, agree on how new model versions are released and whether you can test them before release.",
               (("A11", "3"), ("A22", "2.2"), ("A11D", "7.2"), ("A11D", "7.5"))),
    ControlDef("DATA_INTEGRITY", "Data integrity (ALCOA+)",
               "Data that the system captures, processes or reports must be trustworthy (ALCOA+). Assess data criticality using QRM. The regulated user remains accountable for records produced with AI.",
               (("A11D", "2.4"), ("A11D", "4.5"), ("CH4D", "4.24"))),
    ControlDef("SECURITY", "Information security and confidentiality",
               "Use an information security management system to protect data and systems. Check where prompts and documents (such as client data) go when using a hosted AI service.",
               (("A11D", "15.1"),)),
    ControlDef("PERIODIC_REVIEW", "Periodic review",
               "Review the system periodically after go-live to verify that it remains in a validated state and fit for its intended use.",
               (("A11D", "14.1"), ("A11", "11"))),
    ControlDef("DATA_GOVERNANCE", "Training and input data governance",
               "Apply data governance across the data lifecycle based on data criticality and data risk, covering the data used to train and feed the model.",
               (("CH4D", "4.13"), ("A11D", "2.4"))),
    ControlDef("DYNAMIC_LIFECYCLE", "Lifecycle oversight of a continuously learning model",
               "Define how model updates are monitored, evaluated and controlled. FDA's 2023 discussion paper (non-binding) flags continuous learning as a challenge for oversight, and Annex 22 §10 change control and monitoring practices can be adapted for this.",
               (("FDA-DP", "area-5"), ("A11D", "3.1"), ("A22", "10.1"))),
    ControlDef("FDA_CREDIBILITY", "US products: FDA credibility assessment",
               "For products under FDA oversight, model outputs that support regulatory decisions (including actions taken under CGMP, per the draft guidance's scope) call for FDA's risk-based credibility framework. This covers the question of interest, context of use, model risk (influence × consequence) and credibility plan.",
               (("FDA-CRED", "IV.A"), ("FDA-CRED", "IV.A.3"))),
    ControlDef("AI_ACT", "EU AI Act screening",
               "Check whether the system is high-risk (Art. 6, Annex III, such as AI used in recruitment or worker management) and, if so, meet the deployer duties of Art. 26. Ensure AI literacy for staff (Art. 4). Transparency duties (Art. 50) fall mainly on the provider. As the deployer, check that they are met.",
               (("AIA", "art-6"), ("AIA", "annex-III"), ("AIA", "art-26"), ("AIA", "art-4"), ("AIA", "art-50"))),
    ControlDef("REDESIGN", "Redesign before any GMP-critical use",
               "Under the draft Annex 22, this model type should not be used in a critical GMP application. Your options are to restrict its use to non-critical support with a human in the loop, or to use a static, deterministic model tested under Annex 22.",
               (("A22", "1"),)),
)}

ANNEX22_LIFECYCLE = (
    "INTENDED_USE", "ACCEPTANCE", "TEST_DATA", "TEST_INDEPENDENCE", "TEST_PLAN",
    "EXPLAINABILITY", "CONFIDENCE", "CHANGE_CONTROL_AI", "MONITORING",
)
