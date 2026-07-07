# validation-gate.md
*Run this as a follow-up prompt after ANY producer skill output (`/market-research`, `/craft-value-proposition`, `/product-requirements`, `/craft-go-to-market`). This is the Tier-4 QA loop that raw skill output is missing by default.*

---

## Invocation

After a skill finishes, paste:

```
Apply the validation-gate from validation-gate.md to the output above.
```

## What the gate must produce

**1. Validation Debt count**
```
Validation Debt: N unverified assumptions, M fatal if wrong.
```
Walk the output line by line. Anything stated as fact that came from the user's input (not from a live source or field test) counts as an unverified assumption. Rank fatal = would invalidate the whole recommendation if false.

**2. RAT cross-check**
List every risky assumption from the skill's own RAT/risk section. For each, state:
- Has this been tested in the real world (sale, interview, prototype, live data)? Yes/No.
- If No — is this the cheapest thing to test next, or is something else cheaper and more informative?

**3. GO-verdict correction**
If the skill output contains the word "GO" without "(to validation)" immediately after it, correct it now. State explicitly: *"GO means go test this — not go build this."*

**4. Segment-Job sanity check**
Re-read the chosen segment and Core Job. Ask: does this survive the test *"same expected outcome + different success criteria = different Job"*? If two segments in the output share a criterion set, they are one segment misdescribed as two — flag it.

**5. Subtraction check**
State one thing that should be REMOVED from the recommended plan — a feature, a segment, a channel, an assumption — before anything is added. If the skill's output only proposes additions, this check has failed and must be run explicitly now.

**6. Cheapest next real-world test**
Given everything above, name the single cheapest test that would kill the most fatal assumptions per unit of time/money spent. This must be a real-world action (a sale, a call, an interview, a prototype in front of a real user) — never "run more research" or "analyze this further."

**7. Block/proceed decision**
State explicitly: is it safe to proceed to the next skill in the pipeline (e.g. `/craft-value-proposition` after `/market-research`), or must the cheapest test in item 6 be run first? Default to **block** unless at least one fatal assumption already has real-world evidence.

---

## Example of a properly gated output (generic, illustrative only)

```
Validation Debt: 6 unverified assumptions, 2 fatal.
Fatal #1: Willingness-to-pay at the stated price — no real customer has
  paid this. Cheapest test: sell 3 manual instances of the core offer
  this week, no build required.
Fatal #2: A required third-party partnership will actually be signed —
  no term sheet exists. Cheapest test: 3 direct outreach contacts this week.

RAT cross-check: 4 of 6 risks untested. Market-size risk is the ONE
tested item (live web sources) — do not re-test this, it's the cheapest
thing already done.

GO-verdict correction: original said "GO" — corrected to "GO (to validation)."

Segment-Job sanity check: passed — the two candidate segments have
genuinely different success criteria, so they are correctly two segments,
not one merged incorrectly.

Subtraction check FAILED — skill output only proposed additions (add
feature, add channel, add adjacent market). Recommend removing the
lowest-confidence addition from V1 scope entirely until the core Job
is validated.

Cheapest next real-world test: sell 3 instances of the core offer to
named prospects this week — kills both fatal assumptions in one action
if it works, or narrows to one if it doesn't.

BLOCK. Do not proceed to the next skill until the manual sale test
returns a result.
```
