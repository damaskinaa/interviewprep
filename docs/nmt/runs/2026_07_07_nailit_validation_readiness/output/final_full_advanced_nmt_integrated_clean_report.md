# Final Full Advanced NMT Integrated Clean Report

Run: `2026_07_07_nailit_validation_readiness`
Product: NailIt
Scope: AI interview preparation only
Inputs used:

1. Phase 1 repo-grounded report: `docs/nmt/runs/2026_07_07_nailit_validation_readiness/output/full_advanced_nmt_repo_grounded_research_report.md`
2. Phase 2 external market research report: `docs/nmt/runs/2026_07_07_nailit_validation_readiness/output/full_advanced_nmt_external_market_research_report.md`
3. Run manifest and specified NMT harness/input files

Inputs rejected:

1. Contaminated wrong-category external research
2. Invalid integrated report at `docs/nmt/runs/2026_07_07_nailit_validation_readiness/output/full_advanced_nmt_integrated_research_report.md`
3. `docs/nmt/_source_library/projects/nailit/external_research/deep_research_on_nail_it_2026_07_07.docx`

Production code changes: none.
Commit: none.

## 1. Final Executive Verdict

`STRONG INFERENCE` NailIt is not invalidated. Phase 1 shows a real backend product surface for two connected layers: company-specific interview prep pack generation and Lua mock-interview coaching. Phase 2 shows an active external interview-prep market with paid substitutes and clear trust risks.

`BLOCKED` Market demand for NailIt's exact company-specific pack plus Lua mock-interview loop is not proven.

`BLOCKED` Open self-serve paid launch remains blocked because Phase 1 found checkout creation, contribution/outcome capture, and email delivery explicitly not-ready, with no repo evidence of payment behavior or outcome improvement.

`PROCEED` The next move is controlled concierge validation with real scheduled-interview candidates, paid deposit/price test, source audit, observed Lua-style practice, non-buyer capture, and outcome follow-up.

## 2. Product Identity and Scope Lock

`REPO FACT` NailIt is an AI interview preparation product. Phase 1 identifies interview-specific input models in `api.py:259-276`, including company, role, job description, CV, answer bank, company context, transcripts, user email, and user ID.

`REPO FACT` Layer 1 is company-specific interview-pack generation, anchored in `/prepare` and the full pipeline: `api.py:344-375`, `agent_v2.py:6311-6417`, and `agent_v2.py:6461-6494`.

`REPO FACT` Layer 2 is Lua mock-interview coaching based on the generated pack, anchored in `agent_v2.py:6397-6406`, `lua_brief_builder.py:5-64`, `api.py:653-875`, and `lua_coach.py:86-238`.

`BLOCKED` Any wrong-category consumer-service, visual-preview, or appointment-market source is excluded and is not evidence for NailIt.

## 3. Evidence Base Used

`REPO FACT` Phase 1 repo evidence used exact anchors from `api.py`, `agent_v2.py`, `lua_brief_builder.py`, `lua_coach.py`, `answer_generator.py`, `job_store.py`, readiness tests, and CI.

`TESTED` Phase 1 cited static and dynamic tests for route protection, GDPR/data deletion coverage, payment/contribution not-ready contracts, email not-ready behavior, Lua route protection, temp-store deletion, and disabled provider/network keys in `tests/test_validation_readiness_static.py:83-245` and `tests/test_dynamic_readiness_contracts.py:90-211`.

`EXTERNAL FACT` Phase 2 used 24 external sources in the AI interview-prep market, including Interviewing.io, Final Round AI, Huru, Big Interview, Yoodli, Pramp, Exponent, InterviewBuddy, The Muse, MentorCruise, EEOC, NIST, The Guardian, arXiv papers, and Business Insider.

`DOC CLAIM` The run manifest and business input define NailIt's intended scope, but explicitly state that the input is not evidence that people will pay.

## 4. Evidence Base Rejected

`BLOCKED` The contaminated external research DOCX is excluded.

`BLOCKED` The invalid integrated report is excluded.

`BLOCKED` Any source that does not describe AI interview preparation, company-specific interview prep, mock interview coaching, candidate willingness to pay, candidate privacy/trust concerns, or interview-prep substitutes is excluded.

