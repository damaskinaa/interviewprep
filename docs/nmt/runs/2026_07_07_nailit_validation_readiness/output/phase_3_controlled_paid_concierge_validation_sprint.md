# Phase 3 Controlled Paid Concierge Validation Sprint

Run: `2026_07_07_nailit_validation_readiness`
Product identity: NailIt is an AI interview preparation product, not a wrong-category consumer service.
Phase: Phase 3 controlled paid concierge validation
Production code changes: none
Market research: none in this phase
Commit: none

## 1. Phase 3 Objective

`PROCEED` Run a small, paid, fast validation sprint to test whether real scheduled-interview candidates will pay for and trust NailIt's company-specific prep pack plus Lua-style mock interview loop.

`REPO FACT` Phase 1 found Layer 1 interview-pack generation implemented in `api.py:259-264`, `api.py:344-375`, and `agent_v2.py:6311-6494`.

`REPO FACT` Phase 1 found Layer 2 Lua mock-interview behavior implemented in `agent_v2.py:6397-6406`, `lua_brief_builder.py:5-64`, `api.py:653-875`, and `lua_coach.py:86-238`.

`EXTERNAL FACT` Phase 2 found paid interview-prep substitutes and AI interview-prep alternatives, but did not prove demand for NailIt's exact loop.

`BLOCKED` Do not treat Phase 3 as launch. GO means go to validation, not build.

## 2. Exact Validation Question

`HYPOTHESIS` With a real interview scheduled in the next 7-14 days, will candidates pay before delivery for a source-audited, company-specific NailIt prep pack plus one Lua-style practice session because it feels more useful and trustworthy than generic ChatGPT/Claude/Gemini, human coaching, peer mocks, or ordinary search?

Primary test question:

`PAYMENT EVIDENCE` Will highly screened candidates with real upcoming interviews make a real paid commitment before delivery, such as a small non-refundable deposit or full test payment?

`CLARIFICATION` Payment is the anti-fake-interest gate, not the whole validation result. This sprint does not test whether NailIt is generally validated as a self-serve interview app. It tests one narrow founder-led concierge wedge: company-specific prep pack plus one mock practice session for candidates with urgent real interviews.

Secondary test questions:

1. `FIELD DATA` Do users rate the company-specific pack as meaningfully better than generic AI prep?
2. `FIELD DATA` Do users identify a clear first Aha moment?
3. `FIELD DATA` Do users trust the source audit and privacy posture enough to upload materials?
4. `FIELD DATA` Do users revise answers after Lua-style feedback?
5. `FIELD DATA` Do non-buyers reject because of price, trust, timing, source quality, or alternative preference?

## 3. Segment Eligibility Criteria

Include candidates only if all apply:

1. `FIELD DATA` Real interview scheduled within 7-14 days.
2. `FIELD DATA` Named target company and named role.
3. `FIELD DATA` Has a job description or recruiter-provided role description.
4. `FIELD DATA` Will provide CV or structured background summary.
5. `FIELD DATA` Will provide current prep materials or answer examples if available.
6. `FIELD DATA` Will allow a manual source audit and one observed practice session.
7. `PAYMENT EVIDENCE` Will make a payment or deposit before delivery if they choose to participate.
8. `TRUST RISK` Accepts a plain privacy/source-use explanation before sharing data.

Preferred candidates:

1. `HYPOTHESIS` Interview is high stakes enough that better prep matters.
2. `HYPOTHESIS` Company-specific fit, story selection, or role context feels important.
3. `HYPOTHESIS` Candidate has already tried generic prep and still feels uncertain.

## 4. Exclusion Criteria

Exclude candidates if any apply:

1. `BLOCKED` No real interview scheduled.
2. `BLOCKED` Cannot name company and role.
3. `BLOCKED` Wants hidden live interview assistance rather than preparation before the interview.
4. `BLOCKED` Refuses payment/deposit but wants full delivery.
5. `BLOCKED` Refuses basic privacy/source-use acknowledgement.
6. `BLOCKED` Wants legal, immigration, salary-negotiation, or employment advice outside interview prep.
7. `BLOCKED` Requires guaranteed job offer, guaranteed score, or guaranteed outcome.
8. `BLOCKED` Requires use of restricted or login-gated sources that cannot be verified as allowed.

