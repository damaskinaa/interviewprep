import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NMT_ROOT = REPO_ROOT / "docs" / "nmt"


def read_text(relative_path):
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def lower(text):
    return text.lower()


def assert_terms(text, terms):
    missing = [term for term in terms if lower(term) not in lower(text)]
    assert not missing, f"Missing required terms: {missing}"


def load_terms():
    return json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "nmt_required_methodology_terms.json").read_text(
            encoding="utf-8"
        )
    )


def operational_docs_text():
    paths = [
        "docs/nmt/_harness/METHODOLOGY_PRESERVATION_CONTRACT.md",
        "docs/nmt/_harness/METHODOLOGY_COVERAGE_LEDGER.md",
        "docs/nmt/_harness/CODEX_NMT_HARNESS_ADVANCED.md",
        "docs/nmt/_harness/CODEX_NMT_HARNESS.md",
        "docs/nmt/_harness/OUTPUT_CONTRACT.md",
        "docs/nmt/_templates/RUN_MANIFEST_TEMPLATE.md",
        "docs/nmt/_templates/BUSINESS_INPUT_TEMPLATE.md",
        "docs/nmt/_templates/INTERVIEW_ANALYSIS_TEMPLATE.md",
        "docs/nmt/_templates/VALIDATION_SPRINT_TEMPLATE.md",
        "docs/nmt/codex_prompts/10_AGNOSTIC_ADVANCED_NMT_RESEARCH.txt",
    ]
    return "\n".join(read_text(path) for path in paths)


def test_preservation_contract_exists_and_names_original_nmt_core():
    contract = read_text("docs/nmt/_harness/METHODOLOGY_PRESERVATION_CONTRACT.md")
    required = [
        "Original NMT Core Concepts",
        "Next Move Theory as an integrative operating system",
        "Advanced Jobs To Be Done",
        "Job as the unit of analysis",
        "Job Graph",
        "Critical Chain of Jobs",
        "Value-creation mechanics",
        "Riskiest Assumption Test",
        "ABCDX Segmentation",
        "Unit Economics",
        "Theory of Constraints",
        "Subtraction as a meta-operator",
        "Local optimum vs global optimum",
        "Cause-and-effect chain to profit",
    ]
    assert_terms(contract, required)


def test_preservation_contract_names_enhancement_layer():
    contract = read_text("docs/nmt/_harness/METHODOLOGY_PRESERVATION_CONTRACT.md")
    required = [
        "Anastasia / Team / Book Enhancement Concepts",
        "Strong evidence hierarchy",
        "Claim tagging",
        "Prior docs are DOC CLAIM unless verified",
        "No-carryover protocol",
        "Project isolation",
        "Validation debt",
        "First pass / self critique / evidence check / missing information / final recommendation loop",
        "Payment evidence vs stated interest",
        "Non-buyer and non-user evidence",
        "GO means go to validation, not build approval",
        "No generic startup checklisting",
        "No feature-first analysis",
        "No demographic/ICP-only segmentation",
        "No broad market-size claim as demand proof",
        "No user opinion treated as payment evidence",
        "Explicit false-positive risk",
        "Explicit what not to build",
        "Separate controlled concierge validation from self-serve launch",
    ]
    assert_terms(contract, required)


def test_coverage_ledger_exists_and_includes_all_required_concepts():
    terms = load_terms()
    ledger = read_text("docs/nmt/_harness/METHODOLOGY_COVERAGE_LEDGER.md")
    assert_terms(ledger, terms["core_concepts"])
    assert_terms(ledger, terms["enhancement_concepts"])
    assert_terms(ledger, terms["unavailable_source_terms"])
    assert "UNAVAILABLE_SOURCE" in ledger
    assert "ENFORCED" in ledger


def test_advanced_harness_requires_serious_run_methodology_passes():
    harness = read_text("docs/nmt/_harness/CODEX_NMT_HARNESS_ADVANCED.md")
    required = [
        "Required NMT methodology passes",
        "Source inventory",
        "Source classification",
        "Evidence extraction",
        "Original NMT core preservation check",
        "Enhancement-layer preservation check",
        "Advanced JTBD pass",
        "Job Graph / Critical Chain pass",
        "Segment + Job pass",
        "Value creation / value mechanics pass",
        "Behavior change / switching pass",
        "RAT/RIT and assumption stack pass",
        "ABCDX pass",
        "Unit Economics pass",
        "Theory of Constraints / binding constraint pass",
        "Subtraction pass",
        "Local vs global optimum pass",
        "Field validation gate",
        "BLOCKED / PROCEED by category",
    ]
    assert_terms(harness, required)