`NO EVIDENCE` No rejected source is used to support product, market, pricing, competitor, segment, or validation conclusions in this report.

## 5. Phase 1 Repo-Grounded Findings

`REPO FACT` Layer 1 is implemented. The input contract is in `api.py:259-264`; `/prepare` calls `run_pipeline` in `api.py:344-352`; `/prepare` returns markdown, product JSON, and Lua brief output in `api.py:354-375`; the full pipeline runs candidate extraction, JD analysis, source handling, gap map, strategy, validation, pack assembly, evidence ledger, and Lua brief generation in `agent_v2.py:6311-6417`.

`REPO FACT` Source planning and bridge parsing exist, but Phase 1 did not prove live source sufficiency. Source planning appears in `agent_v2.py:517-580`; source collection parses supplied bridge data when present in `agent_v2.py:583-596`; when absent it logs no bridge in `agent_v2.py:597-599`.

`REPO FACT` Layer 2 is implemented. The pipeline passes research, JD analysis, candidate profile, gap map, story bank, and question-answer bank into the Lua brief in `agent_v2.py:6397-6406`. Lua brief rules include one-question-at-a-time and scoring every candidate answer in `lua_brief_builder.py:40-43`, with scoring dimensions in `lua_brief_builder.py:53-64`.

`REPO FACT` Lua routes support coaching, resume, call-turn, benchmark question, practice feedback, pressure follow-up, mastery, and session/state behavior in `api.py:653-875` and `api.py:950-976`.

`TESTED` Backend readiness contracts are tested, but tests do not prove market demand, payment behavior, source sufficiency, user trust, or interview outcome improvement.

`BLOCKED` Checkout creation returns protected 501 `payment_checkout_not_ready` in `api.py:311-319`; contribution/outcome capture returns protected 501 `contribution_capture_not_ready` in `api.py:322-330`; email delivery is explicitly not configured/implemented in `api.py:109-129`.

## 6. Phase 2 External Market Findings

`MARKET SIGNAL` Phase 2 found an active interview-prep market with paid substitutes: human mock interviews, expert coaching, peer mock practice, AI roleplay, AI mock interviews, and role-specific subscriptions.

`PRICING SIGNAL` External price points support testing payment for interview prep generally: Interviewing.io premium interviews start at $179; Big Interview lists $39/month, $99/3 months, and $299 lifetime; The Muse lists interview coaching from $155 to $659; Huru lists $24.99/month and $99/year; Yoodli lists $8/month and $20/month annual-billed individual tiers; InterviewBuddy lists one-on-one sessions from Rs 1,499; Exponent lists paid access for courses, peer mocks, community, and AI features.

`TRUST RISK` Phase 2 found material trust concerns around AI in hiring and interviewing: EEOC warns that AI and algorithmic employment tools may mask or perpetuate bias; NIST frames AI trustworthiness as an explicit risk-management concern; The Guardian reported job-seeker frustration with AI-led interviews; Business Insider reported employer/candidate tension around AI use in interviews.

`NO EVIDENCE` Phase 2 did not prove that users will pay for NailIt's exact company-specific pack plus Lua mock-interview loop.

## 7. Combined Market + Product Diagnosis

`STRONG INFERENCE` The product is technically plausible and market-adjacent, but not market-validated. Phase 1 proves meaningful backend implementation; Phase 2 proves a market with substitutes and price points; neither proves NailIt's exact wedge has demand.

`STRONG INFERENCE` NailIt should not compete as a generic AI mock-interview tool. That market is crowded by Huru, Final Round AI, Big Interview, Yoodli, Interviewing.io AI Interviewer, and generic LLMs.

`STRONG INFERENCE` NailIt's best current wedge is source-backed, company-specific prep plus a practice loop grounded in the generated pack.

`BLOCKED` The venture/scale narrative, broad self-serve launch, and more feature build are premature until payment, source trust, user trust, and outcome signals exist.

## 8. Segment + Job

Primary segment hypothesis:

