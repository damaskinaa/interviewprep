# Master Prompt Library — Tier 4 Runs
*Paste these directly into Claude Code from the repo root. Each one wires the full canon + TEAM.md + validation-gate together. Run the gate prompt (bottom of file) after every one of these.*

---

## SETUP — run once per session, before any project prompt

```bash
cd ~/Next-Move-Theory-Canon-and-Skills
git pull
claude
```
Inside Claude Code:
```
/model
```
Select Fable 5 if researching (Deep mode), Opus/Sonnet if just conversing.

Then paste:
```
Read TEAM.md in full. Confirm you understand the methodology rules, canon
file map, skill routing, validation debt rule, and current Active Projects
state before I give you a task.
```

---

## PROMPT A — Full Algorithm From Scratch (use for ANY new idea)

```
Read TEAM.md, then read in full: Algorithms/the-algorithm.md,
Next-Move-Theory/nmt-key-theses.md, Next-Move-Theory/subtraction.md,
Next-Move-Theory/local-vs-global-optimum.md,
Riskiest-Assumption-Test/rat-key-theses.md,
Advanced-Jobs-To-Be-Done/ajtbd-key-theses.md,
Advanced-Jobs-To-Be-Done/value-creation-mechanics.md,
Advanced-Jobs-To-Be-Done/job-graph.md,
ABCDX-Segmentation/abcdx-segmentation-key-theses.md
(all under Next-Move-Theory-Canon/). Confirm all read.

Run the COMPLETE 10-step algorithm from the-algorithm.md, as a gated loop,
per TEAM.md's methodology rules. Do not skip steps. Do not soften a failed
gate into a pass.

THE IDEA (raw — every line is [HYPOTHESIS] until validated):

[PASTE YOUR RAW IDEA DESCRIPTION HERE — messy is fine]

CURRENT REAL (non-hypothetical) PROBLEMS, if any:

[PASTE ANY LIVE, CONFIRMED ISSUES — e.g. technical bugs, actual customer
feedback already received. Do not include hopes or assumptions here.]

RUN:

STEP 1 — Challenge the goal. 5 Whys, 3-5 levels up. Apply Local vs Global
Optimum explicitly: state which track any proposed fix/move sits on, and
whether a second parallel track should be funded.
GATE: restate the goal if wrong before continuing.

STEP 2 — Diagnose current state. Explicit PMF stage (none/weak/strong).
Tag every fact [DATA] or [HYPOTHESIS].

STEP 3-4 — Assemble Map of Segments + Job Graph. Apply subtraction
explicitly — what should be REMOVED before anything is added? State the
Big Job above the surface-level ask. Shortlist value-creation mechanics
by name from the catalog.
GATE: does the segment+Job hypothesis survive scrutiny?

STEP 5-7 — Run /market-research in Deep mode. Zero assumptions carried
in as fact. Rank hypotheses by RICE. Apply the unit-economics gate.

STEP 8 — RAT using (probability × cost if wrong) / cost to validate.
Five baseline risks + custom risks specific to this idea. State plainly
whether the goal here is to kill, pivot, or proceed.
GATE: no build/fix recommendations until this step completes.

After Step 8, apply the validation-gate from validation-gate.md.
```

---

## PROMPT B — Resume/Continue an Existing Project

```
Read TEAM.md. Under "Active Projects," find the entry for {PROJECT SLUG —
replace with your project's slug}. Read the most recent file in
my-research/{PROJECT SLUG}/ in full.

Given everything in that file plus TEAM.md's current state for this project,
what is the single next action per the-algorithm.md's step sequence — and
which step of the 10 are we actually on right now, not which step feels
like the obvious next thing to do?

Apply the validation-gate to your answer before giving it to me.
```

---

## PROMPT C — Existing/Live Product Diagnosis (no dedicated skill exists — manual ABCDX)

```
Read TEAM.md, then ABCDX-Segmentation/abcdx-segmentation-key-theses.md and
Next-Move-Theory-Canon/Algorithms/the-algorithm.md Section 5 ("Contextual
branches by PMF stage / existing product").

This is an EXISTING product with real paying/using customers, not a new idea.
Do not run /market-research's new-idea framing on this.

CONTEXT:
[Describe the product, the stalled/declining metric, and any customer data
you have — cohorts, churn reasons if known, support tickets, etc.]

Run ABCDX on the paying base as described in the canon: segment by margin ×
satisfaction (A/B/C/D/X). Identify the 20% of customers giving 80% of margin.
Recommend switch interviews with churned users and "why do they stay"
interviews with A/B customers before recommending any product change.

Apply the validation-gate before finalizing.
```

---

## PROMPT D — Value Proposition (after market-research verdict exists)

```
Read TEAM.md. Read the latest market-research result at
my-research/{PROJECT SLUG}/market-research/{most recent file}.

Run /craft-value-proposition using the chosen segment and Core Jobs from
that file. Before running, state explicitly: has the validation-gate's
"cheapest next real-world test" from the market-research run actually been
completed? If not, warn me that this step is premature per RAT discipline,
but proceed if I confirm.

Apply the validation-gate to the output.
```

---

## THE GATE PROMPT — run after literally every skill output

```
Apply the validation-gate from validation-gate.md to the output above.
```

---

## Save-and-commit block — run after every gated output you intend to keep

```bash
mkdir -p my-research/{PROJECT SLUG}/{skill-name}
cp -r Skills-Results/{PROJECT SLUG}/{skill-name}/* my-research/{PROJECT SLUG}/{skill-name}/
git add my-research/ TEAM.md
git commit -m "{PROJECT SLUG}: {skill-name} run $(date +%Y-%m-%d)"
```

Also update TEAM.md's "Active Projects" section by hand after each run — the harness only stays accurate if this file is kept current.