def test_output_contract_requires_analysis_integrity_loop_and_methodology_sections():
    contract = read_text("docs/nmt/_harness/OUTPUT_CONTRACT.md")
    required = [
        "First pass",
        "Self critique",
        "Evidence check",
        "Missing information list",
        "Final answer",
        "Required Methodology Coverage",
        "Job as unit of analysis",
        "Job Graph",
        "Critical Chain of Jobs",
        "Value creation and value-creation mechanics",
        "RAT/RIT",
        "Unit Economics",
        "Theory of Constraints",
        "Local optimum vs global optimum",
        "False-positive risk",
        "What would kill this idea or product",
        "What not to build",
    ]
    assert_terms(contract, required)


def test_agnostic_advanced_prompt_exists_and_is_not_nailit_specific():
    prompt = read_text("docs/nmt/codex_prompts/10_AGNOSTIC_ADVANCED_NMT_RESEARCH.txt")
    assert "Run an agnostic advanced Next Move Theory" in prompt
    assert "Do not default to NailIt" in prompt
    assert "NailIt validation readiness" not in prompt
    assert "2026_07_07_nailit_validation_readiness" not in prompt
    assert "docs/nmt/_source_library/projects/nailit unless" in prompt


def test_agnostic_advanced_prompt_operationalizes_core_methodology():
    prompt = read_text("docs/nmt/codex_prompts/10_AGNOSTIC_ADVANCED_NMT_RESEARCH.txt")
    required = [
        "Source-first evidence extraction",
        "Original NMT core preservation check",
        "Anastasia/team/book enhancement-layer preservation check",
        "Advanced JTBD",
        "Job as unit of analysis",
        "Big Job / Core Job / Small Jobs / Micro Jobs",
        "Job Graph",
        "Critical Chain of Jobs",
        "Segment + Job as one analytical entity",
        "Value creation",
        "Value-creation mechanics",
        "Behavior change and switching logic",
        "Consideration set",
        "Alternatives and current solutions",
        "RAT/RIT",
        "ABCDX",
        "Unit Economics",
        "Theory of Constraints",
        "Subtraction before addition",
        "Local optimum vs global optimum",
        "Field validation gates",
        "Non-buyer / non-user evidence",
        "Payment evidence",
        "False-positive risk",
        "What not to build",
        "BLOCKED / PROCEED by category",
    ]
    assert_terms(prompt, required)


def test_operational_documents_reject_dangerous_simplifications():
    text = operational_docs_text()
    required = [
        "GO means validation",
        "GO means go to validation",
        "GO never means go to build",
        "market size never proves demand",
        "market size is not demand proof",
        "user opinion never proves payment evidence",
        "user opinion is not payment evidence",
        "demographic/ICP-only",
        "demographics or ICP alone",
        "Value is not features",
        "feature-first analysis",
        "generic startup validation",
        "NailIt is a project",
        "NailIt is not the methodology",
    ]
    assert_terms(text, required)


def test_templates_force_methodology_operational_sections():
    text = "\n".join(
        read_text(path)
        for path in [
            "docs/nmt/_templates/RUN_MANIFEST_TEMPLATE.md",
            "docs/nmt/_templates/BUSINESS_INPUT_TEMPLATE.md",
            "docs/nmt/_templates/INTERVIEW_ANALYSIS_TEMPLATE.md",
            "docs/nmt/_templates/VALIDATION_SPRINT_TEMPLATE.md",
        ]
    )
    required = [
        "Advanced JTBD",
        "Job Graph",
        "Critical Chain of Jobs",
        "value-creation mechanics",
        "RAT/RIT",
        "ABCDX",
        "Unit Economics",
        "Theory of Constraints",
        "Subtraction",
        "Local optimum",
        "global optimum",
        "Behavior change",
        "Consideration set",
        "Payment evidence",
        "Non-buyer",
        "Validation Debt",
        "Field validation gate",
        "What not to build",
    ]
    assert_terms(text, required)


def test_unavailable_methodology_is_marked_not_invented():
    contract = read_text("docs/nmt/_harness/METHODOLOGY_PRESERVATION_CONTRACT.md")
    prompt = read_text("docs/nmt/codex_prompts/10_AGNOSTIC_ADVANCED_NMT_RESEARCH.txt")
    combined = f"{contract}\n{prompt}"
    required = [
        "UNAVAILABLE_SOURCE",
        "Do not invent",
        "Do not pretend coverage exists",
        "Full 100+ value-creation mechanics catalog",
        "Product-diagnosis algorithm",
        "Full unit-economics integration",
    ]
    assert_terms(combined, required)


def test_methodology_enforcement_uses_operational_docs_not_source_library_only():
    operational_text = operational_docs_text()
    source_library_text = read_text(
        "docs/nmt/_source_library/agnostic_methodology/NMT_CANON_FULL_EXTRACTION.md"
    )
    required_operational_terms = [
        "Required NMT methodology passes",
        "Methodology Preservation Contract",
        "Methodology Coverage Ledger",
        "10_AGNOSTIC_ADVANCED_NMT_RESEARCH",
        "tests/test_nmt_methodology_coverage_static.py",
    ]
    assert_terms(operational_text, required_operational_terms)
    assert "Next Move Theory" in source_library_text
