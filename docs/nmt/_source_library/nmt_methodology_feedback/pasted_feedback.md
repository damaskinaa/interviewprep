# Pasted NMT Methodology Feedback

This file summarizes methodology feedback provided by the user in this Codex run. Treat every item as `DOC CLAIM` until supported by field data, product behavior, tests, payment evidence, or a reliable external source.

## 1. Non Technical User Barrier

- `DOC CLAIM`: Some users see the methodology as valuable but are blocked by GitHub, English-language materials, technical setup, and the lack of a step-by-step path.
- `DOC CLAIM`: These users want a workshop-style walkthrough that explains what GitHub is, where to download things, what to install, which skill to run, what output to expect, and what to do next.

## 2. Workshop Demand

- `DOC CLAIM`: At least one user explicitly said they would pay for a guided workshop that turns the methodology into a concrete result for their own product.
- `HYPOTHESIS`: Workshop demand may be a stronger onboarding path than self-serve setup for non-technical users.

## 3. Codex Compatibility

- `DOC CLAIM`: The newer NMT setup supports Codex-style commands using `$nmt...`.
- `DOC CLAIM`: Slash commands are not the correct mental model for Codex.
- `HYPOTHESIS`: NMT onboarding should explain the command difference by environment so users do not copy Claude-style slash commands into Codex.

## 4. Harness Definition

- `DOC CLAIM`: A harness is the agent wrapper around the model.
- `DOC CLAIM`: The harness gives the model tools, runs the loop, manages context, permissions, modes, limits, and tool execution.
- `DOC CLAIM`: The methodology should not rely on one prompt only.
- `DOC CLAIM`: The methodology needs a controlled loop.

## 5. Install And Distribution Feedback

- `DOC CLAIM`: Install friction should be reduced.
- `DOC CLAIM`: Possible `npx` skills distribution was raised as a distribution direction.
- `DOC CLAIM`: Copying the canon into every project should be avoided if possible.
- `DOC CLAIM`: Updates should be easier.
- `HYPOTHESIS`: Lower-friction installation and update paths may increase adoption more than adding more methodology content.

## 6. Interview Analysis Feedback

- `DOC CLAIM`: `nmt analyze interviews` was praised when it extracted Core Jobs, success criteria, personas, alternatives, consideration set, existing solutions, problems, and value hypotheses.
- `HYPOTHESIS`: Interview analysis output is most useful when it converts raw interview material into structured, reusable product evidence.

## 7. Missing Evidence Standard

- `DOC CLAIM`: Strong analysis must explicitly say what the data does not show.
- `DOC CLAIM`: Missing evidence should include missing consideration set, missing near-purchase barriers, missing price threshold, unclear first Aha, and missing respondent types.
- `HYPOTHESIS`: Making absent evidence visible prevents polished reports from overstating confidence.

## 8. Product Diagnosis Feedback

- `DOC CLAIM`: Live product diagnosis should inspect existing repo documents, reviews, surveys, tests, and state before asking questions from zero.
- `HYPOTHESIS`: Repo-first diagnosis reduces repeated intake burden and prevents avoidable questions.

## 9. Output Quality Rule

- `DOC CLAIM`: Outputs must separate evidence from hypotheses.
- `DOC CLAIM`: A report based on guesses can look as polished as a report based on interviews unless validation debt is visible.
- `HYPOTHESIS`: Visible validation debt is a required quality signal, not an optional appendix.

## 10. Implication For This Codex Workbench

- `DOC CLAIM`: Every Codex run should use a run manifest, source-tagged claims, validation debt, a block-or-proceed gate, harness audit, tests before patches, and no carryover of old business ideas unless explicitly listed in the current run manifest.
- `HYPOTHESIS`: The workbench should make validation state harder to lose than polished prose is to produce.