## 5. Recruiting Script

Short version:

> I am testing NailIt, an AI interview-prep system for people with a real interview coming up. You give your target company, role, JD, CV/background, and context. I create a source-audited company-specific prep pack, then run one mock practice session based on that pack. This is not hidden live interview help. It is preparation before the interview. The test is paid because I need to know if the value is real enough to buy, not just interesting. Are you open to a quick screening call?

DM/email version:

> Hi [Name], I am running a small paid validation sprint for NailIt, an AI interview-prep product for candidates with real upcoming interviews.
>
> The test is for people who have a named company and role interview in the next 7-14 days. You would provide the company, role, JD, CV/background, and extra context. I would produce a company-specific prep pack with source audit notes, then run one Lua-style mock practice session where you answer, get scored, get feedback, and can retry.
>
> This is not a self-serve launch and not live interview assistance. It is a controlled test to learn whether candidates will pay for source-backed company-specific prep plus practice.
>
> Test price bands are $29, $49, or $99 depending on the test slot. If you are interested, I will ask a few screening questions first.

## 6. Screening Form

Required fields:

1. Name:
2. Email:
3. Interview date:
4. Target company:
5. Target role:
6. Interview stage or round if known:
7. Job description link or pasted JD:
8. CV or background summary available? yes/no
9. Current biggest worry:
10. Current prep method:
11. Alternatives already tried: ChatGPT/Claude/Gemini, search, peers, mentor, coach, mock interview service, no prep, other
12. Would you pay before delivery if selected? yes/no/maybe
13. Highest price you would seriously consider for this test: $29 / $49 / $99 / other
14. Any privacy concerns about uploading CV, JD, or answers?
15. Consent to follow up after the interview? yes/no

Screening tags:

1. `FIELD DATA` Eligible / not eligible.
2. `FIELD DATA` Primary anxiety.
3. `FIELD DATA` Alternatives considered.
4. `TRUST RISK` Privacy/source concern.
5. `PAYMENT EVIDENCE` Paid / refused / near-buyer.

## 7. Payment/Deposit Ask

Payment ask:

`PAYMENT EVIDENCE` "This is a paid validation test. If you want the pack and mock session, payment is due before delivery. The purpose is to test whether this is valuable enough to buy, not only whether it sounds useful."

Deposit option:

`PAYMENT EVIDENCE` If full price creates friction, ask for a non-refundable deposit of at least $10 before starting, then record the stated reason for not paying the full test price.

Rules:

1. `BLOCKED` Do not count verbal interest as payment evidence.
2. `BLOCKED` Do not count "I would pay later" as payment evidence.
3. `PAYMENT EVIDENCE` Count only actual paid deposit or full test payment.
4. `FIELD DATA` Record refusal reason immediately.

## 8. Price Test Bands

Price bands:

| Band | Use | Evidence meaning |
| --- | --- | --- |
| $29 | Low-friction AI-prep anchor | `PAYMENT EVIDENCE` Tests whether the workflow clears cheap AI alternative pressure |
| $49 | Mid validation band | `PAYMENT EVIDENCE` Tests whether source-backed specificity creates value beyond generic tools |
| $99 | Higher urgency band below human coaching anchors | `PAYMENT EVIDENCE` Tests whether high-stakes candidates value concierge support |

Assignment:

1. `HYPOTHESIS` Start with $49 for the first 4 eligible candidates.
2. `HYPOTHESIS` If $49 gets no buyers, test $29 with the next 3-4 candidates.
3. `HYPOTHESIS` If $49 gets buyers and users are highly urgent, test $99 with 2-4 candidates.

Do not infer price:

`NO EVIDENCE` These bands are test anchors from Phase 2 substitute pricing, not proven NailIt pricing.

