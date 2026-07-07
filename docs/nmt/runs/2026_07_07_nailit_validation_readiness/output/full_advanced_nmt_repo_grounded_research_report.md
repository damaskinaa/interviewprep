# Full Advanced NMT Repo-Grounded Research Report

Run: `2026_07_07_nailit_validation_readiness`
Phase: Phase 1 only: internal repo-grounded Advanced NMT research
Product identity: NailIt is the AI interview preparation product in this repository.
External market research: not run
Public web: not used
Production code changes: none
Commit: none

## 0. Acceptance Gate

This report is accepted only as a repo-grounded Phase 1 diagnosis. It must include exact file and line anchors, Layer 1 trace, Layer 2 trace, evidence labels, the conversation failure ledger, and no external market claims.

Contaminated-source rule:

- `NO EVIDENCE` Wrong-category external research is excluded from this report.
- `NO EVIDENCE` `docs/nmt/runs/2026_07_07_nailit_validation_readiness/output/full_advanced_nmt_integrated_research_report.md` is excluded because it integrated wrong-category external research.
- `NO EVIDENCE` This report does not use public web, external market research, or wrong-category competitor/source claims.

Conversation failure ledger:

1. `STORY RISK` Wrong phase ordering: external/integrated research happened before a strict repo-first Phase 1 acceptance gate. This report is Phase 1 only.
2. `STORY RISK` Wrong external research: wrong-category external research was invalid for NailIt.
3. `STORY RISK` Wrong integration: the integrated report using the contaminated external source is invalid for this run.
4. `STORY RISK` Shallow repo report: the prior repo report lacked enough exact line anchors.
5. `STORY RISK` Missing line anchors: this version cites `api.py`, `agent_v2.py`, `lua_coach.py`, `lua_brief_builder.py`, `job_store.py`, and `tests/...` line ranges.
6. `STORY RISK` Failed strict gate: no product claim is accepted unless it is labeled and tied to repo/test evidence or explicitly marked as not evidenced.

NailIt identity lock:

- `REPO FACT` The backend home route identifies the API as an interview-intelligence API in `api.py:306-308`.
- `REPO FACT` The prep request model is interview-specific: company, role, job description, CV, and extra context in `api.py:259-264`.
- `REPO FACT` The session request model is interview-specific and includes company, role, JD, CV, answer bank, company description, transcripts, user email, and user ID in `api.py:267-276`.

## 1. Validation Debt

`REPO FACT` NailIt has backend code for company/role-specific interview-pack generation and Lua mock-interview flows. The Layer 1 trace is anchored in `api.py:259-264`, `api.py:344-375`, `agent_v2.py:6311-6417`, and `agent_v2.py:6423-6494`. The Layer 2 trace is anchored in `agent_v2.py:6397-6406`, `lua_brief_builder.py:5-64`, `api.py:653-662`, `api.py:690-781`, `api.py:794-875`, and `lua_coach.py:86-238`.

`TESTED` Static and dynamic tests cover route protection, GDPR store coverage, payment/contribution not-ready contracts, email not-ready behavior, Lua route protection, temp-store deletion, and disabled provider/network keys in `tests/test_validation_readiness_static.py:83-245` and `tests/test_dynamic_readiness_contracts.py:90-211`.

`NO EVIDENCE` The repo does not contain payment behavior, non-buyer evidence, willingness-to-pay behavior, acquisition data, live conversion data, source-sufficiency proof, user trust evidence, or interview-outcome improvement evidence.

`STORY RISK` The main validation debt is mistaking implemented artifact generation for validated customer value.

## 2. Fatal if wrong

`HYPOTHESIS` The focal Job is: "When I have a specific interview coming up, help me turn my CV, the JD, company signals, and scattered prep material into credible company-specific answers and realistic practice."

Fatal assumptions:

1. `NO EVIDENCE` Candidates will pay for company-specific interview prep before proven outcomes.
2. `NO EVIDENCE` Public/source inputs are sufficient, current, permitted, and trustworthy enough.
3. `NO EVIDENCE` Users trust AI answer examples, scoring, and feedback.
4. `NO EVIDENCE` Lua practice creates behavior change or interview-performance improvement.
5. `REPO FACT` Checkout is explicitly blocked with 501 `payment_checkout_not_ready` in `api.py:311-319`.
6. `REPO FACT` Contribution/outcome capture is explicitly blocked with 501 `contribution_capture_not_ready` in `api.py:322-330`.
7. `REPO FACT` Email delivery is explicitly not configured/implemented in `api.py:109-129`.

## 3. Cheapest Real World Test

`HYPOTHESIS` The cheapest credible test is a controlled concierge validation sprint with candidates who have real scheduled interviews.

Minimum test:

