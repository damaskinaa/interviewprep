# Methodology Coverage Ledger

This ledger tracks whether the local NMT workbench preserves, operationalizes, and tests the original Next Move Theory core plus the Anastasia/team/book enhancement layer.

Status values:

- `ENFORCED`: Required by active harness/output contract/prompt/template and covered by static tests.
- `PARTIAL`: Source exists and some enforcement exists, but not complete for all run types.
- `SOURCE_ONLY`: Source exists but active workbench does not yet force it.
- `MISSING`: Not present locally.
- `UNAVAILABLE_SOURCE`: Source is explicitly unavailable or paywalled locally and must not be invented.

## Core NMT Concepts

| Concept | Source category | Source file(s) | Current enforcement location(s) | Enforcement type | Status | Required fix if not enforced |
|---|---|---|---|---|---|---|
| Next Move Theory as an integrative operating system | ORIGINAL_NMT_CORE | `docs/nmt/_source_library/agnostic_methodology/NMT_CANON_FULL_EXTRACTION.md` | `METHODOLOGY_PRESERVATION_CONTRACT.md`, `CODEX_NMT_HARNESS_ADVANCED.md`, `OUTPUT_CONTRACT.md`, `10_AGNOSTIC_ADVANCED_NMT_RESEARCH.txt`, `tests/test_nmt_methodology_coverage_static.py` | required analysis pass, output section, prompt requirement, test | ENFORCED | None |
| Advanced Jobs To Be Done / Advanced JTBD / AJTBD | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, harnesses, templates, agnostic prompt, tests | required analysis pass, template requirement, prompt requirement, test | ENFORCED | None |
| Job as unit of analysis | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, business/interview templates, agnostic prompt, tests | required analysis pass, output section, template requirement, test | ENFORCED | None |
| Big Job / Core Job / Small Jobs / Micro Jobs | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, templates, agnostic prompt, tests | required analysis pass, template requirement, prompt requirement, test | ENFORCED | None |
| Job structure | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, interview template, business input template, tests | required analysis pass, output section, template requirement, test | ENFORCED | None |
| Job Graph | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, harnesses, output contract, templates, agnostic prompt, tests | required analysis pass, output section, prompt requirement, test | ENFORCED | None |
| Critical Chain of Jobs | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, harnesses, templates, agnostic prompt, tests | required analysis pass, template requirement, prompt requirement, test | ENFORCED | None |
| Job-based segmentation | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, no-carryover protocol, run manifest template, agnostic prompt, tests | gate, template requirement, prompt requirement, test | ENFORCED | None |
| Map of Segments | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, harnesses, output contract, agnostic prompt, tests | required analysis pass, output section, prompt requirement, test | ENFORCED | None |
| Segment + Job as one analytical entity | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, harnesses, validation gate, agnostic prompt, tests | required analysis pass, gate, test | ENFORCED | None |
| Value creation | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, templates, agnostic prompt, tests | required analysis pass, output section, template requirement, test | ENFORCED | None |
| Value-creation mechanics | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, validation sprint template, agnostic prompt, tests | required analysis pass, prompt requirement, test | ENFORCED | Full 100+ catalog remains `UNAVAILABLE_SOURCE`; use public foundational subset only |
| Aha Moment | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, templates, agnostic prompt, tests | required analysis pass, template requirement, test | ENFORCED | None |
| Barriers | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, templates, agnostic prompt, tests | required analysis pass, template requirement, test | ENFORCED | None |
| Fears | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, templates, agnostic prompt, tests | required analysis pass, template requirement, test | ENFORCED | None |
| Habit / existing behavior | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, templates, agnostic prompt, tests | required analysis pass, template requirement, test | ENFORCED | None |
| Tax Jobs / friction / cost | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, business input template, validation sprint template, agnostic prompt, tests | required analysis pass, template requirement, test | ENFORCED | None |
| Behavior change and switching logic | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, templates, agnostic prompt, tests | required analysis pass, output section, prompt requirement, test | ENFORCED | None |
| Consideration set | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, missing-information checklist, templates, agnostic prompt, tests | required output section, template requirement, test | ENFORCED | None |
| Alternatives and current solutions | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, templates, agnostic prompt, tests | required analysis pass, template requirement, test | ENFORCED | None |
| Consideration Activators | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, agnostic prompt, tests | required analysis pass, output section, test | ENFORCED | None |
| RAT / RIT | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md`, `VALIDATION_GATE.md` | Preservation contract, harnesses, validation gate, validation sprint template, agnostic prompt, tests | required analysis pass, gate, template requirement, test | ENFORCED | None |
| Assumption stack | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, validation sprint template, agnostic prompt, tests | required analysis pass, output section, test | ENFORCED | None |
| Cheapest credible evidence against deadliest assumption | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md`, `VALIDATION_GATE.md` | Preservation contract, output contract, validation gate, agnostic prompt, tests | gate, required output section, test | ENFORCED | None |
| ABCDX Segmentation | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, agnostic prompt, tests | required analysis pass where applicable, test | ENFORCED | Must mark `NOT_APPLICABLE` when no customers/users/revenue exist |
| Unit Economics | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, business input template, agnostic prompt, tests | required analysis pass where applicable, test | ENFORCED | Full unit-economics integration remains `UNAVAILABLE_SOURCE`; use public gates only |
| Theory of Constraints / binding constraint | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, validation sprint template, agnostic prompt, tests | required analysis pass, gate, test | ENFORCED | None |
| Subtraction as a meta-operator | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md`, `VALIDATION_GATE.md` | Preservation contract, harnesses, validation gate, templates, agnostic prompt, tests | required analysis pass, gate, test | ENFORCED | None |
| Focus / company attention management | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, agnostic prompt, tests | required analysis pass, output section, test | ENFORCED | None |
| Local optimum vs global optimum | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, agnostic prompt, tests | required analysis pass, output section, test | ENFORCED | None |
| Main algorithm / cyclical next-move logic | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, run lifecycle, agnostic prompt, tests | required analysis pass, lifecycle gate, test | ENFORCED | None |
| Cause-and-effect chain to profit | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, output contract, agnostic prompt, tests | required analysis pass, output section, test | ENFORCED | None |
| Field validation gates | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md`, `VALIDATION_GATE.md` | Preservation contract, validation gate, templates, agnostic prompt, tests | gate, template requirement, test | ENFORCED | None |
| Product diagnosis for existing products | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, run lifecycle, agnostic prompt, tests | required analysis pass where source supports, prompt requirement, test | PARTIAL | Full product-diagnosis algorithm is `UNAVAILABLE_SOURCE`; use public diagnostic chain and mark limits |
| Producer-skill pipeline: nmt-chat / ask-nmt equivalent, nmt-diagnose, nmt-market-research, nmt-craft-value-proposition, nmt-product-requirements, nmt-craft-go-to-market, nmt-analyze-interviews | ORIGINAL_NMT_CORE | `NMT_CANON_FULL_EXTRACTION.md`, local skill metadata | Preservation contract, agnostic prompt, tests | prompt requirement, test | ENFORCED | None |

