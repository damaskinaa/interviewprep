# Project 2 — PKS: Private Knowledge System
## Full Architecture & Implementation Blueprint

**Generated:** July 3, 2026
**Status:** Architecture complete, ready to build. Nothing built yet — this is the spec.
**Source:** Synthesized and fully engineered from the founder's design conversation (`safety_herms_obsidian.docx`), advancing it from discussion into a concrete, buildable, model-agnostic specification.

---

## 0. What this is, in one paragraph

PKS is a **model-agnostic private AI knowledge system**. Obsidian (plain Markdown files) is the permanent, human-owned source of truth. An orchestration layer routes questions to a pool of interchangeable AI models — cheap-first, escalating to stronger models only when needed — while a deterministic safety layer makes it *structurally impossible* for any AI to delete, overwrite, or corrupt the knowledge base. Sensitive data (customer names, contracts) is routed only to privately-hosted models on infrastructure the founder controls; non-sensitive work may use cloud models. The entire design survives models, vendors, and orchestration tools changing over time, because the architecture depends on **interfaces and rules, not on any specific model or product.**

The single governing principle, stated by the founder and adopted as the foundation of the whole design:

> **Obsidian stores knowledge. The AI never owns it. AI can suggest; only humans (or deterministic validated pipelines) can commit.**

---

## 1. Design goals (what this must guarantee)

These are the founder's stated requirements, extracted and made explicit as testable guarantees:

**G-1 — Model agnosticism.** Any model (Claude, GPT, Llama, Mistral, Qwen, Gemma, or a future model) can be swapped in or out by changing a single adapter, with zero changes to storage, retrieval, routing, or safety logic. *"If I remove every model tomorrow, my system still functions as a structured knowledge database."*

**G-2 — Data integrity is structural, not behavioral.** No AI can delete, overwrite, rename, or move knowledge files — not because it was instructed not to, but because it physically lacks the permission. Guardrails in prompts are treated as advisory only; the real guarantee is OS/filesystem-level.

**G-3 — Privacy by routing, not by hope.** Sensitive data (customer names, contracts, financials, personal info) never reaches a cloud model. Routing rules enforce this deterministically, before any model sees anything. *"A model does not upload data. Only your system does."*

**G-4 — Human-in-the-loop for all truth changes.** Every AI output lands in a sandbox/inbox as an unverified draft. It becomes part of the permanent knowledge base only after human approval (or a deterministic validation pipeline the human has pre-authorized).

**G-5 — Team-scalable, not laptop-bound.** Runs on always-on server infrastructure (the founder already has Hetzner), not on a laptop that has to stay on. Multiple team members, controlled per-user access.

**G-6 — Cost-controlled escalation.** Start with the cheapest capable model; escalate to more expensive models only when a quality gate says the answer isn't good enough — with hard limits so escalation can't loop forever and explode cost.

**G-7 — Full auditability & reversibility.** Every AI action is logged. Every knowledge change is version-controlled (Git) and therefore reversible. No silent corruption can survive undetected.

---

## 2. The layered architecture (the durable core)

The system is seven layers. The founder's key insight, preserved exactly: **the layers that matter are the ones that don't change** (knowledge, retrieval, routing, safety). Models and orchestration tools are deliberately the *replaceable* parts.