1. `FIELD DATA` Recruit 5-10 candidates with named company, role, JD, CV, and interview date.
2. `PAYMENT EVIDENCE` Ask for payment or deposit before delivery.
3. `FIELD DATA` Manually audit sources per company/role and record confidence.
4. `FIELD DATA` Deliver the pack and a Lua-style practice session.
5. `FIELD DATA` Observe whether candidates revise answers, repeat practice, trust feedback, and would recommend/pay again.
6. `FIELD DATA` Capture non-buyer and near-buyer reasons.

This test is not run in this phase.

## 4. Block or Proceed

`PROCEED` for controlled concierge validation design.

`BLOCKED` for self-serve paid launch, external market claims, source-sufficiency claims, Lua-outcome claims, Series A claims, and additional feature build as the next move.

## 5. First Pass

`REPO FACT` Layer 1 is implemented as a backend generation pipeline. The input contract exists in `api.py:259-264`; `/prepare` calls `run_pipeline` in `api.py:344-352`; output returns markdown/product JSON/Lua brief in `api.py:354-375`; the full pipeline runs candidate extraction, JD analysis, research/source collection, gap map, strategy, validation, final pack, evidence ledger, and Lua brief in `agent_v2.py:6311-6417`; artifact files are written in `agent_v2.py:6461-6494`.

`REPO FACT` Layer 2 is implemented as Lua mock-interview backend behavior. The pipeline creates the Lua brief in `agent_v2.py:6397-6406`; `lua_brief_builder.py:5-64` defines the brief, one-question-at-a-time rule, answer scoring rule, and scoring dimensions; `/lua-coach` calls Lua coaching in `api.py:653-662`; resume/call-turn flows store turns and return adapted coach output in `api.py:690-781`; benchmark/practice endpoints generate questions, feedback, pressure followup, mastery, and events in `api.py:794-875`.

`REPO FACT` Sensitive routes are app-key protected by `Depends(require_app_key)` across prep/session/module/answers/Lua/internal/user-data routes, with `require_app_key` itself in `api.py:87-91`.

`STRONG INFERENCE` The product surface is technically meaningful, but the validated business surface is weak because payment, contribution capture, email, user-level auth/ownership, source sufficiency, and outcome evidence are absent or explicitly not-ready.

## 6. Self Critique

`STORY RISK` This report can still over-credit source code because prompt text and routes can describe intended behavior without proving production reliability.

`TESTED` Existing tests prove contracts, not full product quality. They do not prove source truth, pack usefulness, answer safety in live model output, trust, payment, acquisition, or interview outcomes.

`DOC CLAIM` Prior research remains context only unless verified by repo behavior, tests, field data, payment evidence, or reliable external source. This phase used no external research.

## 7. Evidence Check

Evidence priority:

1. `REPO FACT` Current backend source code.
2. `TESTED` Static/dynamic tests and CI workflow.
3. `DOC CLAIM` Run manifest, input files, state files, and prior research.
4. `HYPOTHESIS` NMT interpretation of Job, segment, value, and next move.
5. `NO EVIDENCE` Customer, payment, non-buyer, acquisition, and outcome claims.

Important boundary:

`REPO FACT` Source planning and external bridge parsing exist, but no live web/source fetch was run in this phase. `collect_sources` parses supplied external research only when a bridge block exists in `agent_v2.py:583-596`, and logs no bridge when absent in `agent_v2.py:597-599`.

## 8. Missing Information List

1. `NO EVIDENCE` What we still do not know: whether users pay, trust, complete, improve, or get better outcomes.
2. `NO EVIDENCE` Missing respondent types: buyers, non-buyers, near-buyers, successful candidates, rejected candidates, hiring-side reviewers, and users of alternatives.
3. `NO EVIDENCE` Missing non-buyer evidence: no refusal reasons, cancellation reasons, or price objections.
4. `NO EVIDENCE` Missing consideration set: alternatives must be studied later in a separate allowed research phase.
5. `NO EVIDENCE` Missing near-purchase barriers: source trust, privacy, price, time-to-output, AI voice, hallucination risk, and restricted-source concern.
6. `NO EVIDENCE` Missing price threshold: no payment behavior.
7. `NO EVIDENCE` Unclear first Aha: source-backed specificity, story mapping, gap detection, or Lua feedback may be the Aha.
8. `NO EVIDENCE` Whether alternatives were explored: no customer comparison evidence in repo.
9. `NO EVIDENCE` Whether willingness to pay is behavior or opinion: no payment behavior exists.
10. `NO EVIDENCE` Whether payment evidence exists: not in this Phase 1 evidence.
11. `NO EVIDENCE` Whether stated interest is separated from observed behavior: not proven.
12. `FIELD DATA` What evidence would change the conclusion: paid concierge usage, source trust scoring, observed answer revision, non-buyer reasons, and outcome follow-up.

