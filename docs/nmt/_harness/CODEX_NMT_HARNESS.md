# Codex NMT Workbench Harness

This reusable harness governs Codex workbench runs that use Next Move Theory (NMT) or Advanced Jobs To Be Done (AJTBD) reasoning.

It is intentionally product-agnostic. Business-specific context belongs only in a run folder under `docs/nmt/runs/`.

The original Next Move Theory Canon and Skills are the core. The local workbench may operationalize and enforce that core, but must not replace it with generic startup validation, NailIt-specific assumptions, or a simplified checklist.

## Core Rules

1. Repo truth before document claims. Inspect the repository before making claims about product state, code, tests, docs, behavior, or validation.
2. Validation debt on every output. Every output must state what remains unvalidated.
3. GO means GO to validation, never build approval. A GO verdict authorizes only the next cheapest evidence-gathering step.
4. Read-only diagnosis before edits. Read existing docs, tests, harnesses, state, evidence, and relevant code before changing files.
5. Harness audit before patches. Read this harness and the active run state before editing.
6. Root cause investigation before tests. State the suspected upstream cause before adding or running tests.
7. Tests before production code. If production code changes are needed, add or identify the relevant test first.
8. Narrow patches only. Change the smallest set of files needed for the current validated objective.
9. No voice. Do not add voice interaction, voice output, speech synthesis, speech recognition, or voice-agent behavior.
10. No marketplace. Do not add marketplace, listing, transaction, seller, buyer, payment, or marketplace-discovery features.
11. No model provider change. Do not switch, add, or abstract model providers unless explicitly approved after validation.
12. No paid infrastructure. Do not add paid services, subscriptions, external hosting, paid APIs, or managed infrastructure.
13. No broad market research before repo diagnosis. Diagnose repository evidence and product state before external market scans.
14. Source-tagged claims. Label every consequential claim as `REPO FACT`, `TESTED`, `FIELD DATA`, `PAYMENT EVIDENCE`, `EXTERNAL SOURCE`, `DOC CLAIM`, `STRONG INFERENCE`, `HYPOTHESIS`, `MODEL INFERENCE`, `STORY RISK`, or `NO EVIDENCE`.
15. Subtraction before addition. Prefer removing scope, assumptions, or steps before adding features, docs, systems, or process.
16. Block or proceed decision after every stage. Each stage must end with `PROCEED` or `BLOCKED`, plus the reason.
17. New business idea, new run folder. Every future business idea must get a separate dated run folder.
18. No carryover by default. No previous business idea, segment, price, channel, moat, or conclusion may carry over unless the active `RUN_MANIFEST.md` explicitly allows it.
19. Prior research is context only. Treat prior research as DOC CLAIM unless verified by repo behavior, tests, field evidence, payment, or reliable external source.
20. Stop on missing app code. Stop if a run requires product-repo work and the repository is empty or does not contain the actual app code for the active product.
21. Preserve the original NMT core. Serious runs must use `docs/nmt/_harness/METHODOLOGY_PRESERVATION_CONTRACT.md` and `docs/nmt/_harness/METHODOLOGY_COVERAGE_LEDGER.md`.
22. Methodology words are not coverage. Core concepts must be used as analysis passes, output sections, gates, templates, prompts, or tests.
23. Mark unavailable methodology. If local sources do not provide an algorithm or full catalog, mark `UNAVAILABLE_SOURCE` and do not invent it.

## Required Output Header

Every run output must start with these sections, in this order:

1. `Validation Debt`
2. `Fatal If Wrong`
3. `Cheapest Real World Test`
4. `Block Or Proceed`

## Analysis Integrity Loop

Every serious diagnosis, research, interview analysis, validation analysis, or readiness output must use this analysis integrity loop:

1. First pass
2. Self critique
3. Evidence check
4. Missing information list
5. Final answer

The model may not skip directly from first pass to final answer.

## Required NMT Methodology Passes

Every serious NMT run must explicitly perform or mark `NOT_APPLICABLE` / `UNAVAILABLE_SOURCE` for:

1. Source inventory
2. Source classification
3. Evidence extraction
4. Original NMT core preservation check
5. Enhancement-layer preservation check
6. Advanced JTBD
7. Job as unit of analysis and full Job structure
8. Big Job / Core Job / Small Jobs / Micro Jobs where applicable
9. Job Graph and Critical Chain of Jobs
10. Segment + Job as one analytical entity
11. Map of Segments when multiple segments exist
12. Value creation and value-creation mechanics
13. Aha Moment
14. Barriers, fears, habit, existing behavior, and Tax Jobs where applicable
15. Behavior change and switching logic
16. Consideration set, alternatives, current solutions, and Consideration Activators
17. RAT/RIT, assumption stack, and cheapest credible evidence against the deadliest assumption
18. ABCDX where customer/revenue data exists
19. Unit Economics where pricing/revenue/cost evidence exists
20. Theory of Constraints / binding constraint
21. Subtraction before addition
22. Focus / company attention management
23. Local optimum vs global optimum
24. Main algorithm / cyclical next-move logic
25. Cause-and-effect chain to profit
26. Field validation gate
27. BLOCKED / PROCEED by category

Anti-simplification gates:

1. GO means validation, not build approval.
2. Market size is not demand proof.
3. User opinion is not payment evidence.
4. Segmentation is not demographics or ICP alone.
5. Value is not features.
6. NailIt is a project, not the methodology.

## Missing Information Checklist

Every interview, validation, customer, market, or readiness analysis must explicitly check:

1. What we still do not know
2. Missing respondent types
3. Missing non-buyer evidence
4. Missing consideration set
5. Missing near-purchase barriers
6. Missing price threshold
7. Unclear first Aha moment
8. Whether alternatives were explored
9. Whether willingness to pay is behavior or opinion
10. Whether payment evidence exists
11. Whether stated interest is separated from observed behavior
12. What evidence would change the conclusion

## Required Output Footer

Every run output must end with these sections, in this order:

1. `Evidence Used`
2. `What Was Not Checked`
3. `What Would Change The Conclusion`
4. `Next Lowest Cost Action`
5. `BLOCKED` or `PROCEED`

## Stage Gate

Use this loop for every stage:

1. Read the active `RUN_MANIFEST.md`.
2. Read the active `state/NMT_RUN_STATE.md`.
3. Read the active `state/EVIDENCE_LEDGER.md`.
4. Check whether the repository contains the actual product app code needed for the stage.
5. Tag all claims.
6. Identify validation debt and fatal assumptions.
7. Look for subtraction before addition.
8. Decide `PROCEED` or `BLOCKED`.

## Patch Gate

Before editing files, confirm:

- The edit is allowed by the active run manifest.
- The target file is necessary for the current stage.
- The change is not production code unless a test already exists or is added first.
- The change does not introduce voice, marketplace, model-provider, or paid-infrastructure scope.
- The change is traceable to a source-tagged claim.
- The active run state and evidence ledger will remain accurate after the patch.

## Workbench Layout

- `_harness/`: reusable Codex NMT rules.
- `_templates/`: reusable run/input/output templates.
- `_source_library/`: manually supplied source material, grouped by origin.
- `runs/`: dated, business-specific run folders.

## Stop Conditions

Stop and ask for direction when:

- The active run manifest is missing.
- The requested work would rely on untagged claims.
- The requested work requires product app code and the repository does not contain it.
- The requested work requires production code changes before tests.
- The requested work introduces forbidden scope.
- The requested work treats GO as build approval.
- The requested work carries over prior conclusions without explicit manifest permission.