```
┌────────────────────────────────────────────────────────────┐
│  LAYER 1 — KNOWLEDGE (permanent, human-owned)              │
│  Obsidian vault = plain Markdown. Git-versioned.           │
│  READ-ONLY to all AI. The only source of truth.            │
└───────────────────────────┬────────────────────────────────┘
                            │ (read-only mount)
┌───────────────────────────▼────────────────────────────────┐
│  LAYER 2 — RETRIEVAL (model-independent)                   │
│  Index + search + RAG. Returns only the relevant chunks,   │
│  never the whole vault. Applies permission filtering.      │
└───────────────────────────┬────────────────────────────────┘
                            │ (relevant chunks only)
┌───────────────────────────▼────────────────────────────────┐
│  LAYER 3 — ORCHESTRATION (replaceable: Hermes, or anything)│
│  Pure routing + policy. Holds NO knowledge, NO model logic.│
│  "Traffic controller, not driver."                         │
└───────────────────────────┬────────────────────────────────┘
                            │ (structured task envelope)
┌───────────────────────────▼────────────────────────────────┐
│  LAYER 4 — ROUTING & SENSITIVITY CLASSIFICATION            │
│  Deterministic rules FIRST, cheap model SECOND.            │
│  Decides: which model tier, and (critically) whether data  │
│  is allowed to leave the private boundary at all.          │
└───────────────────────────┬────────────────────────────────┘
                            │ (routed request)
┌───────────────────────────▼────────────────────────────────┐
│  LAYER 5 — MODEL POOL (fully replaceable via adapters)     │
│  Every model implements the SAME interface. Cheap / strong │
│  / specialist (coding, writing). Private-hosted + optional │
│  cloud, split by sensitivity.                              │
└───────────────────────────┬────────────────────────────────┘
                            │ (raw model output + metadata)
┌───────────────────────────▼────────────────────────────────┐
│  LAYER 6 — EVALUATION & FALLBACK GATE                      │
│  Scores answer quality + confidence. Accept / retry /      │
│  escalate — with HARD limits. Catches cascading errors.    │
└───────────────────────────┬────────────────────────────────┘
                            │ (approved draft)
┌───────────────────────────▼────────────────────────────────┐
│  LAYER 7 — SAFETY, SANDBOX & COMMIT                        │
│  Draft → sandbox (untrusted) → human approval → Git commit │
│  to vault. Deterministic validator. Code runs in isolated  │
│  containers. Full audit log.                               │
└────────────────────────────────────────────────────────────┘
```

---

## 3. Layer-by-layer implementation spec

### Layer 1 — Knowledge (Obsidian)

