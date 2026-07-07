# Codex NMT Harness Advanced

## Purpose

This harness governs Codex work for Next Move Theory and Advanced Jobs To Be Done runs.

It is reusable across business ideas.

It must not contain NailIt assumptions as permanent rules.

The original Next Move Theory Canon and Skills are the core. This workbench may preserve, operationalize, strengthen, and test that core, but it must not replace it, shrink it, simplify it into generic startup validation, or make NailIt the methodology.

## Core separation

1. Reusable methodology lives in these folders:

   docs/nmt/_source_library/agnostic_methodology/
   docs/nmt/_source_library/claude_harness_docs/
   docs/nmt/_source_library/validation_gate/
   docs/nmt/_source_library/nmt_methodology_feedback/

2. Project specific sources live only in:

   docs/nmt/_source_library/projects/{project_name}/

3. Run specific outputs live only in:

   docs/nmt/runs/{date}_{project_name}_{run_type}/

## No carryover rule

No source, segment, pricing, channel, moat, validation conclusion, customer assumption, product assumption, market size, competitor claim, or previous business idea may carry from one run into another unless the receiving RUN_MANIFEST.md explicitly imports it as DOC CLAIM context.

Future business ideas must create their own:

1. docs/nmt/_source_library/projects/{project_name}/
2. docs/nmt/runs/{date}_{project_name}_{run_type}/

No NailIt source, segment, pricing, market size, channel, moat, validation conclusion, customer assumption, product assumption, or founder evidence may carry into a future run unless that future RUN_MANIFEST.md explicitly imports it as DOC CLAIM context.

## Required run gate

Every run must have:

1. RUN_MANIFEST.md
2. Business input
3. Source index
4. Evidence ledger
5. Run state
6. Output contract
7. Validation gate

If any is missing, Codex must stop and create or request it before diagnosis.

Every serious run must also read:

1. docs/nmt/_harness/METHODOLOGY_PRESERVATION_CONTRACT.md
2. docs/nmt/_harness/METHODOLOGY_COVERAGE_LEDGER.md

If either file is missing, Codex must stop and create or request it before product diagnosis, market research, strategy, validation planning, value proposition work, PRD work, or go-to-market work.

## Source labels

Every material claim must be tagged as one of:

1. REPO FACT
2. TESTED
3. FIELD DATA
4. PAYMENT EVIDENCE
5. EXTERNAL SOURCE
6. DOC CLAIM
7. STRONG INFERENCE
8. HYPOTHESIS
9. MODEL INFERENCE
10. STORY RISK
11. NO EVIDENCE

## Output contract

Every serious output must start with:

1. Validation Debt
2. Fatal if wrong
3. Cheapest real world test
4. Block or proceed

Every serious diagnosis, research, interview analysis, validation analysis, or readiness output must use this analysis integrity loop:

1. First pass
2. Self critique
3. Evidence check
4. Missing information list
5. Final answer

The model may not skip directly from first pass to final answer.

## Required NMT methodology passes

Every serious NMT diagnosis, research, interview analysis, validation analysis, readiness output, strategy output, value proposition output, PRD handoff, or go-to-market output must include these passes unless explicitly marked `UNAVAILABLE_SOURCE` or `NOT_APPLICABLE` with a reason:

1. Source inventory
2. Source classification
3. Evidence extraction
4. Original NMT core preservation check
5. Enhancement-layer preservation check
6. Advanced JTBD pass
7. Job structure pass
8. Job Graph / Critical Chain pass
9. Segment + Job pass
10. Map of Segments pass when more than one segment is in scope
11. Value creation / value mechanics pass
12. Aha Moment pass
13. Barriers / fears / habit / Tax Jobs pass where applicable
14. Behavior change / switching pass
15. Consideration set / alternatives / current solutions pass
16. Consideration Activators pass where communication, sales, conversion, or adoption is in scope
17. RAT/RIT and assumption stack pass
18. ABCDX pass where there are customers, users, revenue, churn, retention, satisfaction, support load, or margin data
19. Unit Economics pass where pricing, revenue, cost, margin, CAC, LTV, payback, or willingness-to-pay evidence exists
20. Theory of Constraints / binding constraint pass
21. Subtraction pass
22. Focus / company attention management pass
23. Local vs global optimum pass
24. Main algorithm / cyclical next-move pass
25. Cause-and-effect chain to profit pass
26. Field validation gate
27. Validation debt
28. Self critique
29. Evidence check
30. Missing-information checklist
31. Final recommendation
32. BLOCKED / PROCEED by category
33. Preservation check: nothing from the original core or enhancement layer was removed, weakened, or silently skipped

Methodology words are not coverage by themselves. Each applicable concept must appear as a real analysis pass, output section, gate, template requirement, prompt requirement, or test.

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

Every output must end with:

1. Evidence used
2. What was not checked
3. What would change the conclusion
4. Next lowest cost action
5. BLOCKED or PROCEED

## GO meaning

GO means go to validation.

GO never means go to build.

Market size never proves demand. User opinion never proves payment evidence. Segmentation must not be demographic, ICP, role-title, or industry-only without Job Graph and success criteria. Value must not be reduced to features.

## Edit discipline

1. Read only diagnosis before edits.
2. Harness audit before patches.
3. Root cause investigation before tests.
4. Tests before production code.
5. Narrow patches only.
6. No production code edits during business diagnosis.
7. No broad market research before repo diagnosis for existing products.
8. No voice, marketplace, model provider, paid infrastructure, or broad scope expansion unless the current run manifest explicitly allows it.

## Four truth loops

1. Product truth loop

   Can the product work locally, in repo, with tests and realistic data?

2. Research truth loop

   What segment, Job, success criteria, assumptions, alternatives, consideration set, and willingness to pay are actually supported?

3. Field truth loop

   Do real users care, pay, trust, complete, return, refer, or contribute?

4. Application truth loop

   What can be honestly claimed in an accelerator, investor, grant, sales, or public story?

## Fresh run protocol for a new idea

For a new business idea, Codex must start by reading only:

1. This harness
2. Templates
3. Agnostic methodology
4. Validation gate
5. The new project folder
6. The new run manifest

Codex must not read NailIt sources unless the new run manifest explicitly imports them.

NailIt is a project. NailIt is not the methodology.

Unavailable or paywalled methodology areas must be marked `UNAVAILABLE_SOURCE`; Codex must not invent missing proprietary algorithms, the full 100+ mechanics catalog, or full unit-economics integration.

## Stop conditions

Codex must stop if:

1. It cannot confirm the actual product repo.
2. It cannot find a run manifest.
3. It is about to treat a document claim as truth.
4. It is about to use NailIt context in a different project without explicit import.
5. It is about to patch production code before tests.
6. It is about to make market, pricing, moat, or demand claims without source labels.
7. It is about to hide validation debt.