## 9. Concierge Delivery Workflow

Step 1: Screen.

- `FIELD DATA` Confirm interview date, company, role, JD, CV/background, current prep, and alternatives.
- `PAYMENT EVIDENCE` Ask for payment/deposit before delivery.

Step 2: Intake.

- `TRUST RISK` Explain data use, retention, deletion/export, no hidden live assistance, and source limitations.
- `FIELD DATA` Collect CV/background, JD, target company, role, interview stage, answer examples, and extra context.

Step 3: Source audit.

- `FIELD DATA` Manually inspect official company sources, role/JD sources, public interview-process signals, and lower-confidence community signals.
- `TRUST RISK` Mark every source as official, directional, weak, outdated, inaccessible, or excluded.

Step 4: Pack creation.

- `REPO FACT` Use existing backend pack surface where safe and manually correct unsupported claims.
- `FIELD DATA` Deliver a concise pack with company signals, interview-round hypotheses, likely questions, candidate gap map, answer angles, and evidence notes.

Step 5: Pack review.

- `FIELD DATA` Ask the candidate to score usefulness, specificity, trust, missing pieces, and first Aha.

Step 6: Lua-style mock session.

- `REPO FACT` Use the Lua-style flow concept: ask one question, candidate answers, score 1-10, give feedback, allow retry or move on.
- `FIELD DATA` Observe whether the candidate repeats, revises, improves, resists, or distrusts feedback.

Step 7: Post-session interview.

- `FIELD DATA` Ask what they would pay again, what they would remove, what they trusted, what they did not trust, and which alternative they would otherwise use.

Step 8: Outcome follow-up.

- `FIELD DATA` Follow up after the interview to capture perceived usefulness, behavior change, outcome, and referral/reuse intent.

## 10. Source Audit Rubric

Score each source area 0-3:

| Area | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| Official company values/context | No useful source | Generic source only | Specific but thin | Specific and directly useful |
| Role/JD signal | No JD detail | Generic role detail | Clear role requirements | Rich role-specific success signals |
| Interview process signal | None | Unverified generic pattern | Directional public pattern | Official or repeated credible pattern |
| Question signal | None | Generic question bank | Directional role/company questions | Strong role/company-specific questions |
| Candidate fit mapping | Not possible | Very thin evidence | Some real evidence | Clear source-backed story mapping |
| Source freshness | Unknown/old | Mostly old | Mixed | Recent enough for use |
| Source permission/access comfort | Not acceptable | Questionable | Acceptable with caveat | Clear public/allowed source |

Required source labels:

1. `FIELD DATA` Official source.
2. `FIELD DATA` Directional public source.
3. `TRUST RISK` Weak source.
4. `TRUST RISK` Restricted/access-risk source.
5. `NO EVIDENCE` No source found.

Minimum source gate:

`BLOCKED` Do not deliver a confident company-specific claim unless source audit score supports it. If the audit is weak, label the pack section as directional or insufficient.

## 11. Company-Specific Prep Pack Usefulness Scorecard

Ask the participant to score 1-5:

1. `FIELD DATA` The pack felt specific to my target company.
2. `FIELD DATA` The pack felt specific to my target role.
3. `FIELD DATA` The source notes made me trust the content.
4. `FIELD DATA` The company signals changed how I would answer.
5. `FIELD DATA` The gap map identified something important I had missed.
6. `FIELD DATA` The answer angles felt credible for my background.
7. `FIELD DATA` The likely questions felt realistic.
8. `FIELD DATA` The pack saved me meaningful prep time.
9. `FIELD DATA` I would use this again for another interview.
10. `PAYMENT EVIDENCE` I would pay this price again.

Open questions:

1. What was the first Aha?
2. Which section would you remove?
3. Which claim did you not trust?
4. What did this do better than ChatGPT/Claude/Gemini?
5. What did this do worse than a coach, peer mock, or generic tool?
6. What would make it worth more?
7. What would make you ask for a refund?