**Vault structure** (personal and business physically separated, per the founder's requirement — ideally two separate vaults):

```
Business-Vault/
├── Projects/
│   ├── NAILIT/              # Project 1 lives here as knowledge
│   │   ├── Architecture.md
│   │   ├── Decisions.md
│   │   ├── Tasks.md
│   │   └── Research.md
│   └── PKS/                 # This project's own notes
├── Business/
│   ├── Company-Vision.md
│   ├── SOPs.md
│   └── Marketing.md
├── Customers/               # HIGH SENSITIVITY — private models only
│   └── (anonymized where possible: "Customer-184.md")
├── Reference/
├── Templates/
├── _Inbox/                  # AI drafts land here, unverified
├── _AI_Sandbox/             # disposable AI scratch space
└── Archive/

Personal-Vault/              # SEPARATE vault, AI has no access by default
├── Journal/
├── Health.md
└── Goals.md
```

**Hard rules for Layer 1:**
- Every file is plain Markdown — future-proof, openable in any editor 20 years from now.
- The entire vault is a **Git repository.** Every change is a commit; every mistake is reversible via `git revert`. This is the safety net that makes "no silent corruption survives" true.
- AI processes get a **read-only mount** of this directory (see Layer 7). They cannot write here directly, ever.
- **Never store secrets in the vault** — no passwords, API keys, private keys, recovery codes, or tokens. Those belong in a dedicated password/secret manager. (Founder's Layer 12.)

**Provenance metadata** — every AI-generated note begins with YAML front-matter so AI-origin content is never mistaken for verified truth:
```yaml
---
title: Authentication Design
source: ai                 # ai | human
model: <adapter-id>        # which model produced it
status: draft              # draft | reviewed | verified
confidence: unverified     # unverified | low | medium | high
project: PKS
created: 2026-07-03
tags: [architecture, ai]
---
```

### Layer 2 — Retrieval (model-independent RAG)

The founder's core scaling insight: **never load the whole vault into a model.** Search first, send only what's relevant.

**Pipeline:**
1. **Indexer** watches the vault, chunks notes (by heading/paragraph), and stores embeddings in a local vector database (e.g. a self-hosted Qdrant, Chroma, or pgvector instance on Hetzner — all run privately, no cloud).
2. On a query, retrieve the top-K relevant chunks via semantic + keyword (hybrid) search.
3. **Permission filtering happens here** — the retrieval layer tags each chunk with the sensitivity of its source folder (`Customers/` → high, `Reference/` → low) so downstream routing knows what it's dealing with.
4. Only those chunks — never the full vault — pass onward.

This layer is deliberately model-independent: swapping the LLM never touches it.

### Layer 3 — Orchestration (replaceable)

The founder was emphatic: **stop treating "Hermes" as the system.** Hermes is one current orchestrator; the architecture must outlive it. So this layer is defined purely by *what it does*, not what tool implements it:

- Receives a user request.
- Calls retrieval (Layer 2) to gather context.
- Builds a **universal task envelope** (see below).
- Hands off to routing (Layer 4).
- Never stores knowledge. Never embeds model-specific prompt logic. Never assumes a specific model's capabilities.

**Universal task envelope** (the contract that makes everything else swappable):
```json
{
  "task_type": "reasoning | coding | writing | analysis | summarization",
  "context": "<relevant retrieved chunks only>",
  "instruction": "<what to do>",
  "sensitivity": "low | medium | high",
  "output_format": "text | json | code",
  "max_escalations": 1
}
```

Any orchestrator (Hermes today, LangGraph or a custom Go/Python service tomorrow) that can produce this envelope plugs in with no downstream changes.

### Layer 4 — Routing & sensitivity classification

**This is both the performance layer AND the privacy control layer.** The founder correctly identified that wrong routing is a data-leak vector, not just a quality problem.

**Two-stage routing, rules before models (per the founder's fix for router-misclassification risk):**

**Stage A — deterministic sensitivity gate (rules only, no model):**
```
IF context contains data tagged sensitivity=high
   (customer names, contracts, financials, PII)
   → HARD ROUTE to private-hosted model ONLY.
   → Cloud models are physically not an option for this request.

IF folder-of-origin ∈ {Customers/, Business/, Personal/}
   → treat as sensitive → private models only.
```
This stage cannot be overridden by a model's opinion. It's plain code. This is what makes G-3 (privacy) a guarantee rather than a hope.

**Stage B — task/tier routing (rules + optional cheap classifier model):**
```
IF task_type = coding        → coding-specialist model group
IF task_type = writing       → writing/marketing model group
IF task_type = reasoning/analysis → general reasoning group

Within the chosen group:
   start at the CHEAPEST capable tier (see Layer 6 for escalation)
```

**Data minimization before inference** (founder's Layer, made concrete): before any request is sent to any model, a deterministic pass replaces raw identifiers with abstractions where the model doesn't need them:
```
"John Smith, Acme Ltd, john@acme.com"  →  "Customer-184, enterprise, manufacturing"
```
This runs even for private models — least-disclosure by default.

### Layer 5 — Model pool (adapters)

**The key future-proofing abstraction.** You never integrate a model. You integrate an **adapter** that presents every model — regardless of provider — through one identical interface:

```
adapter.generate(task_envelope) -> {
    "response": "...",
    "confidence": 0.0–1.0,
    "uncertainty_flags": [...],
    "missing_info": [...],
    "model_id": "...",
    "tokens": {...}
}
```

The orchestrator only ever knows "a thing that answers a task envelope." It does not know Claude, Llama, or any future model exists. Swapping models = writing one new adapter. Nothing else changes. (This is the direct implementation of G-1.)

**The model pool, organized by role and sensitivity:**

| Role | Sensitivity allowed | Hosting | Example candidates |
|---|---|---|---|
| Cheap router/classifier | any | private (Hetzner) | small Qwen/Mistral/Gemma |
| Fast summarizer | any | private | mid Mistral/Llama |
| Strong reasoning | high | private (Hetzner GPU) | large Llama/Qwen/Mistral |
| Coding specialist | medium/high | private | code-tuned open model |
| Writing/marketing | low/medium | private, or cloud if low | any |
| Cloud escape-hatch | **low only** | cloud (Claude/GPT) | used only for non-sensitive work |

Inference engines to host the open models privately: **Ollama** (simplest), **vLLM** or **TGI** (higher throughput for team scale) — all running on the founder's own Hetzner infrastructure, no external API for sensitive work.

### Layer 6 — Evaluation & fallback gate

The founder's fallback design — cheap-first, escalate if not good enough — made robust by addressing the five vulnerabilities they themselves identified:

**The escalation loop (with hard limits):**
```
1. Route to cheapest capable model.
2. Model returns response + confidence + uncertainty flags.
3. Evaluator (a "judge") scores the answer against the task.
4. Decision:
     - score ≥ threshold  → ACCEPT
     - score < threshold AND escalations_used < max_escalations
                          → ESCALATE to next stronger model
     - escalations exhausted
                          → RETURN best answer so far + explicit
                            confidence score + "needs human review" flag
```

**Hard rules preventing the failure modes the founder flagged:**
- **`max_escalations = 1` (default), hard cap.** Prevents the infinite escalation / cost-explosion loop (Vulnerability 4).
- **The judge is deterministic-assisted**, not purely a cheap model rubber-stamping (Vulnerability 2). Use structured checks (does the answer cite retrieved context? does it contain unsupported claims? does confidence meet threshold?) alongside any model-based scoring.
- **Cascading-hallucination guard (Vulnerability 3):** when one model's output feeds another (e.g. reasoning → coding → writing), each stage re-validates against the original retrieved context, not just the previous model's output. Wrong early assumptions get caught rather than polished.
- **Router-misclassification guard (Vulnerability 1):** the deterministic Stage-A sensitivity gate (Layer 4) means even if the cheap classifier misjudges *task type*, it can never misjudge *sensitivity* — sensitive data still can't leak to cloud.
- **Every answer surfaces its own weaknesses** — the founder specifically asked for this. Each response carries `uncertainty_flags` and `missing_info`, so the human sees "here's what might be wrong / what I didn't have" rather than a confident-looking answer hiding gaps.

### Layer 7 — Safety, sandbox & commit (the structural guarantee)

This is where G-2 and G-4 become *physically* true, not just promised. The founder's own hard-won conclusion, adopted verbatim as the design rule:

> **Guardrails in prompts reduce risk. Only system-level permissions eliminate it. "AI cannot directly touch critical data paths."**

**Defense in depth — six independent layers, so if any one fails the others still protect:**

1. **Read-only vault access.** The AI process runs under an OS user/mount that has read permission on the vault and write permission *only* to `_Inbox/` and `_AI_Sandbox/`. Deletion and modification of real notes is not "discouraged" — it is an OS-level permission denial. This is the single most important safeguard.

2. **Action gateway (no direct execution).** The AI never executes filesystem operations directly. It *proposes* a structured action:
   ```json
   { "action": "create_note", "target": "_Inbox/proposal.md", "content": "..." }
   ```
   A deterministic validator checks: is the target an allowed path? is the operation on the allowlist (create/append only — never delete/rename/move)? is the format valid? If not → automatic reject. Only validated actions execute.

3. **Sandbox writes only.** All AI output lands in `_Inbox/` or `_AI_Sandbox/` as untrusted, disposable drafts. Nothing there is trusted or permanent.

4. **Human approval gate.** A draft becomes real knowledge only when a human reviews it and moves/commits it — or when a deterministic pipeline the human pre-authorized validates it. *"AI can suggest. Only humans can commit."*

5. **Version control (Git) rollback.** The vault is a Git repo. Every commit is reversible. Even a mistake that somehow reaches the vault can be reverted. No silent overwrite survives.

6. **Audit log of all AI actions.** Every proposed action, every route decision, every escalation, every commit is logged — for debugging and for the auditability G-7 requires.

**Code execution isolation:** when a task requires running code (not just generating text), it runs in an isolated container (Docker on Hetzner — the founder correctly noted you do *not* need Daytona specifically; Docker on infrastructure you own is the durable choice). Ephemeral: filesystem is temporary, network controlled, process dies and nothing persists. A misbehaving model's code cannot escape the container to touch the vault or the host.

**Two data classes, different rules** (founder's distinction):
| Class | Examples | Rules |
|---|---|---|
| **Factual (high risk)** | customers, contracts, decisions, financials | read-only, human-verified, AI cannot rewrite |
| **Creative/structural (lower risk)** | drafts, summaries, brainstorming | AI may generate → sandbox → human approves |

---

## 4. Infrastructure topology (on Hetzner, which the founder already runs)

The founder already has a Hetzner server running an orchestrator. Here is how it scales without a rebuild — separating **storage from compute** (the founder's own principle):

```
Team users
    │  (authenticated, per-user permissions)
    ▼
┌──────────────────────────────────────────────┐
│  Server A — Orchestration + Routing + Safety  │
│  (lightweight: decisions, not heavy compute)  │
└───────────────┬───────────────────────────────┘
      ┌─────────┼──────────────────┐
      ▼         ▼                  ▼
┌───────────┐ ┌────────────────┐ ┌──────────────────┐
│ Server B  │ │ Server C       │ │ Cloud AI         │
│ Inference │ │ Vector search  │ │ (LOW-sensitivity │
│ (GPU:     │ │ + embeddings   │ │  tasks ONLY)     │
│  models)  │ │ (RAG index)    │ │                  │
└───────────┘ └────────────────┘ └──────────────────┘
      │
      ▼
┌──────────────────────────────────────────────┐
│  Obsidian vault (Git repo)                    │
│  Synced/backed up; read-only mount to AI      │
└──────────────────────────────────────────────┘
```

**Scaling progression the founder can follow** (their own Phase idea, made concrete):
- **Phase 1 (now):** single server, folder-level sandbox (`_Inbox`/`_Sandbox`), strict read-only vault permission, Git versioning. Enough to be *safe* immediately.
- **Phase 2:** add the retrieval/index layer (biggest performance upgrade — stop reading whole files).
- **Phase 3:** Docker-per-task sandboxes; add a job queue so concurrent requests don't overload the server.
- **Phase 4:** split inference onto its own GPU server; separate the vector-search service.
- **Phase 5:** per-user permissions, multi-project data isolation, VM-level isolation for high-risk tasks.

**Privacy guarantees that hold regardless of scale** (founder's Layer 6 principle — *"privacy is control of data routing, not local-vs-cloud"*): sensitive data never hits a cloud API; routing rules are strict; logs are controlled; encryption in transit and at rest (full-disk encryption on all servers; the vault backed up encrypted). And the honest legal caveat the founder must keep in view: **no architecture removes GDPR obligations** — for an Ireland/EU operation with customer data, access control, retention policy, and auditability are still legally required, not optional. This system *supports* compliance; it does not *grant* it.

---

## 5. Relationship to Project 1 (NAILIT) — how they connect without entangling

These are **two separate projects** and must stay architecturally separate. But they touch at exactly two clean points:

1. **NAILIT's project knowledge can live *in* the PKS vault** — as a `Projects/NAILIT/` folder of Markdown notes (decisions, architecture, tasks). PKS becomes the durable memory layer for NAILIT's development, replacing scattered chat logs and one-off handoff documents. The context-extraction documents already produced for NAILIT are the perfect seed content for that folder.

2. **The shared infrastructure question — Hetzner.** Both projects want to eventually run on Hetzner, and the earlier, firmly-held NAILIT decision was: **do not co-locate NAILIT on the box already running the orchestrator/bots** (insufficient memory headroom, blast-radius risk). That decision applies here too — if PKS's private inference grows to run large models on Hetzner, NAILIT's production backend should still be isolated (separate server or separate provider). Keep the two workloads on separate machines.

**What must NOT happen:** don't let PKS's "model-agnostic multi-model routing" ambitions leak into NAILIT's much simpler needs, and don't let NAILIT's specific pipeline logic contaminate PKS's deliberately general design. Project 1 is a product with customers; Project 2 is personal/business infrastructure. Different goals, different lifecycles, different risk profiles.

---

## 6. Honest risk & reality check

Advancing this from conversation to build surfaces real cautions worth stating plainly:

- **This is a substantial build, not a weekend project.** A genuinely model-agnostic, multi-model, sandboxed, RAG-backed private system with a safety layer is real engineering. The Phase 1 slice (read-only vault + Git + inbox + one private model) is achievable quickly and delivers most of the safety value; the full seven-layer system is a multi-month effort.
- **Self-hosting capable models needs real hardware.** Strong reasoning models want a GPU with meaningful VRAM. The founder's existing Hetzner box may run small models fine but will need GPU capacity for the "strong reasoning on sensitive data" tier. This is a real cost, and per the founder's own broader principle, worth incurring only when the need is proven.
- **The judge/evaluation layer is the hardest part to get right** — the founder identified this correctly. A weak judge approves bad answers; a strict one explodes cost. Budget the most design attention here.
- **Model-agnosticism has a quality cost.** A perfectly generic interface can't exploit any single model's special features. That's an accepted, deliberate tradeoff for durability — worth naming so it's a choice, not a surprise.
- **GDPR is a legal obligation the architecture supports but cannot satisfy alone.** For customer data in the EU, get the access-control, retention, and audit posture reviewed by someone qualified before going live with real customer data. (This exact caveat also sits open in Project 1.)

---

## 7. The one-sentence summary

Build the **durable core** (read-only Git-versioned Obsidian vault + retrieval + deterministic routing/sensitivity gate + adapter interface + sandbox/approval safety layer) first and get it exactly right, because that core is what never changes — then plug in whatever models are best at any given moment as fully-replaceable parts, starting cheap-and-private and escalating only under a hard-capped quality gate, so the system stays private, safe, and useful no matter how the model landscape shifts.