`HYPOTHESIS` Candidates with a real upcoming interview at a named company, especially where company context, role fit, story selection, and answer credibility matter.

Core Job:

`HYPOTHESIS` When I have an interview with a specific company soon, I want to turn my background, the JD, and credible company/interview signals into strong answers and realistic practice, with confidence that I am not inventing claims, so I can perform better in the interview.

`MARKET SIGNAL` Phase 2 supports urgency around scheduled interviews through short-window and high-stakes prep products such as Big Interview's bootcamp framing, Interviewing.io paid mocks, InterviewBuddy pressure-simulation framing, and human coaching offers.

`NO EVIDENCE` This segment has not yet been proven as NailIt's paid dominant segment.

## 9. Consideration Set and Alternatives

Direct AI interview-prep competitors:

- `EXTERNAL FACT` Huru: AI video mock interview and feedback.
- `EXTERNAL FACT` Final Round AI: AI mock interview and live interview assistance positioning.
- `EXTERNAL FACT` Big Interview: interview training platform with AI feedback.
- `EXTERNAL FACT` Yoodli: AI roleplay and communication coaching.
- `EXTERNAL FACT` Interviewing.io AI Interviewer: AI interviewer/practice alternative.

Substitutes:

- `EXTERNAL FACT` Human mock interviews and coaching: Interviewing.io, The Muse, MentorCruise, InterviewBuddy.
- `EXTERNAL FACT` Peer practice: Pramp and Exponent practice/community.
- `EXTERNAL FACT` Role-specific prep: Exponent.
- `MARKET SIGNAL` Generic ChatGPT, Gemini, and Claude can generate questions, roleplay, critique answers, and ingest JDs at low cost.

`STRONG INFERENCE` Generic LLMs are the highest-pressure substitute unless NailIt proves better source discipline, company specificity, structure, and practice integration.

## 10. Differentiation: Company-Specific Prep Pack + Lua Mock Interview Loop

`REPO FACT` NailIt's differentiator is implemented as a two-layer loop: Layer 1 generates a company/role/candidate-specific pack; Layer 2 turns the pack into a Lua mock-interview brief and coaching flow.

`REPO FACT` Pack assembly includes executive strategy, candidate positioning, forbidden claims, interview process intelligence, company intelligence, interview rounds, questions and answers by round, dangerous questions, story bank, gap repair scripts, and evidence ledger in `agent_v2.py:6089-6268`.

`REPO FACT` Lua brief includes candidate strategy, company intelligence, JD decode, candidate evidence, gap map, story bank, question-answer bank, operating rules, and scoring dimensions in `lua_brief_builder.py:25-64`.

`STRONG INFERENCE` This is meaningfully different from generic question banks and generic AI chat if source quality and trust are high.

`NO EVIDENCE` External research does not prove that this differentiation is strong enough to drive payment.

## 11. Payment and Willingness-to-Pay Evidence

`PRICING SIGNAL` Phase 2 found external willingness-to-pay proxies: paid mocks, paid interview coaching, and paid AI interview-prep subscriptions exist across multiple products.

`REPO FACT` NailIt has partial payment infrastructure: Stripe webhook and crediting exist in `api.py:159-178`, and credit storage exists in `job_store.py:438-492`.

`REPO FACT` NailIt checkout creation is intentionally blocked with protected 501 in `api.py:311-319`; paid deduction is not wired into endpoints per `api.py:182-187`.

`NO EVIDENCE` NailIt has no observed payment behavior in the valid evidence base.

`NO EVIDENCE` External pricing proves substitutes charge money; it does not prove NailIt's exact product will convert at $29, $49, $99, or any other price.

## 12. Trust, Privacy, and Source-Risk Diagnosis

`TRUST RISK` NailIt asks users to provide sensitive job-search data: CV, JD, company target, answer bank, interview answers, and potentially transcripts.

`REPO FACT` GDPR export/delete routes exist and are protected in `api.py:204-213`; deletion covers sessions, jobs/workspaces, credits, credit transactions, and Lua sidecar stores in `job_store.py:520-563`; export returns sessions and credit balance in `job_store.py:593-615`.