## 9. Source Inventory

Files read:

- `docs/nmt/codex_prompts/10_AGNOSTIC_ADVANCED_NMT_RESEARCH.txt`
- `docs/nmt/_harness/CODEX_NMT_HARNESS_ADVANCED.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/RUN_MANIFEST.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/input/01_business_input.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/input/02_prior_research_index.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/input/03_chat_feedback.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/input/04_agnostic_methodology.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/input/04_claude_harness_docs.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/input/05_validation_rules.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/state/EVIDENCE_LEDGER.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/state/NMT_RUN_STATE.md`
- `docs/nmt/_source_library/projects/nailit/prior_research/00_read_first/NAILIT_SOURCE_COMPLETENESS.md`
- `docs/nmt/_source_library/projects/nailit/prior_research/00_read_first/SOURCE_CLASSIFICATION_LEDGER.md`
- `docs/nmt/_source_library/projects/nailit/prior_research/README_FIRST.md`
- `docs/nmt/_source_library/projects/nailit/prior_research/active_product_sources/MASTER_INDEX_2026_07_03.md`
- `docs/nmt/_source_library/projects/nailit/prior_research/active_product_sources/NAILIT_MASTER_2026_07_03.md`
- `docs/nmt/_source_library/projects/nailit/prior_research/active_research_context/NAILIT_NMT_FULL_CANON_RUN_2026_07_04.md`
- `api.py`
- `agent_v2.py`
- `lua_brief_builder.py`
- `lua_coach.py`
- `answer_generator.py`
- `job_store.py`
- `tests/test_validation_readiness_static.py`
- `tests/test_dynamic_readiness_contracts.py`
- `.github/workflows/backend-tests.yml`
- `/Users/asia/.agents/skills/nmt-diagnose/SKILL.md`

Files not used:

- Wrong-category external research.
- Public web.
- External market research.

## 10. Source Classification

| Source | Label | Use |
| --- | --- | --- |
| `api.py`, `agent_v2.py`, `lua_brief_builder.py`, `lua_coach.py`, `answer_generator.py`, `job_store.py` | `REPO FACT` | Primary implementation evidence |
| `tests/test_validation_readiness_static.py`, `tests/test_dynamic_readiness_contracts.py`, CI workflow | `TESTED` | Contract and safety evidence |
| Run manifest/input/state/prior research | `DOC CLAIM` | Scope, rules, and context only |
| NMT skill/workbench docs | Methodology input | Diagnostic frame |
| Wrong-category external research | Excluded | Not evidence |

## 11. Evidence Extraction

### Auth and safety

- `REPO FACT` App-key auth checks `X-App-Key` in `api.py:87-91`.
- `REPO FACT` `X-App-Key` is allowed in CORS headers in `api.py:255`.
- `TESTED` Sensitive-route protection is statically checked in `tests/test_validation_readiness_static.py:83-117`.
- `TESTED` Missing app key rejection is dynamically checked in `tests/test_dynamic_readiness_contracts.py:94-107`.

### Payment and contribution

- `REPO FACT` Stripe webhook verifies signature and credits users in `api.py:159-178`.
- `REPO FACT` `check_and_deduct` says it is not wired pending auth integration in `api.py:182-187`.
- `REPO FACT` Checkout creation returns protected 501 not-ready in `api.py:311-319`.
- `REPO FACT` Contribution/outcome capture returns protected 501 not-ready in `api.py:322-330`.
- `TESTED` Payment/credit wiring static checks are in `tests/test_validation_readiness_static.py:171-203`.
- `TESTED` Runtime checkout/contribution not-ready contracts are checked in `tests/test_dynamic_readiness_contracts.py:108-123`.

### Email and followup

- `REPO FACT` Email delivery is not configured/implemented in `api.py:109-129`.
- `REPO FACT` Followups are protected and call `send_email` in `api.py:132-156`.
- `REPO FACT` Follow-up selection requires email in `job_store.py:407-418`.
- `TESTED` Email/contribution static checks are in `tests/test_validation_readiness_static.py:206-231`.
- `TESTED` Runtime followup returns email-provider-not-configured without sending real email in `tests/test_dynamic_readiness_contracts.py:163-185`.

### GDPR and persistence

- `REPO FACT` `create_session` stores `user_email` and `user_id` in `job_store.py:307-341`.
- `REPO FACT` Credits and transactions exist in `job_store.py:438-492`.
- `REPO FACT` Data deletion handles sessions, jobs/workspaces, credits, credit transactions, and Lua stores in `job_store.py:520-563`.
- `REPO FACT` Data export returns sessions and credit balance in `job_store.py:593-615`.
- `TESTED` Static GDPR coverage checks are in `tests/test_validation_readiness_static.py:120-168`.
- `TESTED` Dynamic isolated GDPR deletion/export is tested in `tests/test_dynamic_readiness_contracts.py:133-162`.