## 12. Lua Mock Interview Observation Sheet

Before practice:

1. Candidate confidence 1-10:
2. Question selected:
3. Candidate's expected answer quality 1-10:

During practice:

1. `FIELD DATA` First answer length:
2. `FIELD DATA` Score given 1-10:
3. `FIELD DATA` Feedback accepted / challenged / ignored:
4. `FIELD DATA` Candidate chose retry / move on:
5. `FIELD DATA` Number of retries:
6. `FIELD DATA` Observable answer change:
7. `FIELD DATA` Candidate used pack evidence:
8. `FIELD DATA` Candidate used unsupported claim:
9. `TRUST RISK` Candidate distrusted score or feedback:

After practice:

1. Candidate confidence 1-10:
2. Most useful feedback:
3. Least useful feedback:
4. Did the candidate revise the answer? yes/no
5. Would the candidate use this before a real interview? yes/no/maybe
6. Would the candidate pay for this again? yes/no/maybe

Do not claim:

`NO EVIDENCE` Lua improves outcomes unless observed answer revision or post-interview follow-up supports it.

## 13. Non-Buyer Interview Script

Use when an eligible candidate refuses payment.

Questions:

1. What made you decide not to pay?
2. Was the issue price, trust, timing, privacy, company specificity, AI feedback, or something else?
3. What would you use instead: ChatGPT/Claude/Gemini, human coach, peer mock, search, interview reports, no prep, other?
4. What price, if any, would have made this worth trying?
5. Did the sample or explanation feel company-specific enough?
6. Did sharing CV/JD/interview data feel uncomfortable?
7. What would need to be true for you to pay?
8. Would you use a free version? Why?
9. Would you pay only after seeing the pack? Why?
10. Is this a problem you actually need solved before this interview?

Coding:

1. `FIELD DATA` Price objection.
2. `TRUST RISK` Privacy objection.
3. `TRUST RISK` Source trust objection.
4. `FIELD DATA` Alternative chosen.
5. `NO EVIDENCE` No urgent Job.
6. `BLOCKED` Not a buyer for this wedge.

## 14. Near-Buyer Interview Script

Use when candidate is interested but hesitates.

Questions:

1. What almost made you buy?
2. What stopped you?
3. Which part sounded most valuable: company-specific pack, answer mapping, gap analysis, Lua practice, source audit, or time saving?
4. Which part sounded least valuable?
5. What proof would make you comfortable paying?
6. Would a smaller deposit change your decision?
7. Would a sample from your target company change your decision?
8. Would privacy/data deletion terms change your decision?
9. Are you comparing this to ChatGPT/Claude/Gemini, a coach, a peer mock, or something else?
10. Should we follow up before or after your interview?

Coding:

1. `FIELD DATA` Near-purchase barrier.
2. `PAYMENT EVIDENCE` Deposit accepted or refused.
3. `TRUST RISK` Trust blocker.
4. `HYPOTHESIS` Fixable conversion issue.

## 15. Post-Interview Outcome Follow-Up Script

Send 1-3 days after the interview.

Questions:

1. Did you complete the interview?
2. Which NailIt section did you actually use?
3. Did any NailIt question or practice moment appear in the interview?
4. Did you change an answer because of the pack or Lua-style feedback?
5. Did the pack make you more confident? 1-10 before/after.
6. Did the pack make you more specific? 1-10.
7. Did any claim feel wrong or untrusted after the interview?
8. What alternative would you use next time?
9. Would you pay again?
10. Would you refer a friend with an upcoming interview?
11. What happened next: moved forward, rejected, waiting, offer, withdrew, unknown?

Evidence labels:

1. `FIELD DATA` Self-reported usefulness.
2. `FIELD DATA` Observed answer change if supported by before/after artifacts.
3. `PAYMENT EVIDENCE` Repeat-payment intent is not payment evidence until paid.
4. `NO EVIDENCE` Interview outcome is not solely attributable to NailIt.

## 16. Continuation Criteria

