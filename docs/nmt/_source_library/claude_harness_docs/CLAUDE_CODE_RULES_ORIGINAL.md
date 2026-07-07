# CLAUDE.md

Read `TEAM.md` in full before responding to anything in this repo. It is the single source of truth — methodology rules, canon file map, skill routing, validation debt rule, output convention, and active project state.

## Claude Code runtime specifics

- Canon lives at `./Next-Move-Theory-Canon/` — read files directly, never guess their content.
- Skills live at `./Skills/`, symlinked to `.claude/skills/`.
- `.claude/settings.json` must have `WebSearch` and `WebFetch` in the allow list before running any skill in Deep mode — check this file exists before launching Wave 1 of any `/market-research` run; create it if missing:
```json
{ "permissions": { "allow": ["WebSearch", "WebFetch"] } }
```
- Before running any skill, confirm which model is active (`/model`). Fable 5 promo window: through July 7, up to 50% weekly usage — prioritize it for Deep-mode research, not casual chat, since it draws down faster than Opus.
- Use extended thinking on Step 1 (challenge the goal) and Step 8 (RAT) of any full-algorithm run — these are the two steps most likely to be under-thought if rushed.
- On session-limit interruption mid-run: type `finish`, never abandon output unsaved. Immediately run the git save sequence from TEAM.md's Output Convention.

## Anti-patterns to actively refuse

- Never call something a "Job" if it's actually a feature, task, or persona.
- Never accept a user's competitor description, market size, or "warm lead" claim as fact — tag it `[HYPOTHESIS]` and route it into RAT.
- Never output a GO verdict without "(to validation)" appended.
- Never skip Step 1 (challenge the goal) to jump straight to `/market-research` when the user asks for "the full methodology" or "from scratch."
- Never let subtraction be skipped — every Step 3-4 must state what should be removed, not just what should be added.