## 12. Original NMT Core Preservation Check

`REPO FACT` The local prompt/harness requires Advanced JTBD, Job Graph, Critical Chain, Segment + Job, value creation mechanics, RAT/RIT, ABCDX, Unit Economics, Theory of Constraints, subtraction, local/global optimum, behavior switching, consideration set, field validation, validation debt, and evidence hierarchy.

`MODEL INFERENCE` This report applies those passes to NailIt as an existing product with weak validation, not as a generic startup checklist and not as a wrong-category product.

`UNAVAILABLE_SOURCE` Any unavailable/paywalled methodology areas are not invented.

## 13. Enhancement Layer Preservation Check

`REPO FACT` This report preserves claim tagging, prior-doc DOC CLAIM discipline, no carryover, repo-first evidence, validation debt, missing-information discipline, GO-as-validation-not-build, payment-evidence separation, non-buyer evidence gap, and BLOCKED/PROCEED gates.

## 14. Layer 1 End-to-End Trace

Layer 1 = company-specific interview-pack generation.

1. `REPO FACT` User input schema: company, role, JD, CV, extra in `api.py:259-264`.
2. `REPO FACT` `/prepare` protected endpoint accepts the schema and calls `run_pipeline` in `api.py:344-352`.
3. `REPO FACT` `/prepare` reads `prep_pack.md`, product JSON, and `lua_brief.json` in `api.py:354-367`, then returns them in `api.py:369-375`.
4. `REPO FACT` Async prep creates and dispatches jobs in `api.py:615-628`; status is returned in `api.py:631-636`.
5. `REPO FACT` Source plan generation creates company/role/JD/source queries in `agent_v2.py:517-580`.
6. `REPO FACT` Source collection parses provided external bridge sources if present, otherwise logs no bridge in `agent_v2.py:583-599`.
7. `REPO FACT` Source collection caps, dedupes, and writes source manifest/mix in `agent_v2.py:600-654`.
8. `REPO FACT` Company intelligence structure and source-confidence rules are in `agent_v2.py:768-828`.
9. `REPO FACT` Gap map uses candidate/JD/research objects and forbids invented candidate evidence in `agent_v2.py:2441-2479`.
10. `REPO FACT` Interview strategy emits likely questions, dangerous questions, answer outlines, company/role maps, and prep plan in `agent_v2.py:2661-2730`.
11. `REPO FACT` Strategy requires JD signal, candidate gap, and research signal for every question; no generic questions; no new stories/metrics in `agent_v2.py:2732-2736`.
12. `REPO FACT` Company signals must be real or marked insufficient, not generic filler, in `agent_v2.py:2752-2758`.
13. `REPO FACT` Pack assembly sections are defined in `agent_v2.py:4489-4623`.
14. `REPO FACT` Full pipeline stages and Lua brief creation are in `agent_v2.py:6311-6417`.
15. `REPO FACT` Pipeline writes all major artifacts and `lua_brief.json` in `agent_v2.py:6461-6494`.

Layer 1 verdict:

`REPO FACT` Implemented.

`BLOCKED` for claims of validated source sufficiency, validated quality, payment, or outcome improvement.

## 15. Layer 2 End-to-End Trace

Layer 2 = Lua AI mock interview based on the generated pack.

1. `REPO FACT` Layer 1 passes research, JD analysis, candidate profile, gap map, story bank, and question-answer bank into `build_lua_mock_interview_brief` in `agent_v2.py:6397-6406`.
2. `REPO FACT` Lua brief builder defines the brief function in `lua_brief_builder.py:5`.
3. `REPO FACT` Lua brief output type is `nailit_lua_mock_interview_brief` in `lua_brief_builder.py:26`.
4. `REPO FACT` Lua brief rules include asking one question at a time and scoring every candidate answer in `lua_brief_builder.py:40-43`.
5. `REPO FACT` Lua brief scoring dimensions are in `lua_brief_builder.py:53-64`.
6. `REPO FACT` `/lua-coach` calls Lua coach response generation with company, role, question, answer, and brief in `api.py:653-662`.
7. `REPO FACT` `/lua-coach-resume` stores user turns, waits for final answer, then builds/stores/returns adapted coach feedback in `api.py:690-721`.
8. `REPO FACT` `/lua-call-turn` stores transcript turns, waits when not final, builds answer context, generates coach response, stores feedback, and returns adapted output in `api.py:725-781`.
9. `REPO FACT` `/lua-benchmark-question` generates and stores benchmark questions in `api.py:794-806`.
10. `REPO FACT` `/lua-practice-benchmark-turn` generates feedback, pressure follow-up, mastery update, and practice event storage in `api.py:824-875`.
11. `REPO FACT` Lua health/state endpoints exist in `api.py:950-976`.
12. `REPO FACT` Lua coach response schema contains `score_out_of_10`, `adaptive_follow_up_question`, and `move_on_allowed` in `lua_coach.py:170-193`.
13. `REPO FACT` Lua adapter maps the score and returns "Try again" below 7 or "Ready for next question" otherwise in `lua_coach.py:227-238`.