These criteria decide whether to continue controlled concierge validation. They do not prove product-market fit, do not authorize self-serve launch, and do not prove NailIt demand.

Minimum success:

1. `PAYMENT EVIDENCE` At least 3 of 10 eligible candidates pay a deposit or full test price before delivery.
2. `FIELD DATA` At least 6 of 8 delivered participants complete pack review.
3. `FIELD DATA` At least 5 of 8 delivered participants rate company-specific usefulness 4/5 or higher.
4. `FIELD DATA` At least 5 of 8 delivered participants identify a clear first Aha.
5. `FIELD DATA` At least 5 of 8 delivered participants complete one Lua-style practice session.
6. `FIELD DATA` At least 4 of 8 delivered participants revise an answer after feedback.
7. `TRUST RISK` Fewer than 3 of 10 eligible candidates reject due primarily to privacy/source trust.
8. `FIELD DATA` At least 6 non-buyer or near-buyer reasons are captured.

Strong success:

1. `PAYMENT EVIDENCE` At least 5 of 10 pay.
2. `PAYMENT EVIDENCE` At least 2 candidates pay or accept the $99 band.
3. `FIELD DATA` At least 3 candidates say the company-specific pack was the reason they paid.
4. `FIELD DATA` At least 3 candidates show clear before/after answer improvement.
5. `FIELD DATA` At least 2 candidates say they would use it again for another interview.

## 17. Stop / Redesign Criteria

Stop, narrow, or redesign this concierge wedge if any occur. These signals do not automatically kill NailIt; they block self-serve launch and force diagnosis of segment, offer, price, source trust, privacy, Lua feedback, or delivery cost:

1. `BLOCKED` Fewer than 3 of 10 eligible candidates pay any deposit or price.
2. `BLOCKED` Most buyers say generic ChatGPT/Claude/Gemini would be enough after seeing the output.
3. `BLOCKED` Source audit fails for most target companies or roles.
4. `BLOCKED` Users do not trust company-specific claims.
5. `BLOCKED` Users do not trust Lua-style scoring or feedback.
6. `BLOCKED` Users do not revise or retry answers after feedback.
7. `BLOCKED` Privacy/data concerns block participation for more than 30% of eligible candidates.
8. `BLOCKED` The manual delivery cost is too high to support a plausible paid product without a much higher price.

Do not kill the whole idea from one weak signal:

`STRONG INFERENCE` A weak sprint can also imply a narrower segment, different price, stronger privacy posture, or more manual source QA is required. The decision must distinguish invalidated Job from fixable execution.

## 18. Evidence Ledger Template

Use one row per candidate or non-buyer.

| Field | Entry |
| --- | --- |
| Candidate ID | |
| Date | |
| Interview date | |
| Target company | |
| Role | |
| Eligibility status | `FIELD DATA` |
| Price band offered | |
| Paid before delivery | `PAYMENT EVIDENCE` yes/no |
| Amount paid | |
| Non-buyer / buyer / near-buyer | |
| Alternative considered | `FIELD DATA` |
| Privacy objection | `TRUST RISK` |
| Source trust objection | `TRUST RISK` |
| Pack delivered | `FIELD DATA` yes/no |
| Source audit score | `FIELD DATA` |
| Pack usefulness average | `FIELD DATA` |
| First Aha | `FIELD DATA` |
| Lua session completed | `FIELD DATA` yes/no |
| Answer revised after feedback | `FIELD DATA` yes/no |
| Repeat/retry count | `FIELD DATA` |
| Would pay again | `FIELD DATA` yes/no/maybe |
| Follow-up outcome | `FIELD DATA` |
| Key quote | `FIELD DATA` |
| Decision implication | `PROCEED` / `BLOCKED` / `HYPOTHESIS` |

## 19. Day-by-Day Sprint Plan

Day 0: Setup.

- `PROCEED` Finalize screening form, privacy/source explanation, payment/deposit flow, scorecards, and evidence ledger.
- `BLOCKED` Do not build new product features.

Day 1: Recruit.