## Enhancement Layer Concepts

| Concept | Source category | Source file(s) | Current enforcement location(s) | Enforcement type | Status | Required fix if not enforced |
|---|---|---|---|---|---|---|
| Strong evidence hierarchy | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `pasted_feedback.md`, `METHODOLOGY_FEEDBACK_SUMMARY.md` | Claim tagging schema, harnesses, output contract, tests | gate, output section, test | ENFORCED | None |
| Claim tagging | HARNESS_LOOP_ENFORCEMENT | `CLAIM_TAGGING_SCHEMA.md` | Harnesses, output contract, templates, tests | output section, test | ENFORCED | None |
| Prior docs are DOC CLAIM unless verified | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `pasted_feedback.md`, `CHATGPT_TRANSFER_SYNTHESIS.md` | Harnesses, project source template, no-carryover protocol, tests | gate, template requirement, test | ENFORCED | None |
| No-carryover protocol | HARNESS_LOOP_ENFORCEMENT | `NO_CARRYOVER_PROTOCOL.md` | Harnesses, run manifest template, new idea prompts, tests | gate, template requirement, test | ENFORCED | None |
| Project isolation | HARNESS_LOOP_ENFORCEMENT | `NO_CARRYOVER_PROTOCOL.md` | Harnesses, run manifest template, new idea prompts, tests | gate, template requirement, test | ENFORCED | None |
| Repo/source-first evidence where repo exists | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `pasted_feedback.md`, `CHATGPT_TRANSFER_SYNTHESIS.md` | Harnesses, run lifecycle, agnostic prompt, tests | gate, prompt requirement, test | ENFORCED | None |
| Validation debt | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `pasted_feedback.md`, `VALIDATION_GATE.md` | Harnesses, output contract, templates, prompts, tests | output section, gate, test | ENFORCED | None |
| Analysis integrity loop: First pass, Self critique, Evidence check, Missing information list, Final recommendation | HARNESS_LOOP_ENFORCEMENT | `CODEX_NMT_HARNESS_ADVANCED.md`, `OUTPUT_CONTRACT.md` | Harnesses, templates, prompts, tests | required analysis pass, test | ENFORCED | None |
| Missing-information checklist / Missing information discipline | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `pasted_feedback.md`, `CHATGPT_TRANSFER_SYNTHESIS.md` | Harnesses, templates, prompts, tests | output section, template requirement, test | ENFORCED | None |
| Payment evidence vs stated interest | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `pasted_feedback.md`, `CLAIM_TAGGING_SCHEMA.md` | Harnesses, templates, prompts, tests | output section, test | ENFORCED | None |
| Non-buyer and non-user evidence | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `pasted_feedback.md` | Harnesses, templates, prompts, tests | output section, test | ENFORCED | None |
| Field evidence before product claims | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `pasted_feedback.md`, `VALIDATION_GATE.md` | Harnesses, output contract, agnostic prompt, tests | gate, test | ENFORCED | None |
| GO means validation, not build / GO means go to validation | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `CHATGPT_TRANSFER_SYNTHESIS.md`, `VALIDATION_GATE.md` | Harnesses, validation gate, prompts, tests | gate, test | ENFORCED | None |
| Cheapest credible real-world test before build | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `VALIDATION_GATE.md` | Harnesses, output contract, validation gate, agnostic prompt, tests | gate, output section, test | ENFORCED | None |
| Subtraction before addition | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `VALIDATION_GATE.md`, `NMT_CANON_FULL_EXTRACTION.md` | Harnesses, validation gate, templates, tests | gate, test | ENFORCED | None |
| No generic startup checklisting | ANASTASIA_TEAM_BOOK_ENHANCEMENT | User instruction, preservation contract | Preservation contract, agnostic prompt, tests | anti-simplification rule, test | ENFORCED | None |
| No feature-first analysis | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, agnostic prompt, tests | anti-simplification rule, test | ENFORCED | None |
| No demographic/ICP-only segmentation | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `NMT_CANON_FULL_EXTRACTION.md` | Preservation contract, run manifest template, agnostic prompt, tests | anti-simplification rule, test | ENFORCED | None |
| No broad market-size claim as demand proof | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `VALIDATION_GATE.md`, preservation contract | Preservation contract, agnostic prompt, tests | anti-simplification rule, test | ENFORCED | None |
| No user opinion treated as payment evidence | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `pasted_feedback.md`, claim tagging schema | Preservation contract, templates, agnostic prompt, tests | anti-simplification rule, test | ENFORCED | None |
| BLOCKED / PROCEED by category | HARNESS_LOOP_ENFORCEMENT | `VALIDATION_GATE.md` | Preservation contract, output contract, agnostic prompt, tests | output section, gate, test | ENFORCED | None |
| False-positive risk | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `pasted_feedback.md` | Preservation contract, output contract, agnostic prompt, tests | output section, test | ENFORCED | None |
| What would kill this idea/product | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `VALIDATION_GATE.md`, preservation contract | Preservation contract, agnostic prompt, tests | output section, test | ENFORCED | None |
| What not to build | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `VALIDATION_GATE.md`, preservation contract | Preservation contract, templates, agnostic prompt, tests | output section, test | ENFORCED | None |
| Product-state distinction: new idea, existing product, live product with weak validation, paid product, scale-stage product, dying product | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `NMT_CANON_FULL_EXTRACTION.md`, preservation contract | Preservation contract, agnostic prompt, tests | required analysis pass, prompt requirement, test | ENFORCED | None |
| Controlled concierge validation vs self-serve launch | ANASTASIA_TEAM_BOOK_ENHANCEMENT | `VALIDATION_GATE.md`, preservation contract | Preservation contract, agnostic prompt, tests | gate, prompt requirement, test | ENFORCED | None |
| Agnostic reuse for any business | HARNESS_LOOP_ENFORCEMENT | `NO_CARRYOVER_PROTOCOL.md` | Harnesses, start-here doc, new idea prompts, agnostic prompt, tests | gate, test | ENFORCED | None |