Layer 2 verdict:

`REPO FACT` Implemented.

`BLOCKED` for claims that Lua scoring is trusted, accurate, behavior-changing, or outcome-improving.

## 16. Advanced JTBD Diagnosis

Likely Core Job:

`HYPOTHESIS` "I want to prepare for a specific upcoming interview using company-specific signals, my own evidence, and realistic practice so I can answer credibly under pressure."

Big Job:

`HYPOTHESIS` Improve chances of succeeding in a high-stakes interview.

Small Jobs:

- `REPO FACT` Decode JD and company context through Layer 1 artifacts.
- `REPO FACT` Map CV/proof points to role/company signals.
- `REPO FACT` Identify gaps and risky questions.
- `REPO FACT` Practice answers with Lua scoring and feedback.

`NO EVIDENCE` This is not yet proven as the paid dominant Job.

## 17. Job Structure

State A:

`HYPOTHESIS` Candidate has an interview target, scattered information, uncertain answer quality, and limited time.

State B:

`HYPOTHESIS` Candidate has a structured company-specific prep pack, credible answer angles, known gaps, and practiced answers.

Higher-level Job:

`HYPOTHESIS` Win the interview or materially improve interview performance.

## 18. Job Graph

1. `HYPOTHESIS` Interview trigger creates urgency.
2. `REPO FACT` Candidate submits company/role/JD/CV/extra inputs in `api.py:259-264`.
3. `REPO FACT` Pipeline creates source plan and parses supplied source bridge in `agent_v2.py:517-654`.
4. `REPO FACT` Pipeline builds candidate/JD/research/gap/strategy artifacts in `agent_v2.py:6315-6355`.
5. `REPO FACT` Pipeline validates and assembles pack in `agent_v2.py:6356-6395`.
6. `REPO FACT` Pipeline builds Lua brief in `agent_v2.py:6397-6406`.
7. `REPO FACT` Lua routes run question/answer/feedback loops in `api.py:653-875`.
8. `NO EVIDENCE` Candidate changes behavior, pays, or performs better.

## 19. Critical Chain of Jobs

`HYPOTHESIS` The critical chain is:

1. Get reliable company/interview/role signals.
2. Convert signals into likely evaluation criteria and questions.
3. Select candidate proof and repair gaps.
4. Build credible answers without unsupported claims.
5. Practice under realistic pressure.
6. Improve actual interview performance.

`STRONG INFERENCE` The weakest links are source reliability, user trust, payment behavior, and measured outcome improvement.

## 20. Segment + Job Analysis

`HYPOTHESIS` Best initial segment is candidates with a real named-company interview soon enough to need urgent prep.

`NO EVIDENCE` There is no repo-grounded proof that this segment pays, or that a different segment is better.

Do not reduce the segment to demographics. The useful segmentation axis is interview urgency, role/company specificity, source difficulty, career stakes, and confidence gap.

## 21. Value Creation Analysis

`REPO FACT` NailIt creates a structured pack with interview process map, company signals, role signals, candidate fit, gaps, likely/dangerous questions, best answer outlines, evidence ledger, and prep checklist in `agent_v2.py:4489-4623`.

`REPO FACT` NailIt creates Lua practice input from the pack in `agent_v2.py:6397-6406` and `lua_brief_builder.py:5-64`.

`HYPOTHESIS` Value exists if the product saves research time, increases company-specificity, prevents weak/unsupported answers, and improves practice quality.

`NO EVIDENCE` The repo does not prove users perceive or pay for that value.

## 22. Value-Creation Mechanics

- `REPO FACT` Aggregation: research plan/source manifest in `agent_v2.py:517-654`.
- `REPO FACT` Translation: company/JD/candidate/research objects into strategy in `agent_v2.py:2661-2766`.
- `REPO FACT` Personalization: gap map and story assignments in `agent_v2.py:2441-2479`.
- `REPO FACT` Risk reduction: validation before pack in `agent_v2.py:6356-6390`.
- `REPO FACT` Practice loop: Lua coach/benchmark/practice endpoints in `api.py:653-875`.
- `NO EVIDENCE` The actual Aha moment is not proven.

## 23. Aha Moment

Possible Aha moments:

