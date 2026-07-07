# Upstream NMT Sync State

This file records the upstream watcher state for the public Next Move Theory Canon & Skills repository.

The watcher is detection-only. It must never update, rewrite, merge, patch, synchronize, or normalize local `docs/nmt` methodology files.

## Upstream Repository

- Upstream repository URL: https://github.com/zamesin/Next-Move-Theory-Canon-and-Skills
- Default branch: main
- Last reviewed upstream SHA: UNKNOWN
- Last checked date: UNKNOWN
- Last integrated local commit: 84b83fc

## Sync Policy

1. Detect automatically.
2. Review manually.
3. Update only after a separate sync-audit run.
4. Require explicit human approval before adoption.
5. Run methodology preservation checks before adoption.
6. Run methodology coverage tests before commit.
7. Require CI before commit.

## Forbidden Behavior

1. No auto-merge.
2. No auto-rewrite.
3. No auto-update of local canon content.
4. No auto-synchronization of `docs/nmt` methodology files.
5. No silent concept deletion.
6. No weakening original NMT core concepts.
7. No weakening Anastasia/team/book enhancement rules.
8. No inventing unavailable/paywalled methodology.
9. No treating upstream changes as locally adopted until a human-approved sync-audit run completes.

## Required Manual Review If Upstream Changed

If the watcher reports a different upstream SHA, run:

`docs/nmt/codex_prompts/11_UPSTREAM_NMT_SYNC_AUDIT.txt`

That audit must compare upstream changes, classify methodology impact, preserve the local methodology contract, run tests, and return a human-review decision. The watcher itself must not perform any adoption work.
