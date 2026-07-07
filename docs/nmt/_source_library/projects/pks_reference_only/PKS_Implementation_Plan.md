# Project 2 — PKS: Implementation Plan & Next Steps

**Companion to:** `PKS_Architecture_Blueprint.md`
**Purpose:** Turn the architecture into an ordered, buildable sequence. Each phase is independently useful and safe to stop at.

---

## The build philosophy for this project

Mirror the discipline already proven in Project 1: **one layer at a time, verify before moving on, never bundle.** The safety layers come *first*, before any clever model routing — because an unsafe system that's smart is worse than a safe system that's simple. Get the "AI physically cannot corrupt my knowledge" guarantee working before anything else.

---

## Phase 1 — Safe foundation (do this first, it's small and high-value)

**Goal:** A vault the AI can read but *structurally cannot damage*, with every change reversible. This alone delivers ~80% of the safety value.

**Steps:**
1. Create the Obsidian vault with the folder structure from the blueprint (`Projects/`, `Business/`, `Customers/`, `_Inbox/`, `_AI_Sandbox/`, `Archive/`). Keep Personal a **separate vault** the AI never gets mounted.
2. `git init` the vault. Commit everything. This is the rollback safety net — set it up before any AI touches anything.
3. Configure the AI/orchestrator process to run under an OS user that has **read-only** permission on the vault and **write** permission *only* to `_Inbox/` and `_AI_Sandbox/`. Test it: try to make the AI delete a note and confirm the OS denies it. This test passing is the whole point of Phase 1.
4. Establish the provenance-metadata convention (YAML front-matter: `source`, `status`, `confidence`) and a template for AI-generated notes.
5. Seed the vault with Project 1's knowledge — drop the NAILIT context-extraction documents into `Projects/NAILIT/`. Now PKS is immediately useful as NAILIT's memory layer.

**Stop-and-verify:** the AI can answer questions from the vault and can write drafts to `_Inbox/`, but any attempt to modify or delete a real note fails at the OS level. Confirmed by direct test, not by trusting a prompt.

---

## Phase 2 — Retrieval (the biggest performance/scale upgrade)

**Goal:** Stop loading whole files into models. Search first, send only relevant chunks.

**Steps:**
1. Stand up a private vector database on the server (Qdrant / Chroma / pgvector — all self-hosted, no cloud).
2. Build the indexer: watch the vault, chunk notes by heading/paragraph, embed, store. Re-index on change.
3. Implement hybrid retrieval (semantic + keyword), returning top-K chunks.
4. Tag each retrieved chunk with the sensitivity of its source folder — this feeds the routing gate in Phase 4.

**Stop-and-verify:** ask a question, confirm the system retrieves only the 2–3 relevant notes (not the whole vault), and that `Customers/`-sourced chunks are correctly tagged high-sensitivity.

---

## Phase 3 — Model adapter + one private model

**Goal:** Prove model-agnosticism with a single working adapter, on a privately-hosted model.

**Steps:**
1. Define the adapter interface exactly as in the blueprint (`generate(task_envelope) → {response, confidence, uncertainty_flags, missing_info, ...}`).
2. Stand up one open model via Ollama on the server (start small — a mid Qwen/Mistral/Llama).
3. Write the adapter for it. Wire orchestrator → adapter → response.
4. Route a real question end-to-end: retrieval → task envelope → adapter → draft in `_Inbox/`.

**Stop-and-verify:** a full private round-trip works, entirely on your infrastructure, with nothing leaving the server. Then write a *second* adapter (even a cloud one, for a non-sensitive test) and confirm swapping models requires zero changes outside the adapter — this proves G-1.

---

## Phase 4 — Routing & the sensitivity gate (the privacy guarantee)

**Goal:** Make it structurally impossible for sensitive data to reach a cloud model.

**Steps:**
1. Implement the deterministic Stage-A sensitivity gate: rules-only, runs before any model, hard-routes anything tagged high-sensitivity to private models exclusively.
2. Implement the data-minimization pass (replace raw identifiers with abstractions before inference).
3. Implement Stage-B task/tier routing (coding → coding model, etc.), starting at the cheapest capable tier.

**Stop-and-verify:** feed a request containing a customer name; confirm via the audit log that it was hard-routed to a private model and that a cloud path was never even considered. This test passing is the privacy guarantee (G-3).

---

## Phase 5 — Evaluation, fallback & the safety commit pipeline

**Goal:** Cheap-first escalation with hard limits, plus the full draft → approve → commit flow.

**Steps:**
1. Build the evaluator/judge: structured checks (cites context? unsupported claims? confidence ≥ threshold?) plus optional model scoring.
2. Implement escalation with `max_escalations = 1` hard cap; on exhaustion, return best answer + confidence + "needs human review."
3. Build the action gateway: AI proposes structured actions (create/append only), deterministic validator approves or rejects against an allowlist.
4. Build the human approval step: review `_Inbox/` drafts, approve → Git commit into the permanent structure.
5. Turn on the full audit log.

**Stop-and-verify:** a low-quality cheap-model answer escalates exactly once, then stops; a good answer is accepted; every AI action appears in the audit log; nothing reaches the vault without passing through approval.

---

## Phase 6 — Scale & harden (only when the need is real)

Per the founder's own "don't pay before you need it" discipline, applied here too:
- Split inference onto a dedicated GPU server (needed for the strong-reasoning-on-sensitive-data tier).
- Add a job queue for concurrency.
- Docker-per-task sandboxes for code execution.
- Per-user permissions and multi-project data isolation for team use.
- Encrypted backups (3 copies: primary, encrypted external, encrypted cloud) — and actually test a restore.

---

## What to build first, in one line

**Phase 1 only, this week:** Git-versioned Obsidian vault + OS-level read-only-for-AI permissions + an `_Inbox` for drafts. That single step makes your knowledge structurally safe from AI corruption and immediately gives NAILIT a durable memory home — everything else builds on top of it and can wait until each prior layer is verified.

---

## Open decisions to make (deliberately, each in its own moment)

1. **Vector DB choice** — Qdrant vs. Chroma vs. pgvector. Any works; pick based on what's easiest to self-host on your current Hetzner setup.
2. **Inference engine** — Ollama (simplest, start here) vs. vLLM/TGI (higher throughput, for team scale later).
3. **Which open models** for each role tier — decide after Phase 3 proves the adapter pattern, based on real quality tests on your actual documents, not on benchmarks.
4. **GPU capacity** — when (not if) the strong-reasoning tier needs it; size it against real workload, defer the spend until proven.
5. **GDPR posture** — get qualified review before real customer data enters the system. This is a legal task, not an engineering one, and it's shared with Project 1.