- `HYPOTHESIS` "This pack is specific to my target company and role."
- `HYPOTHESIS` "It shows the exact gaps I must repair."
- `HYPOTHESIS` "It turns my real experience into stronger answers."
- `HYPOTHESIS` "Lua gives concrete feedback I can act on."

`NO EVIDENCE` The repo does not prove which Aha drives payment or usage.

## 24. Barriers, Fears, Habit, and Tax Jobs

Barriers:

- `NO EVIDENCE` Source trust and source permission.
- `NO EVIDENCE` Privacy concerns around CV/JD/interview data.
- `NO EVIDENCE` Fear of AI-written answers.
- `REPO FACT` Checkout not ready in `api.py:311-319`.
- `REPO FACT` Outcome capture not ready in `api.py:322-330`.
- `REPO FACT` Email not ready in `api.py:109-129`.

Habit:

`HYPOTHESIS` Candidates likely use free search/chat, public reports, friends, mentors, and coaches. This needs a separate allowed research phase.

Tax Jobs:

`HYPOTHESIS` Source gathering, credibility checking, translating signals into personal answers, and repeated practice are the costly tasks.

## 25. Behavior Change and Switching Logic

`HYPOTHESIS` NailIt requires switching from self-directed prep to a structured pack-plus-practice loop.

Switching must overcome:

- `NO EVIDENCE` Trust in source accuracy.
- `NO EVIDENCE` Trust in AI feedback.
- `NO EVIDENCE` Willingness to upload sensitive data.
- `NO EVIDENCE` Willingness to pay.
- `NO EVIDENCE` Belief that company-specific prep beats cheaper alternatives.

## 26. Consideration Set and Alternatives

`NO EVIDENCE` This phase did not research alternatives.

`HYPOTHESIS` Alternatives to study later include generic AI chat, search, company pages, public interview reports, coaches, peers, and generic interview banks.

## 27. Consideration Activators

`HYPOTHESIS` Likely activators:

- Interview invite.
- Fear of unknown company process.
- Role/company mismatch anxiety.
- Previous interview failure.
- High career stakes.

`NO EVIDENCE` Acquisition timing and channel reach are not proven.

## 28. RAT/RIT and Assumption Stack

Deadliest assumption:

`HYPOTHESIS` Candidates with real upcoming interviews will pay because source-backed company-specific prep plus Lua feedback beats their current alternatives.

Assumption stack:

1. `NO EVIDENCE` The target segment has urgent enough pain.
2. `NO EVIDENCE` Sources are sufficient and trustworthy.
3. `NO EVIDENCE` The generated pack is better than alternatives.
4. `NO EVIDENCE` Lua feedback is trusted.
5. `NO EVIDENCE` Users will pay.
6. `NO EVIDENCE` Users can be reached at the trigger moment.
7. `REPO FACT` Self-serve payment and contribution capture are not ready in `api.py:311-330`.

Cheapest falsification:

`FIELD DATA` Paid concierge test with real upcoming interviews, audited source pack, observed Lua practice, non-buyer logging, and outcome follow-up.

## 29. ABCDX Applicability

`NO EVIDENCE` ABCDX cannot be scored because there is no customer/user/revenue/retention/satisfaction/support/margin data.

`BLOCKED` for ABCDX scoring.

## 30. Unit Economics Applicability

`REPO FACT` Credits and transactions exist in `job_store.py:438-492`.

`REPO FACT` Stripe webhook crediting exists in `api.py:159-178`.

`REPO FACT` Checkout is blocked and deduction not wired in `api.py:182-187` and `api.py:311-319`.

`NO EVIDENCE` Price, margin, model cost per pack, support cost, CAC, LTV, payback, and refund data are absent.

`BLOCKED` for unit economics conclusions.

## 31. Theory of Constraints / Binding Constraint

`STRONG INFERENCE` The binding constraint is not feature volume. It is validated trust and payment for a source-backed interview-prep outcome.

Why:

- `REPO FACT` Product surface already includes Layer 1 and Layer 2.
- `REPO FACT` Self-serve payment/contribution/email are not-ready.
- `NO EVIDENCE` Customer trust, payment, non-buyer, and outcome evidence are absent.

## 32. Subtraction

Do not build yet:

- `STRONG INFERENCE` More pack sections.
- `STRONG INFERENCE` More source-surface expansion.
- `STRONG INFERENCE` More Lua feature depth.
- `STRONG INFERENCE` Venture/scale narrative.
- `STRONG INFERENCE` Self-serve launch features beyond what validation needs.

Preserve:

- `REPO FACT` Explicit 501 not-ready contracts for payment/contribution/email.
- `TESTED` Readiness tests.
- `REPO FACT` Evidence labeling and source discipline.

## 33. Focus / Company Attention Management

