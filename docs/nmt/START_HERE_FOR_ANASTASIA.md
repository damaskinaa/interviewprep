# Start Here For Anastasia

## What this workbench is

This is a reusable NMT workbench for Codex. It keeps methodology, project sources, run state, evidence labels, and prompts separated so Codex does not mix assumptions between business ideas.

## Where reusable methodology lives

Reusable methodology lives in:

1. docs/nmt/_harness/
2. docs/nmt/_templates/
3. docs/nmt/_source_library/agnostic_methodology/
4. docs/nmt/_source_library/claude_harness_docs/
5. docs/nmt/_source_library/validation_gate/
6. docs/nmt/_source_library/nmt_methodology_feedback/

## Where NailIt lives

NailIt project sources live in:

1. docs/nmt/_source_library/projects/nailit/prior_research/
2. docs/nmt/_source_library/projects/nailit/new_frontiers/

The NailIt validation readiness run lives in:

docs/nmt/runs/2026_07_07_nailit_validation_readiness/

Backend primary repo path: /Users/asia/interview-agent
Frontend related repo path: /Users/asia/interview-frontend

## How to start a future project without NailIt carryover

1. Use docs/nmt/codex_prompts/09_NEW_IDEA_STARTER.txt.
2. Give Codex the new project name and run type.
3. Codex must create:
   - docs/nmt/_source_library/projects/{project_name}/
   - docs/nmt/runs/{date}_{project_name}_{run_type}/
4. Codex must not read NailIt sources unless the new RUN_MANIFEST.md explicitly imports NailIt as DOC CLAIM analogy context.

## How to start NailIt diagnosis later

Use docs/nmt/codex_prompts/03_NAILIT_DIAGNOSIS.txt only after docs/nmt/WORKBENCH_READY_STATUS.md says READY.

That diagnosis must be read only. Backend is the primary diagnosis repo. Frontend may be inspected read only only when frontend/backend contract evidence is needed.

## What not to run yet

Do not run product diagnosis until you intentionally start the NailIt diagnosis prompt.
Do not run market research before repo diagnosis for an existing product.
Do not ask Codex to modify production code during business diagnosis.
Treat prior research only as DOC CLAIM until stronger evidence verifies it.

## Why GO means validation, not build

In this workbench, GO means there is enough evidence to run the next validation test. It never means build approval. Building comes only after validation evidence supports it.

## First prompt for a new business idea

Use:

docs/nmt/codex_prompts/09_NEW_IDEA_STARTER.txt

## First prompt for NailIt

Use:

docs/nmt/codex_prompts/03_NAILIT_DIAGNOSIS.txt

## Terminal commands versus Codex instructions

Terminal shell commands are commands like `pwd`, `git status`, or `python -m pytest`. They run on the computer.

Codex instructions are plain English tasks you paste into Codex, such as "create a new NMT run" or "audit the harness." Codex may decide which safe terminal commands to run, but it must obey the restrictions in your instruction.
