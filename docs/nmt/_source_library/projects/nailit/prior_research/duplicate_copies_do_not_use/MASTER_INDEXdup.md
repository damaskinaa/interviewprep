# MASTER INDEX — All Projects & Documents

**Last updated:** July 3, 2026
**Purpose:** The single entry point to everything. Two separate projects, fully documented.

---

## ⭐ START HERE

**`_INDEX/FULL_PORTFOLIO_HANDOFF.md`** — the complete handoff covering BOTH projects: architecture, next steps, market research, strategy, segments, assumptions, and the reasoning behind every major decision. This is the document to hand a colleague taking over the whole operation. Read it top-to-bottom once, then work from the per-project deep-dives below.

---

## The two projects, at a glance

| | **Project 1 — NAILIT** | **Project 2 — PKS** |
|---|---|---|
| **What** | AI interview intelligence product (CV+JD -> company-specific prep pack -> mock interview with AI feedback) | Private, model-agnostic AI knowledge infrastructure (Obsidian truth layer + swappable models + structural safety layer) |
| **Type** | A product, for customers | Personal/business infrastructure |
| **Stage** | Built & live-verified; pre-auth, pre-revenue | Fully architected; not yet built |
| **Lives in** | `PROJECT-1_NAILIT/` | `PROJECT-2_PKS-Knowledge-Infrastructure/` |
| **Deep-dive** | `NAILIT_MASTER.md` | `PKS_Architecture_Blueprint.md` |
| **Next action** | Ship auth -> fix story bug -> build contribution DB (the moat) | Build Phase 1: Git vault + OS read-only-for-AI |

**Why separate:** different goals, lifecycles, risk profiles. **How they connect:** (1) NAILIT's knowledge can live inside the PKS vault as `Projects/NAILIT/`; (2) both may run on Hetzner but must stay on **separate machines**.

---

## PROJECT 1 — NAILIT

**Authoritative deep-dive:** `PROJECT-1_NAILIT/NAILIT_MASTER.md` — the full unified master (27 sections + 6 appendices) with June 2026 market intelligence, the honest-prep-vs-copilot positioning, the full Segment 5 analysis, the RAT risk model, the ordered ACT-1->8 plan, the 4-week validation roadmap, competitor pricing, the interview kit, API pricing, and the founder's verified answer bank. **This is the current single source of truth for NAILIT** and supersedes the earlier handoff/PMD files.

**Context-extraction set** (rigorous, source-tagged — built via the formal 3-stage extraction skill):
- `nailit-developer-handoff.md` — engineer-focused handoff
- `nailit-knowledge-base.md` — organized 8-cluster reference + dependency graph + feature matrix
- `nailit-extraction-ledger.md` — 101 source-tagged raw facts (the evidence layer)
- `nailit-audit-report.md` — completeness proof (zero-delta coverage, reconstruction score)

**Granular history & assets:**
- `NAILIT_ULTIMATE_HANDOFF.md`, `NAILIT_COMPLETE_PMD.md`, `NAILIT_ADDENDUM_DEFENSIBILITY_FEASIBILITY.md`, `NAILIT_PMD.md`, `NAILIT_HANDOFF.md` — prior versions, superseded by `NAILIT_MASTER.md`, kept for reference
- `Hermes_NMT_Pipeline_Run.md` — the two external strategy runs (WARNING: scored a *generic invented product*, not NAILIT; methodology reference only)
- `answer_bank_condensed.txt` — worked example of a condensed answer-bank input
- `nailit-website.html`, `NAILIT_Client_Guide.pptx`, `NAILIT_Investor_Deck.pptx` — marketing/deck assets

---

## PROJECT 2 — PKS (Private Knowledge System)

**Authoritative deep-dive:** `PROJECT-2_PKS-Knowledge-Infrastructure/PKS_Architecture_Blueprint.md` — the full seven-layer architecture (Knowledge -> Retrieval -> Orchestration -> Routing/Sensitivity -> Model Pool -> Evaluation -> Safety/Commit), design goals as testable guarantees, infrastructure topology, and honest risk check.

**Build guide:** `PKS_Implementation_Plan.md` — the phased sequence (Phase 1-6), each phase independently useful with stop-and-verify gates. **Build Phase 1 first** (Git vault + OS read-only-for-AI + inbox) — a week's work, ~80% of the safety value.

---

## Shared caveats (both projects)

- **GDPR is a legal obligation, not an engineering one** — get qualified review before real EU personal data flows at scale.
- **No paid infrastructure before real paying users** — the founder's firm, repeatedly-correct discipline.
- **Verify on the real running system — an AI's self-report is not verification.**
- **Keep the two projects on separate machines** if both land on Hetzner.

---

## Suggested reading order for a colleague

1. `_INDEX/FULL_PORTFOLIO_HANDOFF.md` — the whole picture.
2. `PROJECT-1_NAILIT/NAILIT_MASTER.md` — the product, in full depth.
3. `PROJECT-2_PKS-Knowledge-Infrastructure/PKS_Architecture_Blueprint.md` — the infrastructure.
4. `PROJECT-2_PKS-Knowledge-Infrastructure/PKS_Implementation_Plan.md` — how to start building PKS this week.
5. Everything else as needed, via the maps inside each primary document.