`STRONG INFERENCE` Focus should move to controlled validation design, not more build.

Highest learning per effort:

1. `PAYMENT EVIDENCE` Ask real candidates to pay.
2. `FIELD DATA` Audit whether source-backed specificity is valuable.
3. `FIELD DATA` Observe Lua practice behavior.
4. `FIELD DATA` Capture non-buyer evidence.

## 34. Local Optimum vs Global Optimum

Local optimum:

`STORY RISK` Improve generated pack completeness and Lua sophistication.

Global optimum:

`HYPOTHESIS` Find the Segment + Job where source-backed company-specific prep creates paid value better than alternatives.

## 35. Main Algorithm / Cyclical Next-Move Logic

1. `REPO FACT` Product surface exists.
2. `TESTED` Safety/readiness contracts exist.
3. `NO EVIDENCE` Customer/payment/outcome evidence is missing.
4. `STRONG INFERENCE` Next move is validation design.
5. `FIELD DATA` Run controlled paid concierge validation.
6. `FIELD DATA` Use results to update Segment + Job, value mechanics, and source strategy.

## 36. Cause-and-Effect Chain to Profit

- Market with money: `NO EVIDENCE`
- Segment + Job: `HYPOTHESIS`
- Added value: `REPO FACT` implemented, `NO EVIDENCE` validated
- Unit economics: `NO EVIDENCE`
- Demand/acquisition: `NO EVIDENCE`
- Conversion/retention/repeat: `NO EVIDENCE`
- Target profit: `NO EVIDENCE`

`BLOCKED` for profit-chain claims.

## 37. Field Validation Gate

Before self-serve launch:

- `PAYMENT EVIDENCE` Users pay before delivery.
- `FIELD DATA` Non-buyers and near-buyers are logged.
- `FIELD DATA` Source sufficiency is audited.
- `FIELD DATA` Users rate trust and usefulness of specific sections.
- `FIELD DATA` Lua practice creates observed answer revision.
- `FIELD DATA` Interview outcome follow-up is captured.
- `REPO FACT` Payment/contribution/email/user identity are no longer not-ready.

## 38. Non-Buyer / Non-User Evidence Gap

`NO EVIDENCE` No non-buyer or non-user evidence exists in this repo-grounded run.

Need:

- refusal reasons
- alternative chosen
- price threshold
- privacy/source trust objections
- whether company-specificity matters

## 39. Payment Evidence Gap

`REPO FACT` Payment infrastructure is partial: webhook and credits exist in `api.py:159-178` and `job_store.py:438-492`.

`REPO FACT` Checkout and paid deduction are not ready in `api.py:182-187` and `api.py:311-319`.

`NO EVIDENCE` No payment behavior exists.

## 40. False Positive Risk

1. `STORY RISK` Treating implemented features as validation.
2. `STORY RISK` Treating source plans as source reliability.
3. `STORY RISK` Treating AI scoring as outcome improvement.
4. `STORY RISK` Treating DOC CLAIM prior research as truth.
5. `STORY RISK` Treating stated interest as payment evidence.
6. `STORY RISK` Treating wrong-category research as relevant.

## 41. What Would Kill This Product

- `FIELD DATA` Real candidates refuse to pay after seeing a sample.
- `FIELD DATA` Source data is too sparse, stale, or untrusted.
- `FIELD DATA` Users prefer cheaper/free alternatives.
- `FIELD DATA` Users distrust AI scoring or answer examples.
- `FIELD DATA` Lua practice does not change answers or behavior.
- `FIELD DATA` Acquisition at interview-trigger moment is unreachable or too costly.

## 42. What Not to Build

Do not build:

- `STRONG INFERENCE` more product surface before payment/source/trust validation
- `STRONG INFERENCE` broad self-serve launch
- `STRONG INFERENCE` additional external-source integrations before source policy/sufficiency is validated
- `STRONG INFERENCE` Series A or scale story
- `STRONG INFERENCE` more answer variants without evidence of Aha

## 43. Controlled Concierge vs Self-Serve

`PROCEED` controlled concierge validation:

- manual source QA
- manual or semi-automated pack generation
- manual payment/deposit
- observed Lua-style practice
- non-buyer capture
- outcome follow-up

`BLOCKED` self-serve launch:

- checkout 501
- contribution capture 501
- email not configured
- app-key auth only
- no payment/source/outcome evidence

## 44. Product Readiness

`REPO FACT` Backend product surface exists for Layer 1 and Layer 2.

`TESTED` Contracts are tested in static/dynamic readiness tests.

`BLOCKED` for open self-serve paid validation.

`PROCEED` for manually controlled validation if privacy/source/payment boundaries are explicit.

## 45. Validation Readiness

`PROCEED` for concierge validation preparation.