- `FIELD DATA` Contact 30-50 likely candidates through founder network, communities, referrals, and warm intros.
- `FIELD DATA` Screen for interview in 7-14 days and named company/role.

Day 2: Screen and collect payment.

- `PAYMENT EVIDENCE` Ask eligible candidates for payment/deposit before delivery.
- `FIELD DATA` Log non-buyer and near-buyer reasons immediately.

Day 3: Source audit and pack preparation.

- `FIELD DATA` Run manual source audit for paid candidates.
- `TRUST RISK` Mark weak or restricted-access sources as excluded or directional.

Day 4: Deliver first packs.

- `FIELD DATA` Deliver 2-4 packs.
- `FIELD DATA` Run pack usefulness scorecard immediately after review.

Day 5: Lua-style practice sessions.

- `FIELD DATA` Run observed practice sessions.
- `FIELD DATA` Log score, feedback trust, retry behavior, and answer revision.

Day 6: Continue delivery and interviews.

- `FIELD DATA` Complete remaining pack reviews and Lua sessions.
- `FIELD DATA` Run non-buyer and near-buyer interviews.

Day 7: Interim decision.

- `PROCEED` Continue if payment/source/trust signals meet minimum thresholds.
- `BLOCKED` Stop broadening if payment, source trust, or Lua feedback fails.

Day 8-14: Outcome follow-up.

- `FIELD DATA` Follow up after real interviews.
- `FIELD DATA` Capture usefulness, answer changes, confidence, next-stage outcome, reuse/referral intent.

Day 15: Decision review.

- `PROCEED` Decide whether to repeat the sprint, narrow the segment, adjust price, improve privacy/source posture, or stop.
- `BLOCKED` Do not move to self-serve launch unless Phase 3 evidence clears gates.

## 20. What Not to Build During Phase 3

Do not build:

1. `BLOCKED` New self-serve checkout.
2. `BLOCKED` New contribution/outcome product surface.
3. `BLOCKED` New email automation.
4. `BLOCKED` More Lua modes.
5. `BLOCKED` More pack sections.
6. `BLOCKED` More answer variants.
7. `BLOCKED` New source integrations.
8. `BLOCKED` Broad public launch surface.
9. `BLOCKED` Venture/scale narrative.
10. `BLOCKED` Hidden live interview assistance.

Allowed manual work:

1. `PROCEED` Manual source QA.
2. `PROCEED` Manual payment/deposit collection.
3. `PROCEED` Manual pack review and correction.
4. `PROCEED` Manual Lua-style session observation.
5. `PROCEED` Manual non-buyer and follow-up interviews.

## 21. Final GO / NO-GO Decision Rule

GO means continue controlled validation, not launch, not build, and not claim that NailIt is validated.

GO to next validation loop if:

1. `PAYMENT EVIDENCE` At least 3 of 10 eligible candidates pay before delivery.
2. `FIELD DATA` Buyers identify the company-specific pack as a real reason for buying.
3. `FIELD DATA` Source audit supports enough credible company/role-specific signal.
4. `FIELD DATA` Lua-style practice produces observed answer revision or repeat behavior.
5. `TRUST RISK` Privacy/source concerns are manageable, not dominant blockers.
6. `FIELD DATA` Non-buyer reasons are specific and potentially fixable.

NO-GO or pivot if:

1. `BLOCKED` Payment does not happen.
2. `BLOCKED` Users prefer generic ChatGPT/Claude/Gemini after seeing the sample.
3. `BLOCKED` Source trust fails.
4. `BLOCKED` Lua-style feedback is not trusted or used.
5. `BLOCKED` Privacy concerns prevent enough users from participating.
6. `BLOCKED` Manual delivery reveals the value is too costly to provide at plausible prices.

Final Phase 3 readiness:

`PROCEED` Phase 3 is ready to run as a controlled paid concierge validation sprint.

`BLOCKED` Phase 3 is not permission for self-serve launch, more feature build, demand claims, payment claims, or outcome claims.