## Unavailable Source Ledger

| Methodology area | Source category | Source file(s) | Enforcement location(s) | Enforcement type | Status | Required handling |
|---|---|---|---|---|---|---|
| Full 100+ value-creation mechanics catalog | UNAVAILABLE_SOURCE | `NMT_CANON_FULL_EXTRACTION.md` public/paywalled boundary | Preservation contract, agnostic prompt, tests | unavailable-source marker, test | UNAVAILABLE_SOURCE | Do not invent; use foundational public subset |
| Product-diagnosis algorithm | UNAVAILABLE_SOURCE | `NMT_CANON_FULL_EXTRACTION.md` public/paywalled boundary | Preservation contract, agnostic prompt, tests | unavailable-source marker, test | UNAVAILABLE_SOURCE | Use public diagnostic chain; mark limits |
| Per-question algorithms | UNAVAILABLE_SOURCE | `NMT_CANON_FULL_EXTRACTION.md` public/paywalled boundary | Preservation contract, agnostic prompt, tests | unavailable-source marker, test | UNAVAILABLE_SOURCE | Do not invent step-by-step proprietary algorithms |
| Product/feature idea generation | UNAVAILABLE_SOURCE | `NMT_CANON_FULL_EXTRACTION.md` public/paywalled boundary | Preservation contract, agnostic prompt, tests | unavailable-source marker, test | UNAVAILABLE_SOURCE | Use public algorithm only |
| Goal-setting/growth-point algorithm | UNAVAILABLE_SOURCE | `NMT_CANON_FULL_EXTRACTION.md` public/paywalled boundary | Preservation contract, agnostic prompt, tests | unavailable-source marker, test | UNAVAILABLE_SOURCE | Use public goal-challenge principles only |
| Demand creation/acquisition-channel delivery detail | UNAVAILABLE_SOURCE | `NMT_CANON_FULL_EXTRACTION.md` public/paywalled boundary | Preservation contract, agnostic prompt, tests | unavailable-source marker, test | UNAVAILABLE_SOURCE | Mark as unavailable if deep operational detail is required |
| Branding on Jobs | UNAVAILABLE_SOURCE | `NMT_CANON_FULL_EXTRACTION.md` public/paywalled boundary | Preservation contract, tests | unavailable-source marker, test | UNAVAILABLE_SOURCE | Do not invent |
| Company rollout process | UNAVAILABLE_SOURCE | `NMT_CANON_FULL_EXTRACTION.md` public/paywalled boundary | Preservation contract, tests | unavailable-source marker, test | UNAVAILABLE_SOURCE | Do not invent |
| Customer Success and Support built on Jobs | UNAVAILABLE_SOURCE | `NMT_CANON_FULL_EXTRACTION.md` public/paywalled boundary | Preservation contract, tests | unavailable-source marker, test | UNAVAILABLE_SOURCE | Do not invent |
| Full unit-economics integration | UNAVAILABLE_SOURCE | `NMT_CANON_FULL_EXTRACTION.md` public/paywalled boundary | Preservation contract, agnostic prompt, tests | unavailable-source marker, test | UNAVAILABLE_SOURCE | Use public UE gates only |