`TRUST RISK` Phase 2 shows that privacy and trust posture are buying criteria in adjacent products. Yoodli publishes data-use distinctions by plan; Final Round AI displays compliance/security badges; Interviewing.io emphasizes anonymity.

`TRUST RISK` Source reliability remains a core risk. Phase 1 shows source planning and bridge parsing, but does not prove that public/company/interview sources are sufficient, accurate, permitted, or current.

`BLOCKED` Source sufficiency and source-access claims are blocked until audited in field validation.

## 13. AI Interview-Prep Opportunity vs AI Hiring Backlash

`MARKET SIGNAL` Candidate-side AI prep exists as a visible category: Huru, Big Interview, Yoodli, Final Round AI, Interviewing.io AI Interviewer, and Exponent AI features.

`TRUST RISK` Employer-side AI interviews and AI evaluation create backlash and legal/ethical sensitivity. EEOC and NIST sources make AI trust and fairness central; The Guardian and Business Insider sources show user/employer tension.

`STRONG INFERENCE` NailIt's safer positioning is ethical preparation before the interview, not hidden live assistance or automated employment evaluation.

`BLOCKED` Any claim that Lua scoring is fair, trusted, or outcome-improving is blocked until tested with users and outcomes.

## 14. Strongest Positive Evidence

`REPO FACT` NailIt has an implemented two-layer backend surface with exact repo anchors: Layer 1 in `api.py:259-264`, `api.py:344-375`, `agent_v2.py:6311-6494`; Layer 2 in `agent_v2.py:6397-6406`, `lua_brief_builder.py:5-64`, `api.py:653-875`, and `lua_coach.py:170-238`.

`TESTED` Static/dynamic readiness tests cover key backend contracts in `tests/test_validation_readiness_static.py:83-245` and `tests/test_dynamic_readiness_contracts.py:90-211`.

`PRICING SIGNAL` Phase 2 found multiple paid substitutes in interview prep, with visible pricing from human coaching, expert mocks, and AI interview-prep tools.

`STRONG INFERENCE` The combined evidence supports a paid validation test, not a demand claim.

## 15. Strongest Negative Evidence

`NO EVIDENCE` There is no valid evidence that NailIt's exact company-specific pack plus Lua mock-interview loop converts, improves outcomes, earns trust, or beats generic LLM/human/peer alternatives.

`REPO FACT` Checkout, contribution/outcome capture, and email delivery are not-ready in `api.py:311-330` and `api.py:109-129`.

`TRUST RISK` Candidates may resist uploading sensitive data, distrust AI feedback, or reject source claims if the pack feels generic, stale, or unsupported.

`MARKET SIGNAL` Free and cheap substitutes create price pressure, especially Pramp, Interviewing.io AI Interviewer, and generic ChatGPT/Gemini/Claude workflows.

## 16. Risky Assumption Stack

1. `HYPOTHESIS` Candidates with real scheduled interviews will pay before delivery.
2. `HYPOTHESIS` Company-specific source-backed prep is the purchase trigger, not generic practice.
3. `HYPOTHESIS` Lua feedback creates a visible answer-quality improvement.
4. `TRUST RISK` Users will trust NailIt with CV, JD, company target, and interview answers.
5. `TRUST RISK` Users will trust source provenance and AI-generated guidance.
6. `NO EVIDENCE` Public/source inputs are sufficient for enough companies and roles.
7. `NO EVIDENCE` NailIt can acquire users at the interview-trigger moment.
8. `NO EVIDENCE` NailIt has a repeatable price point.
9. `REPO FACT` Open self-serve payment/contribution/email flows are not ready.

Deadliest assumption:

`HYPOTHESIS` Real scheduled-interview candidates will pay because NailIt's source-backed company-specific pack plus Lua practice is meaningfully better than generic AI, public search, peer practice, and human coaching alternatives at the chosen price.

## 17. What Would Kill NailIt

