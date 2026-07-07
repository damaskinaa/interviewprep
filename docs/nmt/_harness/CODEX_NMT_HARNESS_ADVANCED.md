# Codex NMT Harness Advanced

## Purpose

This harness governs Codex work for Next Move Theory and Advanced Jobs To Be Done runs.

It is reusable across business ideas.

It must not contain NailIt assumptions as permanent rules.

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

## Stop conditions

Codex must stop if:

1. It cannot confirm the actual product repo.
2. It cannot find a run manifest.
3. It is about to treat a document claim as truth.
4. It is about to use NailIt context in a different project without explicit import.
5. It is about to patch production code before tests.
6. It is about to make market, pricing, moat, or demand claims without source labels.
7. It is about to hide validation debt.
