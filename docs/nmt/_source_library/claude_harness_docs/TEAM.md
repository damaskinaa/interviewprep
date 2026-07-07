# TEAM.md — Single Source of Truth
*Agent-agnostic. Read by both CLAUDE.md and AGENTS.md wrappers. Update the Active Projects section as work progresses.*

---

## Methodology Rules (non-negotiable)

- Use **Advanced Jobs To Be Done (AJTBD)** as defined in `Next-Move-Theory-Canon/`, never generic/Christensen JTBD.
- A **Job** = `WHEN [context+trigger] I WANT TO [outcome] WITH [success criteria] IN ORDER TO [higher Job]`. Never shorten a Job to just the verb.
- **Segment by Job Graph similarity, never by demographics.** Demographics are a correlate, not a cause.
- **Same outcome + different success criteria = different Job = different segment.** Always check criteria before merging two "similar" segments.
- **Every input is a hypothesis until field-validated.** Never let a skill treat a user's claim (competitor description, "warm lead," market size) as fact. Explicitly tag `[DATA]` vs `[HYPOTHESIS]` in every output.
- **GO always means "GO to validation," never "GO to build."** Append "(to validation)" to every GO verdict.
- **Subtraction before addition.** Before proposing a new feature/segment/Job, first ask what should be *removed*. Apply the four reasons (brain rewards less spent; risk compounds multiplicatively; focus doesn't sum; loss aversion ~2×).
- **The goal of a new initiative is to kill it or pivot it, cheaply, not to launch it.** A RAT run that kills an idea before the build is a successful RAT.
- **Local vs. Global Optimum is an explicit gate, not a footnote.** Every Step 1 must state which track a proposed move sits on, and whether a second parallel track should be funded.
- **Recruit evidence only from past-payers / past-doers.** Never treat stated future intent as validated demand.

## Canon File Map (read before running any skill)

| Task | Required reading |
|---|---|
| Any run at all | `Algorithms/the-algorithm.md`, `Next-Move-Theory/nmt-key-theses.md` |
| Segment/Job work | `Advanced-Jobs-To-Be-Done/ajtbd-key-theses.md`, `Advanced-Jobs-To-Be-Done/job-graph.md`, `Advanced-Jobs-To-Be-Done/segmentation.md` |
| Value/mechanics work | `Advanced-Jobs-To-Be-Done/value-creation.md`, `Advanced-Jobs-To-Be-Done/value-creation-mechanics.md` |
| Risk/validation work | `Riskiest-Assumption-Test/rat-key-theses.md` |
| Existing-product diagnosis | `ABCDX-Segmentation/abcdx-segmentation-key-theses.md` |
| Strategic framing | `Next-Move-Theory/subtraction.md`, `Next-Move-Theory/local-vs-global-optimum.md`, `Next-Move-Theory/focus-as-company-attention-management.md` |
| B2B work | `Advanced-Jobs-To-Be-Done/b2b.md` |
| Interviews | `HowTos/basic-ajtbd-interview-guide-and-principles.md` |

## Skill Routing

- Stuck / need to pressure-test an idea → `/ask-nmt` first
- New idea, no segment chosen → `/market-research`
- Segment known, need value hypothesis → `/craft-value-proposition`
- Value known, ready to build → `/product-requirements`
- Value known, ready to sell → `/craft-go-to-market`
- **Existing product, stalled metric** → no dedicated skill exists yet; run ABCDX manually via `/ask-nmt` referencing `abcdx-segmentation-key-theses.md`

## Validation Debt Rule

Every artifact this repo produces must open with:
```
Validation Debt: N unverified assumptions, M fatal if wrong.
Cheapest real-world test for the top fatal assumption: [specific action].
```
No exceptions, including for /ask-nmt conversational output when it produces a recommendation.

## Output Convention

- All skill outputs saved to: `my-research/{project-slug}/{skill-name}/{YYYY-MM-DD}-result.md`
- Never leave anything only in `Skills-Results/` — copy and commit same day:
```bash
mkdir -p my-research/{project-slug}/{skill-name}
cp -r Skills-Results/{project-slug}/{skill-name}/* my-research/{project-slug}/{skill-name}/
git add my-research/
git commit -m "{project-slug}: {skill-name} run {YYYY-MM-DD}"
```

## Session Discipline (Claude Pro / Fable promo constraints)

- Quick mode for iteration; Deep mode only for the run you intend to act on.
- If session limit hits mid-run, type `finish` — never abandon a partial run unsaved.
- Fable 5 promo (through July 7): up to 50% of weekly usage; draws down faster than Opus — reserve for Deep-mode research runs, not casual chat.

---

## Active Projects

*Add one entry per project here as you start working on it. Template:*

```
### Project: {slug}
- **What:** [one-line description]
- **Stage:** [pre-idea / pre-revenue / mid-build / live with customers]
- **Current blocking gate:** [the single thing that must resolve before anything else]
- **Last research run:** [skill + date + verdict]
- **Files:** `my-research/{slug}/`
```

*This section is intentionally empty in the base harness. Keep project-specific business content in `my-research/{slug}/`, referenced by slug only — TEAM.md's methodology rules above stay reusable across any idea.*