- `NO EVIDENCE` Public/source data is too sparse, stale, inaccessible, or untrusted for target companies.
- `NO EVIDENCE` Users choose generic LLMs or free peer practice after seeing a NailIt sample.
- `NO EVIDENCE` Users refuse to pay even with real upcoming interviews.
- `TRUST RISK` Users fear uploading CV/JD/interview-answer data enough to abandon.
- `TRUST RISK` Users perceive AI feedback or answer examples as generic, risky, or inauthentic.
- `NO EVIDENCE` Lua practice does not produce observed answer revision, repeat attempts, confidence increase, or post-interview usefulness.
- `NO EVIDENCE` Acquisition at the interview-trigger moment is unreachable or too expensive.

## 18. What Would Strengthen NailIt

- `PRICING SIGNAL` Paid conversion from real scheduled-interview candidates at a repeatable price.
- `MARKET SIGNAL` Users choose NailIt over generic LLM, peer practice, or human coach alternatives after seeing a sample.
- `TRUST RISK` Risk reduced through explicit privacy, retention, deletion/export, source provenance, and no hidden live-assistance positioning.
- `REPO FACT` Payment, contribution/outcome capture, and email follow-up become production-ready after validation defines the evidence contract.
- `NO EVIDENCE` Source sufficiency becomes supported by a source-audit rubric across target companies and roles.
- `NO EVIDENCE` Lua outcome claims become supported by observed practice behavior and post-interview follow-up.

## 19. Cheapest Real-World Validation Test

`PROCEED` Run controlled concierge validation.

Test design:

1. `MARKET SIGNAL` Recruit 8-12 candidates with real interviews scheduled in the next 7-14 days.
2. `PRICING SIGNAL` Ask for a deposit or payment before delivery. Test $29, $49, and $99 as hypotheses anchored by Phase 2 substitute pricing, not as proven NailIt prices.
3. `TRUST RISK` Use an explicit privacy/source policy before collecting CV/JD/interview-answer data.
4. `REPO FACT` Use the existing Layer 1/Layer 2 backend surface where safe, with manual source QA and manual correction.
5. `MARKET SIGNAL` Compare against alternatives chosen or considered: generic LLM, human coach, peer practice, no prep, Interviewing.io, Huru, Big Interview, Yoodli, Pramp, Exponent, InterviewBuddy.
6. `NO EVIDENCE` Record non-buyer reasons, near-purchase barriers, price threshold, source trust rating, first Aha, answer revision, repeat attempts, referral intent, and post-interview outcome.

Kill criteria:

- `BLOCKED` Fewer than 3 of 10 candidates pay at any tested price.
- `BLOCKED` Users do not rate the company-specific pack as meaningfully better than generic AI.
- `BLOCKED` Users distrust source quality, privacy posture, or Lua feedback.
- `BLOCKED` Users do not revise or repeat answers after feedback.

## 20. What Not to Build

- `BLOCKED` Do not build more generic AI mock-interview features before validation.
- `BLOCKED` Do not build broad self-serve launch surface before payment/source/trust evidence.
- `BLOCKED` Do not expand source integrations before source sufficiency and access rules are validated.
- `BLOCKED` Do not build venture/scale story or Series A narrative from current evidence.
- `BLOCKED` Do not build live hidden-assistance positioning.
- `BLOCKED` Do not build more pack sections or answer variants until the first Aha is known.

## 21. Final Next Move

`PROCEED` Create and run a controlled concierge validation sprint.

One clear next move:

`STRONG INFERENCE` Recruit real scheduled-interview candidates and ask them to pay before delivery for a manually source-audited NailIt pack plus observed Lua-style practice session.

Phase 2 effect on Phase 1:

`STRONG INFERENCE` External research does not change the Phase 1 recommendation. It strengthens it. The market is active enough to validate, crowded enough to avoid more generic build, and trust-sensitive enough to require controlled validation before self-serve launch.

## 22. BLOCKED / PROCEED Table