`BLOCKED` for market demand claims, source sufficiency claims, payment readiness claims, Lua outcome claims, and broad launch.

## 46. Final Recommendation

`STRONG INFERENCE` Stop product expansion. Run a paid, controlled concierge validation sprint focused on whether candidates with real upcoming interviews will pay for and trust source-backed company-specific prep plus Lua feedback.

## 47. BLOCKED / PROCEED by Category

| Category | Status | Evidence |
| --- | --- | --- |
| Repo-grounded Layer 1 implementation | `PROCEED` | `api.py:259-264`, `api.py:344-375`, `agent_v2.py:6311-6494` |
| Repo-grounded Layer 2 implementation | `PROCEED` | `agent_v2.py:6397-6406`, `lua_brief_builder.py:5-64`, `api.py:653-875`, `lua_coach.py:170-238` |
| Controlled concierge validation | `PROCEED` | `STRONG INFERENCE` from product surface and missing validation |
| Self-serve paid launch | `BLOCKED` | checkout/contribution/email not-ready in `api.py:109-129`, `api.py:311-330` |
| Payment readiness | `BLOCKED` | `api.py:182-187`, `api.py:311-319` |
| Source sufficiency | `BLOCKED` | source plan/bridge only in `agent_v2.py:517-654` |
| Market demand | `BLOCKED` | no external research in Phase 1; no payment evidence |
| Lua outcome claims | `BLOCKED` | implementation only, no field outcome data |
| More build | `BLOCKED` | binding constraint is validation/trust/payment |

## 48. Evidence Used

Exact repo/test anchors used:

- `api.py:87-91`
- `api.py:109-129`
- `api.py:132-178`
- `api.py:182-187`
- `api.py:259-276`
- `api.py:311-330`
- `api.py:344-375`
- `api.py:401-434`
- `api.py:444-482`
- `api.py:535-604`
- `api.py:615-662`
- `api.py:690-781`
- `api.py:794-875`
- `api.py:950-976`
- `agent_v2.py:517-654`
- `agent_v2.py:768-828`
- `agent_v2.py:2441-2479`
- `agent_v2.py:2661-2766`
- `agent_v2.py:4489-4623`
- `agent_v2.py:6311-6494`
- `lua_brief_builder.py:5-64`
- `lua_coach.py:29-66`
- `lua_coach.py:86-238`
- `job_store.py:307-341`
- `job_store.py:407-418`
- `job_store.py:438-492`
- `job_store.py:520-563`
- `job_store.py:593-615`
- `tests/test_validation_readiness_static.py:83-245`
- `tests/test_dynamic_readiness_contracts.py:90-211`
- `.github/workflows/backend-tests.yml:18-39`

## 49. What Was Not Checked

- `NO EVIDENCE` No public web.
- `NO EVIDENCE` No external market research.
- `NO EVIDENCE` No live OpenAI/Tavily/Stripe/email calls.
- `NO EVIDENCE` No frontend inspection in this phase.
- `NO EVIDENCE` No live production database mutation.
- `NO EVIDENCE` No real candidate sessions.
- `NO EVIDENCE` No legal/source-access review.
- `NO EVIDENCE` No live generated-pack quality test with model calls.

## 50. What Would Change the Conclusion

Conclusion improves if:

- `PAYMENT EVIDENCE` Real scheduled-interview users pay before delivery.
- `FIELD DATA` Source audits show sufficient reliable company/role signal.
- `FIELD DATA` Users identify a clear first Aha.
- `FIELD DATA` Users revise answers after Lua feedback.
- `FIELD DATA` Non-buyers reveal fixable objections.
- `FIELD DATA` Outcome follow-up suggests interview-performance improvement.

Conclusion worsens if:

- `FIELD DATA` Users refuse to pay.
- `FIELD DATA` Users prefer free alternatives.
- `FIELD DATA` Source data is sparse, stale, or untrusted.
- `FIELD DATA` Users distrust AI answer examples or Lua scores.

## 51. Next Lowest Cost Action

`PROCEED` with a controlled concierge validation design document, not more product build.

Minimum next artifact:

1. `FIELD DATA` Candidate eligibility criteria.
2. `PAYMENT EVIDENCE` Payment/deposit ask.
3. `FIELD DATA` Source audit rubric.
4. `FIELD DATA` Pack usefulness scoring sheet.
5. `FIELD DATA` Lua practice observation sheet.
6. `FIELD DATA` Non-buyer interview script.
7. `FIELD DATA` Outcome follow-up script.

## 52. Final BLOCKED or PROCEED

`PROCEED` for controlled concierge validation preparation.

`BLOCKED` for self-serve paid launch, market demand claims, source sufficiency claims, payment readiness claims, Lua outcome claims, Series A claims, and more feature build as the next move.