| Decision area | Status | Evidence |
| --- | --- | --- |
| Product identity | `PROCEED` | `REPO FACT` interview-specific input and pipeline anchors in `api.py:259-276`, `api.py:344-375`, `agent_v2.py:6311-6417` |
| Layer 1 implementation | `PROCEED` | `REPO FACT` `api.py:344-375`, `agent_v2.py:517-654`, `agent_v2.py:6311-6494` |
| Layer 2 implementation | `PROCEED` | `REPO FACT` `agent_v2.py:6397-6406`, `lua_brief_builder.py:5-64`, `api.py:653-875`, `lua_coach.py:86-238` |
| Backend readiness contracts | `PROCEED` | `TESTED` `tests/test_validation_readiness_static.py:83-245`, `tests/test_dynamic_readiness_contracts.py:90-211` |
| External market existence | `PROCEED` | `MARKET SIGNAL` active competitors/substitutes and 24 Phase 2 sources |
| Substitute pricing | `PROCEED` | `PRICING SIGNAL` Interviewing.io, Big Interview, Huru, Yoodli, InterviewBuddy, Exponent, The Muse |
| NailIt exact willingness to pay | `BLOCKED` | `NO EVIDENCE` no NailIt payment behavior |
| Source sufficiency | `BLOCKED` | `REPO FACT` source planning/bridge parsing exists; `NO EVIDENCE` no field source audit |
| Lua outcome improvement | `BLOCKED` | `REPO FACT` Lua implementation exists; `NO EVIDENCE` no outcome evidence |
| Trust/privacy readiness | `BLOCKED` | `TRUST RISK` sensitive candidate data and AI trust concerns |
| Open self-serve paid launch | `BLOCKED` | `REPO FACT` checkout/contribution/email not-ready in `api.py:109-129`, `api.py:311-330` |
| More product build before validation | `BLOCKED` | `STRONG INFERENCE` binding constraint is validation, not feature count |
| Controlled concierge validation | `PROCEED` | `STRONG INFERENCE` product surface plus external market signals justify a paid test |

## 23. Final Decision

Controlled concierge validation: `PROCEED`

Open self-serve paid launch: `BLOCKED`

More product build before validation: `BLOCKED`

NailIt idea invalidated: `NO`

Final recommendation:

`PROCEED` with one focused paid concierge validation sprint for candidates with real upcoming interviews. Do not claim market demand, source sufficiency, willingness to pay, Lua outcome improvement, or self-serve readiness until the sprint produces evidence.

Evidence used:

- `REPO FACT` Phase 1 repo anchors: `api.py:87-91`, `api.py:109-129`, `api.py:159-178`, `api.py:182-187`, `api.py:259-276`, `api.py:311-330`, `api.py:344-375`, `api.py:615-662`, `api.py:690-875`, `agent_v2.py:517-654`, `agent_v2.py:6311-6494`, `lua_brief_builder.py:5-64`, `lua_coach.py:86-238`, `job_store.py:438-492`, `job_store.py:520-615`.
- `TESTED` Phase 1 readiness tests: `tests/test_validation_readiness_static.py:83-245`, `tests/test_dynamic_readiness_contracts.py:90-211`.
- `EXTERNAL FACT` Phase 2 sources: Interviewing.io, Final Round AI, Huru, Big Interview, Yoodli, Pramp, Exponent, InterviewBuddy, The Muse, MentorCruise, EEOC, NIST, The Guardian, arXiv papers, and Business Insider.

What was not checked:

- `NO EVIDENCE` No new web research was run for this integrated report.
- `NO EVIDENCE` No contaminated external source was used.
- `NO EVIDENCE` No production code was changed.
- `NO EVIDENCE` No live customer validation, payment collection, source audit, or outcome follow-up was run.

What would change the conclusion:

- `PRICING SIGNAL` Real NailIt users pay before delivery at a repeatable price.
- `MARKET SIGNAL` Users choose NailIt over generic LLM, peer practice, or human coaching alternatives.
- `TRUST RISK` Users accept the privacy/source posture and trust the pack.
- `NO EVIDENCE` Lua practice produces observed answer revision, repeat practice, and post-interview usefulness.

Next lowest cost action:

`PROCEED` Write the controlled concierge validation sprint protocol: candidate eligibility, payment ask, source audit rubric, sample pack review, Lua practice observation sheet, non-buyer script, and outcome follow-up.

Final status:

`PROCEED` for controlled concierge validation.

`BLOCKED` for self-serve paid launch, further build, demand claims, source sufficiency claims, and Lua outcome claims.
