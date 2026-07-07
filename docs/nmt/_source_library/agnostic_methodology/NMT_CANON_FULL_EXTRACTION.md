# Next Move Theory — Complete Canon Knowledge Extraction
*Extracted from: GitHub repo (zamesin/Next-Move-Theory-Canon-and-Skills), full AJTBD key theses file, NMT key theses file, conversation context, and all shared materials.*
*Extraction date: 2026-06-18*
*Note on repo growth: at first share in this conversation, the repo had 10 stars / 0 forks. At time of extraction: 133 stars / 34 forks / 2 pull requests. Significant traction in days.*

---

## PART 1 — WHAT THE REPO ACTUALLY CONTAINS

### Repository structure (complete)

```
Next-Move-Theory-Canon-and-Skills/
├── AGENTS.md                           # Rules file for Codex/non-Claude agents
├── CLAUDE.md                           # Rules file for Claude Code
├── LICENSE                             # CC BY-NC-SA 4.0
├── README.md                           # Full setup guide + canon map
│
├── Next-Move-Theory-Canon/
│   ├── Advanced-Jobs-To-Be-Done/
│   │   ├── ajtbd-key-theses.md         ← 455 lines, 61.5KB — the core document
│   │   ├── b2b.md
│   │   ├── barrier-removal.md
│   │   ├── behaviour-change.md
│   │   ├── communication.md
│   │   ├── consideration-activators.md
│   │   ├── critical-chain.md
│   │   ├── customers-attention-management.md
│   │   ├── job-graph.md
│   │   ├── job-structure.md
│   │   ├── job-types-and-properties.md
│   │   ├── scientific-foundations.md
│   │   ├── segmentation.md
│   │   ├── value-creation.md
│   │   └── value-creation-mechanics.md
│   ├── ABCDX-Segmentation/
│   │   └── abcdx-segmentation-key-theses.md
│   ├── Riskiest-Assumption-Test/
│   │   └── rat-key-theses.md
│   ├── Next-Move-Theory/
│   │   ├── nmt-key-theses.md           ← 242 lines, 27KB — integrative root
│   │   ├── focus-as-company-attention-management.md
│   │   ├── local-vs-global-optimum.md
│   │   └── subtraction.md
│   ├── HowTos/
│   │   └── basic-ajtbd-interview-guide-and-principles.md
│   └── Algorithms/
│       └── the-algorithm.md
│
└── Skills/
    ├── ask-nmt/
    ├── market-research/
    ├── craft-value-proposition/
    ├── product-requirements/
    └── craft-go-to-market/
```

### What's public vs. paywalled

**Public (this repo — ~25% of methodology):**
- All canon files listed above
- The main algorithm (the-algorithm.md)
- All five Claude Code skills
- CLAUDE.md / AGENTS.md

**Paywalled (nextmovetheory.com products/courses — ~75%):**
- Product-diagnosis algorithm
- Per-question algorithms: launch & PMF, scale, save dying product, position, exit competition, grow conversion, raise AOV, improve retention, build acquisition channel
- Full 100+ value-creation mechanics catalog (canon has foundational subset only)
- Product idea and feature idea generation
- Goal-setting algorithm (finding real growth points)
- Demand creation and acquisition channels (methodology at delivery stage)
- Branding on Jobs
- Company rollout process principles and algorithms
- Customer Success and Support built on Jobs
- Full unit-economics integration

---

## PART 2 — THE FULL AJTBD KEY THESES (verbatim content)

*Source: github.com/zamesin/Next-Move-Theory-Canon-and-Skills/blob/main/Next-Move-Theory-Canon/Advanced-Jobs-To-Be-Done/ajtbd-key-theses.md — fetched live June 2026*

### Preamble

Built from scratch by Ivan Zamesin, with one goal: an algorithm for any product or business goal. Existing JTBD interpretations were deliberately not adopted — to keep the thinking unframed. The methodology came from studying one hypothesis in detail — a person wants to transition to a different state — and from how the brain and psyche actually work during that transition.

After AJTBD was created, he found it alone does not deliver a complete algorithm. Combined with Unit Economics, RAT, ABCDX segmentation, OKRs, and other methodologies, it forms Next Move Theory.

**AJTBD doesn't require forgetting what you already know.** Customer research, problem interviews, CJM, ICP, WTP, feature backlogs — none rejected. They become more useful *inside* AJTBD, grounded in the right unit of analysis and connected to business decisions instead of floating free.

**Expect rewiring to take practice.** Most people arrive with an intuitive, feature-first or persona-first model. The structural, Job-first model takes ~100 honest mistakes before it feels natural.

---

### §1 — Units of Analysis

AJTBD operates on three units. Every concept, mechanic, and decision is built on these three:

**1. A Job** — the specification of a desired transition. Names: the person's situation (State A), the transition process they are trying to perform, and the expected outcome (State B), in order to perform a higher-level Job that ultimately satisfies a need. The atomic unit.

In customer analysis, a Job is paired with the chosen Solution. The Job carries the Consideration Set in State A: the customer's existing knowledge of how to perform higher-level Jobs efficiently, their fear reductions across alternatives, and their fears of specific competitors. The Consideration Set lives inside the Job, not as a separate unit.

**2. The Job Graph of the segment** — the hierarchy of all Jobs that exist for the people in the segment around the Core Jobs the product touches. Includes higher-order, lower-order, same-level, unconscious, and Jobs people don't say out loud. The unit for creating value and designing strategic moves — which Jobs of which segments to compete for, where to climb, where to expand.

The Critical Chain of Jobs is the Job Graph projected onto a time axis. It is the operational unit for value delivery, communication, activation, retention, and churn diagnosis.

**3. The Map of Segments** — the set of distinct Job-based segments in the market around the Core Jobs we want to compete for, with their economic attractiveness attached: size, Jobs budget, frequency, reachability, ability to create value, competition. The unit for choosing where to compete.

---

### §2 — The Job is the root cause of everything

- **A Job is the specification of a desired transition.** Names: State A (current situation + context + Consideration Set + negative emotions + trigger) → transition process → expected outcome (State B, with success criteria) → higher-level Job.
- A Solution is what the customer uses to perform a Job. Dual position: a real thing (TurboTax, Uber, Claude Code) AND a label for the specific Job Graph the customer walks under it. Switching Solutions = switching Job Graphs.
- **A Job is the root cause of every human action.** Everything — every action, purchase, choice, moment of attention — flows from a Job being performed.
- A Job is a unit of human motivation. The brain forms goals to satisfy needs, and those goals — formulated as concrete expected outcomes in concrete contexts — are Jobs.
- Goal = task = Job. `I want + infinitive verb` is a Job. Each verb is a separate Job.
- **A Job is NOT a Need.** Needs (safety, status, autonomy, contact, control, self-realization) live in the unconscious — too abstract to act on. A Job is the concrete, conscious way a person tries to satisfy needs.
- **Every product decision silently encodes a Job and a segment.** The choice is not whether to embed one — it's whether you embed the right Job of the right segment deliberately.
  - Features are not value; they're the delivery format for value.
  - Communication conveys value, doesn't create it.
  - Internal company Jobs exist (OKRs are Jobs of business entities).
  - Business model and unit economics are downstream of Jobs.
- **The most expensive single error in product: choosing the wrong Job of the wrong segment.** Most common and most damaging error.
- **The highest-leverage move: choosing the right Jobs of the right segments.** Nothing else compounds as strongly.

---

### §3 — The Structure of a Job (8 elements)

**All 8 elements together are the Job:**

```
WHEN [context + trigger + negative emotions + Consideration Set]
I WANT TO [expected outcome]
  WITH THESE SUCCESS CRITERIA [concrete criteria for "well enough"]
IN ORDER TO [higher-level Job expected outcome]
  → FEEL [positive emotions]
```

**When cluster — what explains why this person wants this outcome with these criteria:**
- **I'm in context:** features of the person and situation that make them want exactly this outcome with exactly these criteria
- **I feel negative emotions:** what the person feels while the result is not yet reached (anxiety, irritation, doubt, shame)
- **Consideration Set:** information that loaded awareness that a more effective way exists
- **Trigger happened:** the event that kicks off action

**I want to cluster:**
- **Expected outcome:** `I want to + infinitive verb` — the outcome expected in this context. The main element; the Job can be shortened to this but the full Job is all 8.
- **Success criteria:** concrete, measurable (or at least concrete) criteria by which the person judges the outcome was reached well enough.

**In order to cluster:**
- **Higher-level Job(s):** what sits after "in order to" — the expected outcome of the Job one level up
- **Feel positive emotions:** what the person feels once the expected outcome is reached

**Worked example — Uber Comfort Job (San Francisco):**

Segment: young SF professionals, 28–38, tech income ~$150K+, no car, social on weekends.

- **Context:** Friday 11:30pm, just finished dinner at Foreign Cinema in the Mission; two glasses of wine; lives alone in Russian Hill ~3 miles away; no car (6 years in SF); 9am Saturday yoga class already paid for
- **Negative emotions:** mild anxiety about getting home safely after drinking; slight frustration with Friday surge pricing
- **Consideration Set (4 slots):**
  1. Awareness of available Job Graphs: Uber tariffs (X, Comfort, Black, Pet, Green), Lyft, Muni late-night, walking, driving
  2. Comparative knowledge: Comfort = recent-model car + top-rated driver + "no chat" preference honored; UberX = cheaper but variable; Black = overkill for 3 miles; Lyft = fewer cars at this hour
  3. Named products with entry paths: Uber Comfort = open app → tap "Comfort" → set "no chat"
  4. Fears and what reduces them: Comfort rating filter (4.85+), in-app GPS/ETA/price upfront, past trips proving clean cars; fears of alternatives (UberX gamble, Black overpriced, late-night Muni = walk 3 blocks in heels, walking = unsafe after wine, driving = DUI risk + no car)
- **Trigger:** the check arrives, the group starts splitting up on the sidewalk, she opens the Uber app

- **Expected outcome:** get from Foreign Cinema (Mission) to her apartment door in Russian Hill
- **Success criteria:**
  - Safely — door-to-door, not "a block away"
  - Without driving herself — no navigation responsibility, decompress in back seat
  - Driver arrives within 5 minutes (visible ETA)
  - Driver follows in-app route — no detours
  - Total cost under $25 even with Friday surge
  - Driver doesn't try to chat — she's tired
  - Cabin is clean (no food smell, no sticky seats — she's wearing a dress)
  - Recent-model car, adjustable climate

- **Higher-level Job:** get to bed by 12:30am rested for yoga at 9am, having made the responsible adult choice
- **Positive emotions:** relief (home safe), satisfaction (smart adult choice), quiet pride (responsible, no DUI risk)
- **Job Frequency:** ~3×/month
- **Job Budget:** $20–25 per trip (~$800/year on this Job); pays ~30% more than UberX for the Comfort criteria
- **Job Importance:** 8/10

*The success criteria separate Uber Comfort from UberX. Same surface verb, same A and B — different criteria, different Job, different segment, different tariff.*

**Interview questions mapped to Job structure:**

| Job element | Question |
|---|---|
| Expected outcome | What outcome did you expect from using {solution}? |
| Success criteria | By what criteria did you judge you got {expected outcome} well enough? |
| Context | In what situation were you when you decided to use {solution} to get {expected outcome}? |
| Trigger | At what moment did you start doing something to get {expected outcome}? What was the trigger? |
| Higher-level Job | Why did you want {expected outcome}? In order to do what? |
| Positive emotions | How did you want to feel after you got {expected outcome}? |
| Negative emotions | Until you got {expected outcome}, did you experience any negative emotions? |

---

### §4 — Three Fidelity Levels for Jobs

**Level 1 — Full.** All 8 elements + Job Frequency + Job Budget + Job Importance. For: research notes, value prop design, Job Graph mapping, RAT cards.

**Level 2 — Intermediate.** One prose sentence:
`When {context} + {trigger}, I want to {expected outcome} with {main success criteria}, in order to {expected outcome of the higher-level Job}.`

**Level 3 — Minimal.** `I want to {expected outcome} with {main success criteria}.` For: landing-page headlines, ad copy, segment labels.

**Level 1 is the source of truth; Levels 2 and 3 are derived artifacts.** When Levels 2 or 3 drift from Level 1, the artifact has lost its anchor.

---

### §5 — Success Criteria

**Answer: by what concrete criteria does the person judge the expected outcome was reached *well enough*?**

- Concrete, never abstract. "Fast" = wish. "Within 15 minutes" = criterion.
- **Same expected outcome + different criteria = different Core Jobs** and different segments.
- Criteria are the specification of value. Without criteria, value is a wish; with criteria, it's a buildable specification.
- Aha Moment placement needs the criteria — the Aha fires when Job is performed better than the criteria the customer came in expecting.

---

### §6 — Value: The Brain as an Investor

*Grounded in Lisa Feldman Barrett's allostasis framework — brain as metabolic energy-budget manager.*

- **Value = energy efficiency for the brain in performing a Job — outcome (per success criteria) over cost (time, money, effort, cognitive load, negative emotion, Tax Jobs).** The brain commits attention only when predicted outcome justifies predicted cost.
- **The Aha Moment** is the pleasant surprise that signals value. When reality beats criteria-encoded prediction — Job done cheaper/faster/better/simpler than expected — the brain fires a Positive Prediction Error. The Aha is *not* value itself; it's the signal that value was delivered above expectation.
- **A Problem** is the unpleasant surprise. When a Job is performed below the customer's expected success criteria, the brain fires a Negative Prediction Error. A Problem is the structural condition underneath — a Solution hired for a Job, performed below the customer's expected success criteria.
- **Behaviour change is always relative to expectations; value itself is not.** Yesterday's wow is today's baseline. The brain's predictive model adapts constantly. Value itself (absolute energy-efficiency of Solution × Job pairing) stays; the customer's behaviour-change response shifts as the bar climbs.
- **A feature is not value.** A feature is the truck that delivers value — the format in which energy-efficiency arrives. Customers need a change of state (the prediction error), not a feature.

---

### §7 — A Problem is a Consequence, Not a Root Cause

**A problem is always the consequence of a Solution hired for a Job and screwed up against that Job's success criteria.** Without the Job and Solution underneath, there is no such thing as a "problem."

*"I've been trying to hire a Product Manager for six months"* — take that as the Job and you end up in PM sourcing. The Job underneath is usually *"save a failing product,"* and the unhirable PM is one consequence of that Job being delegated to a failing recruiting process.

The structural framing (§7) tells you where to intervene; the neurobiological framing (§6) tells you what the customer is experiencing.

---

### §8 — The Job Graph: Where Strategic Moves Live

**Strategic moves operate on two surfaces: the Job Graph and the Map of Segments.** On the Graph: where to climb, which Small Jobs to capture, which Job to kill, where to add a link to a new Big Job. On the Map: which segments to compete for, which to expand into, which to exit.

Most foundational AJTBD concepts live at the Graph level, not on the static Job:
- Value = Job Graph performed more energy-efficiently
- A Problem = Solution hired for a Job, performing below success criteria
- A Solution = label for a Job Graph (the specific sub-graph the customer walks)
- Behavior change = customer swapping one Job Graph for another
- Consideration Activators = 5 pieces of information that, loaded into the Consideration Set in State A, activate choice in our favor

**AJTBD operates at two complementary levels: the Job + Solution pair, and the Job Graph.** Skip the Graph and Jobs become disconnected requirements floating in the air.

---

### §9 — The Job Graph (structure detail)

**Four levels, defined relative to our product's reach (not absolute positions):**

- **Core Jobs:** the highest-level Jobs the product performs fully — and cannot climb above with its current shape. Operational criterion: a Job is Core if most Micro Jobs underneath are performed inside the product, by the team, or by owned automation.
- **Big Jobs:** Jobs one level above Core Jobs, which the product contributes to but does not fully perform. Big Jobs carry the customer's motivation; Core Jobs are what the product does. One set of Core Jobs typically serves several Big Jobs simultaneously.
- **Small Jobs:** Jobs at the same level as Core Jobs, in service of the same Big Jobs, but which the product does not perform. Performer-agnostic. Our Small Jobs are another product's Core Jobs. **Primary source of growth opportunities** — perform more Jobs in one Solution; capture the Previous Job or Next Job in the chain.
- **Micro Jobs:** Jobs one level below Core and Small Jobs. Fine grain where customer experience lives.

**Levels above Core Job carry motivation; levels below carry mechanism** — Jobs performed only as a necessary evil.

It's a graph, not a tree. One lower-level Job can connect to many higher-level Jobs (many-to-many). The more higher-level Jobs a single lower-level Job contributes to, the higher the customer's motivation to perform it.

---

### §10 — The Critical Chain of Jobs (operational delivery)

**The Critical Chain of Jobs = the Job Graph projected onto a time axis at a chosen Solution.** Only lowest-level Jobs at the chosen zoom appear as nodes; higher-level Jobs collapse into what the chain *delivers* by running every lowest-level Job in order.

The chain holds: the sequence the customer walks, hand-offs between roles or systems, cycles, time-gaps, slowest links, and the operational dynamics: predictions and prediction errors at each step, interruptions, drop-offs, Solution switches, per-step emotions, knows-how vs first-time entry.

**Where strategy operates on the Graph, operational delivery operates on the chain** — value delivery, communication, activation, retention, churn diagnosis, trigger timing. The Aha Moment fires here, on the chain.

**What a team actually ships is the Critical Chain of Jobs, not the Job.** The Job names the destination; the chain is the lived path — onboarding flow, pricing tier, in-product moments where the Aha must fire, post-purchase touchpoints that prevent churn.

---

### §11 — Critical Chain Scaling Discipline

In a new sub-segment, the chain often breaks — different regulator, different role on buy-side, different language of success criteria. The break is a knowledge problem, not a quality problem.

**Discovering, attributing, and unblocking chain-breaks across sub-segments is the first priority when scaling.** Even when the broken Job sits outside the product's scope, owning the fix is often the largest single source of unlocked value.

---

### §12 — Segmentation by Jobs (not demographics)

- **A segment = a group of people with similar Job Graphs.** Segmentation is by similarity of the set of Jobs (the full Job Graph), not any single Job. First criterion: almost always Job-Graph similarity — rarely demographics in isolation. Demographics are correlates, not causes.
- **One person is in one segment, not many.** Their whole graph places them in a segment. Alexander taking a taxi to work and a taxi to the airport is one representative of one segment with both Jobs in its graph.
- **Same expected outcome + different success criteria = different Jobs, and different segments.** Uber tariffs wear the same surface verb (*"I want to get from A to B"*) but split into distinct Jobs by criteria, and into distinct segments to the extent different people hire different tiers.
  - UberX: cheapest acceptable safe ride, "good enough" car
  - Uber Comfort: recent-model car, top-rated driver, climate control, no chat
  - Uber Black: luxury vehicle, professional driver, status
- **Segmenting first by demographics is one of the most expensive segmentation errors.** The moment you draw the first cut by age/income/industry, you've amputated parts of the market and embedded a bias you'll fight for years.
- **A segment description must answer three questions:** (1) How do we create added value for them? (2) How do we earn target per-unit margin? (3) How do we create demand and scale within this segment? If the description doesn't include Jobs and causal criteria from which these three can be answered — fake segmentation.
- **One of the riskiest assumptions in any new product: the right segment-and-Job hypothesis.** Upstream of every other assumption.

---

### §13 — Strategy = Choosing Jobs and Segments

**Every strategic product decision reduces to one type: which Jobs of which people will we compete for, why these and not others, and why will we win?**

---

### §14 — The Cause-and-Effect Chain to Profit

```
Market with money
  → Segment + Job   (one analytical entity, not two steps)
  → Added Value
  → ┌─ Business Model and Unit Economics — positive per-unit math
    ├─ Ability to create demand and acquire customers — at target CAC and lead quality
    └─ Ability to scale, including scaling customer service — without quality decay
  → Conversions + retention + repeat purchases at target levels (UE keeps closing at scale)
  → Target Profit
```

- **Market with money** = sum customer segments currently spend to perform their Core Jobs. Defined in Job terms — not "the EdTech market" but "the sum spent by people who want to learn a skill in order to switch careers." No paying Jobs = no market.
- **Segment + Job** = one analytical entity, not two steps. Defined by Job Graph.
- **Added Value** = performing Jobs above customer's expectations against success criteria.
- **Three parallel conditions** — each must hold; failure of any stops the chain.
- **An error at any step propagates downstream.** Low conversion almost never means a funnel problem — almost always a problem upstream: wrong segment+Job, value not beating alternatives, or one of the three parallel conditions failing.
- **Largest leverage:** upstream choice. Most economically valuable Job × segment whose budget supports target margin × segment large enough to scale × segment reachable through known channels at target CAC.

---

### §15 — Almost Everything You Need is Already in the Customer's Head

**Every input the methodology needs is already present in the customer's head** — Jobs, contexts, triggers, success criteria, emotions, higher-level Jobs, value already perceived, fears, Consideration Activators, decision principles.

The part NOT in the customer's head: the invention — new technologies and mechanics that perform the Job more effectively than anything the customer has seen.

- You both extract AND invent. Extract the Jobs, criteria, segments, fears, Consideration Activators. Invent the value and the delivery.
- **The single most important recruitment discipline: study only people who PAID in the past.** People are unreliable forecasters of their future behavior. Past payment (or significant past investment of time/attention/energy on the same Big Job) is the cheapest, most reliable filter against fake Jobs.
- **The dominant cause of new-product failure: building for non-existent Jobs of non-existent people.**

---

### §16 — AJTBD Interviews Are the Best Way to Internalize the Methodology

Reading installs vocabulary; **interviews make the mental rewire happen.** The Job stops being an idea and becomes a structure the practitioner can extract, inspect, compare, and use.

---

### §17 — People Can Do Without Products

A product is a means, not an end. **The customer doesn't need your product — they need a Job performed.**

**You compete with every other way the customer could perform their Big Jobs** — not just products in your category — including doing it themselves, doing nothing, or a non-obvious substitute. Zoom killed business-trip airfare for whole classes of meetings; a good mattress competes against another cup of coffee tomorrow morning.

The moment you treat your product as the end rather than as one of many means to the customer's end, you stop seeing the real competitive set — and the largest value-creation opportunities.

---

### §18 — Consideration Activators

The customer arrives carrying a Consideration Set in State A — their existing knowledge of the most efficient way to perform higher-level Jobs, fear reductions across alternatives, fears of specific competitors.

**Consideration Activators = the five pieces of information that activate the customer's choice in our favor when loaded into their Consideration Set.**

**The five Consideration Activators:**

1. **A new Job Graph exists** — with *this* graph, *these* Small Jobs and Core Jobs (ours), to *these* success criteria.
2. **The new Job Graph performs the Big Job more efficiently** than the customer's current way. Concrete, criteria-anchored delta. Abstract "better" doesn't activate.
3. **A concrete named product performs that Job Graph, and here is the door** — a name (brand, service, vendor) and a first concrete step (download, sign up, book a call).
4. **Specific fears about the new Job Graph are reduced.** A fear = the customer's prediction that the Big Job won't be performed well through the new graph. Name the specific feared break, show why it's prevented/absorbed/reversible/irrelevant. If the break is real, communication cannot reduce it — change reality first.
5. **Alternative Job Graphs are fired** — concrete Problems and Risks from sticking with the competing Solution. Abstract "they're worse" doesn't fire anything; the customer's brain won't down-weight an option without a concrete reason.

**Value Creation creates the reason to switch Job Graphs; Barrier Removal creates the possibility to switch. Loading Consideration Activators writes the five Activators into the Consideration Set.**

**Prerequisites (in this order):**
a. Detailed knowledge of the target segment
b. Detailed knowledge of the Core Jobs, including concrete success criteria
c. Detailed knowledge of the Job Graph (Big Jobs, Small Jobs, Micro Jobs, Critical Chains, cycles, hidden Jobs)
d. Actually performing Core Jobs significantly more energy-efficiently than alternatives — and being able to prove it. Build, ship, watch real customers, validate which value is actually delivered, THEN extract concrete Consideration Activators. Activators built before validation is validated are hypotheses, not facts.

**Loading Consideration Activators is what makes it possible to sell radically unfamiliar, innovative products.** Without them, an innovative product fails not because the value isn't there but because the customer's Consideration Set never gets the new Big-Job-and-Graph pairing written into it.

---

### §19 — Barrier Removal

**Where Value Creation gives the customer a reason to switch Job Graphs, Barrier Removal gives them the possibility to switch.**

A Barrier = an objective condition preventing the customer from performing the new Job Graph — a missing prerequisite, an unsupported context (state, ZIP, plan, compliance regime), a broken chain link, a failing hand-off, a cycle that sends the customer back for rework, or an irreversible-loss exposure.

Examples: TurboTax without K-1 support blocks LLC owners; DoorDash outside a ZIP code blocks delivery; B2B SaaS without SAML blocks IT security review.

Barriers are segment-specific. Stripe's API worked for engineering-staffed startups; local merchants needed no-code checkout. Zoom worked for corporate meetings; K-12 schools needed FERPA, waiting rooms, locked rooms.

**Reality first, communication second.** Barrier Removal makes the claim true; Consideration Activators make the truth usable in the customer's head.

---

### §20 — Habit and Fears

- **Habit is a physical change in the brain** under a specific way of performing a specific Job. Three rules: don't try to instill new habits (painful and expensive); reuse existing habits (embed into them); roll out changes very gradually.
- **Fears eat value.** You can deliver enormous value, but if the customer fears the new solution will fail their Job, the value never lands.

---

### §21 — The Four Forces of Progress (ARCHIVED)

The Four Forces (added value pulling forward, current-Solution problems pulling forward, fears holding back, habit holding back) were a useful intermediate tool inherited from earlier JTBD work. **AJTBD has moved past them** — there are more than four forces, and a Problem with the current Solution is usually the trigger that launches evaluation rather than a force in steady state.

**AJTBD's current anchor for behavior-change practice:** create Value (§6), remove real Barriers (§19), load Consideration Activators (§18), reduce specific Fears (§20), embed in existing Habits (§20).

---

### §22 — Value-Creation Mechanics (overview)

**There are 100+ mechanics in the Next Move Theory methodology, and every one rests on one or more of six foundations:**

1. **Creating value** — performing the Jobs of a target segment more energy-efficiently against their success criteria. The substrate everything else stands on.
2. **Managing the customer's attention** — directing finite customer attention to the moments where value lands, and away from where it doesn't.
3. **Choosing which Jobs of which segments to compete for, and which NOT to.** Segment discovery, Job-Graph mapping, success-criteria research, ABCDX analysis, focus and subtraction at the segment level.
4. **Loading Consideration Activators** — writing the case for our Job Graph into the Consideration Set so they move our way.
5. **Activating the customer into value once they enter the funnel** — landing the first Aha Moment, repairing chain-breaks before they fire, designing the activation path so attention doesn't drop before value lands.
6. **Communicating value already delivered** — translating proven value into the customer's language of Jobs and criteria so it can scale.

**Mechanics by business task:**
- Grow product value
- Grow conversions
- Reduce churn / improve retention
- Go-to-Market
- Exit direct competition
- Foundational value-creation mechanics
- Acquire customers
- Scale the product (expand the market we compete for)
- Grow return rate / repeat purchases
- Foundational product-management mechanics
- Grow average order value
- Foundational strategies
- Create an acquisition channel
- First priority of value creation
- What NOT to do

The same mechanic often attaches to several tasks.

**Most foundational mechanics for orientation:**
- Move up to a higher-level Job — turn a Big Job into your new Core Job and kill many lower-level Jobs as a class. Often the most powerful mechanic when applicable (§23).
- Kill a Job — a class of Jobs disappears (Uber killed *"search for change"*)
- Take a Job off the customer — do it for them
- Fix breaks in the Critical Chain of Jobs — highest-leverage when present (§11)
- Lower costs without removing Jobs (price, cognitive cost, time, emotional cost)
- Eliminate a negative emotion — sell peace of mind, not the absence of problems

---

### §23 — The Most Powerful Mechanic: Move Up the Job Graph

**Of every value-creation mechanic, one dominates whenever it applies: move up one level in the Job Graph.** Turn a Big Job above your current Core Jobs into your new Core Jobs, and kill many lower-level Jobs as a class.

**Examples:**
- **Uber:** climbed above owning a car by becoming the Core Job for *"get from A to B around the city, on demand."* Buying, financing, insuring, parking, refueling, servicing, registering, reselling — none performed by the rider anymore. Same Big Job, Job Graph a fraction of the size.
- **TurboTax:** climbed above filing taxes by hand by becoming Core Job for *"file my federal and state return correctly."* Reading instructions, picking forms, computing deductions, double-checking arithmetic, mailing the envelope — collapsed into a guided Q&A.
- **ChatGPT:** climbed above Word by performing the entire *"produce a finished document"* Big Job. The Jobs Word required collapsed for the segment that adopted ChatGPT.
- **Claude Code:** climbed above writing code by hand by becoming Core Job for *"ship a working change in this codebase."* Reading surrounding code, writing character by character, looking up APIs, debugging, writing tests, running the linter, managing commits — all collapsed into *"describe the change in English; the model writes it, runs tests, iterates on failures."*

**This is the methodology-level explanation for the AI-product wave.** Every fast-growing neural-net product runs the same mechanic at unprecedented scale, climbing above some Big Job in knowledge work and removing the entire class of lower-level Jobs underneath.

**The North Star this mechanic points at: the invisible product.**
> The ideal product performs the Job entirely — and does not exist as a product the customer interacts with.

You leave home in the morning, come back in the evening, the house is clean — and there is no "cleaning product" you used. Zoom didn't beat the airlines by being a better airline; it removed the trip. The robot vacuum is closer to the ideal than a better mop.

Every other mechanic in the catalog is a partial step toward this ideal.

---

### §24 — Communication Through Jobs

**All communication is communication in the language of Jobs.** Landing pages, ad creatives, sales scripts, emails — the underlying sentence is always: *we perform these Jobs of this segment more effectively, by these success criteria, through these features.* If the comm doesn't translate cleanly back into that sentence, it's not on-strategy.

**Value-proposition formula:** `[For which segment] + [Which Job — Big or Core] + [How much more effectively, in concrete success criteria] + [Through which features].` Features come last.

**Promise must match delivery.** Communicating at the Big-Job level while the product only performs Core Jobs underneath inflates the customer's prediction, manufactures a Negative Prediction Error, and produces disappointment — no matter how well the Core Jobs were performed.

**Creatives are formulaic Job-language recombinations, not invention.** Plug Core Jobs, Big Jobs, triggers, Problems, criteria, and State-B images into formulas and test which the segment responds to.

---

### §25 — B2B Specifics

- **A B2B sale = a graph of Jobs performed by several roles along a Critical Chain of Jobs that must not break at any link.** Roles: champion, decision-maker, budget holder, IT/security/legal influencers, end users, sometimes saboteurs. Drop one role's Jobs and the deal stalls there while every other role is satisfied.
- Every role has at least two kinds of Jobs — business Jobs and personal Jobs.
- **B2B motivation is usually dominated by personal Jobs, not business Jobs.** The business Jobs are the *frame* in which the deal happens; the personal Jobs are *why* the human actually moves. Counter-intuitive for teams trained on B2C.
- **Knowing and performing the business and personal Jobs of every role dramatically increases close probability.** Most teams know one business Job of the decision-maker and stop there.

**Five typical personal Jobs of a decision-maker:**
1. *"I want to make a vendor choice that won't get me blamed or fired."*
2. *"I want to use the same tools the best people in my field use."*
3. *"I want to build a career-defining story from this implementation."*
4. *"I want to offload operational routine."*
5. *"I want to pick a vendor who will still support me at year 3."*

**If the product, sales script, and comm focus only on the business Job, adding a layer that performs the decision-maker's personal Jobs is one of the highest-ROI moves available in B2B.** The same buyers, same product baseline — just a deliberate layer:
- Product explicitly makes the DM look good (auto-generated executive summaries, dashboards they can present, "look how much we saved" reports)
- Communication speaks to the personal Job
- Sales brings ammunition for the DM to defend the decision internally

This single layer compounds across the funnel — uplift in deal close rate, average contract value, and retention.

---

## PART 3 — NMT KEY THESES (verbatim content)

*Source: github.com/zamesin/Next-Move-Theory-Canon-and-Skills/blob/main/Next-Move-Theory-Canon/Next-Move-Theory/nmt-key-theses.md — fetched live June 2026*

### Overview

**Next Move Theory = the integrative meta-framework joining five core methodologies into one system.**

Four pillars: AJTBD, Unit Economics, Riskiest Assumption Test, ABCDX Segmentation.
Fifth core methodology: Theory of Constraints.
Supporting goal-setting methodology: OKR.

**The leading principle: the product is a single organism.** Marketing can't be changed in isolation from the product and the segment. Every function performs Jobs for the same target segment, in the same shared language.

**Status:** in active development. Main algorithm (v1.0) exists, ~80 strategies catalogued in Mechanics Catalog. Open frontiers: cross-function goal-setting alignment and universal decision-tree tool.

---

### §1 — The Unit of Analysis: The Company Strategy

**A Company Strategy = a sequence of actions of the company's functions that leads the company toward an expected outcome.** Functions: Discovery, Delivery, Marketing, Sales, Support, R&D, Finance. The sequence covers everything: research, expert interviews, quantitative validation, internal alignment, segment-and-Job anchor choice, OKR translation, hiring, quarterly execution.

**Multiple Company Strategies are always available at any moment.** These are alternative sequences of cross-function actions.

**NMT's job: make those alternatives visible, comparable, and choosable, so the company can pick the most economically valuable one.**

**The Chosen Company Strategy is anchored on AJTBD: the choice of Jobs of segments.** It answers: *"which Jobs of which people will we compete for, why these and not others, and why will we win?"* Without that anchor, a Company Strategy is just an action list.

---

### §2 — The Six Methodologies

**Four core pillars:**
- **AJTBD** — the unit of customer analysis (Job, Job Graph of segment, Map of Segments). Gives the language and customer-side unit. Other pillars close the gap between "we found valuable Jobs" and "we extract target profit."
- **Unit Economics** — the financial filter. If per-unit math doesn't add up, the product doesn't exist, regardless of how good the Jobs are.
- **RAT (Riskiest Assumption Test)** — the integrative function. Pulls every component of the product into one validation system. Removes riskiest assumptions cheaply and in the right order before building.
- **ABCDX Segmentation** — allocating company resources to profitable, satisfied customers (A/B) and firing unprofitable, unsatisfied ones (C/D/X).

**Core methodology — constraint management:**
- **Theory of Constraints (Goldratt)** — throughput is governed by the slowest link; bottleneck moves as the system changes; Critical Chain is where breaks and cycles cluster. AJTBD's Critical Chain of Jobs is borrowed and adapted from Goldratt's *Critical Chain.*

**Supporting methodology:**
- **OKR** — translates the Chosen Company Strategy into measurable cross-function commitments. Company goals (OKR) are Jobs of business entities. OKR provides the protocol that propagates the Chosen Company Strategy into each function's goals without drift.

---

### §3 — Why NMT Exists: The Alignment Problem

**The author could not find any step-by-step methodology for forming Company Strategies that both rests on value creation for the customer AND solves the cross-functional alignment problem inside a company.**

In a typical product company, every function speaks a different language:
- Researchers run studies the product team shelves
- Product ships features Marketing doesn't know how to sell
- Marketing brings in leads that don't fit what the product serves well
- Sales closes deals on customers who churn or never see value
- Support is overloaded with C/D customers consuming 80% of energy for 0% of profit
- Three different segmentations live in the same company: Product by Jobs, Marketing by demographics, Sales by industry
- Three strategies — product, brand, marketing — written separately and rarely reconciling

**NMT's job: align every function around one Chosen Company Strategy and one target segment, in one shared language: the language of Jobs.**

---

### §4 — The Cause-and-Effect Chain to Profit

```
Market with money
  → Segment + Job   (one analytical entity)
  → Added Value
  → ┌─ Business Model and Unit Economics — positive per-unit math (LTV > CAC, payback <12mo, target margin)
    ├─ Ability to create demand and acquire customers — at target CAC and lead quality, in volume
    └─ Ability to scale, including scaling customer service — without quality decay
  → Conversions + retention + repeat (UE keeps closing at scale)
  → Profit
```

**Three parallel conditions** — tested simultaneously (RAT treats them as co-equal, not sequential):
- Business Model and UE: LTV > CAC, payback under 12 months, target margin per unit
- Demand creation and acquisition: channels delivering leads at target CAC and quality in volume
- Scale: operations, support, R&D, and hiring keeping pace without quality decay

---

### §5 — Two Consequences of the Chain + Diagnostic Discipline

**Consequence 1: When a downstream metric breaks, investigate the upstream chain first.**
- Low conversion = most often Job, segment, value, or communication problem upstream wearing a funnel mask
- High CAC = most often segment-and-Job mismatch, rarely a channel-tactic problem
- High churn = most often a value problem (customer now sees the gap clearly) or segment problem (wrong people acquired), rarely a retention-mechanic problem

**Consequence 2: Largest single leverage = choosing the most economically valuable Job in a segment with the budget to sustain UE.**

Four dimensions of the choice:
1. The Job's value gap against current Solutions — how much room to create Added Value?
2. The segment's budget for the Job — enough to close UE?
3. The segment's size and reachability — enough volume to scale into?
4. The segment's accessibility through known channels — reachable at target CAC?

---

### §6 — Subtraction: The Meta-Operator Across All Four Pillars

**Underneath all four pillars, one operation runs: subtraction.** Removing something from the system that, at first glance, looked like it had to stay.

| Pillar | What gets subtracted |
|---|---|
| AJTBD | Jobs from the target segment's Job Graph; non-target segments from the strategic landscape |
| Unit Economics | Negative-margin units, channels, transactions, SKUs |
| RAT | Risky assumptions before they get built into the product |
| ABCDX | C/D customers from the paying base; their support load |

**Subtraction asymmetrically beats addition for four structural reasons:**

1. **The brain rewards "less spent."** Every product interaction = investment of attention, time, energy. Subtraction hands back what the customer was already spending, immediately, before any learning curve. AirPods didn't "add wireless audio" — they killed *untangling headphones.* ChatGPT didn't "add AI writing" — it killed *find a template, format headings, draft from blank.*
2. **Risk compounds multiplicatively.** Seven 60%-confidence assumptions = 3% joint survival probability. Removing one assumption multiplies the chance by 1.67×. Adding one at 80% confidence multiplies by 0.8×. Cheapest way to raise a product's chance of working = remove a risky assumption.
3. **Focus doesn't sum.** Every addition steals from every prior commitment. Subtraction runs in reverse: removing a segment, Job, feature, or channel hands time and attention back to everything that remains.
4. **Loss aversion runs at ~2×.** The customer's brain registers removal of friction, anxiety, or chain-break at roughly twice the strength of an equivalent feature addition. Square's tip screen removed *the awkwardness of choosing while the barista watches.* TurboTax removed *the anxiety of "am I doing this wrong."*

**Diagnostic question across pillars:** *"In each pillar, what has this team explicitly subtracted in the last quarter, and why?"* A team that answers in all four is running the meta-operation. A team silent in one or more has a pillar-specific gap.

---

### §7 — Value is the Substrate on Which Everything Stands

**Value = energy efficiency for the brain in performing a Job — outcome over cost.** Outcome measured against success criteria. Cost covers time, money, effort, cognitive load, negative emotion, and Tax Jobs.

Two consequences:
- **Behaviour change is always relative to expectations; value itself is not.** Yesterday's wow is today's baseline. Value creation is continuous work, not a one-time delivery.
- **A feature is not value.** Customers need a change of state (prediction error), not a feature.

Value lives across the canon in different operational forms: full theory in Value Creation; allostasis substrate in Scientific Foundations; communication as conveyance in Communication; criteria differences in Segmentation; chain-walk where value delivers in Critical Chain; Consideration Activators in Consideration Activators; subtraction as asymmetric value-creator in Subtraction; validation before scaling in RAT; customers worth keeping in ABCDX.

---

### §8 — Focus is a Core Operation of NMT

**Focus, attention management, and subtraction are one operation in three names.**
- Focus = the chosen target (target segment, Core Jobs, criteria)
- Attention management = continuous routing of constrained team-and-customer attention at that target
- Subtraction = the mechanism: `direct(X) = subtract(claims-on-non-X)`

**Five nested scopes of the same operation:**
- (a) Directing the customer's attention through the chain-walk
- (b) Company-level focus on segments and Core Jobs
- (c) Department-level focus per function
- (d) Product-portfolio focus across products and acquisitions
- (e) Individual employee focus across the day

---

### §9 — Local vs. Global Optimum

- **Local optimum:** improving current product, segment, or business model. Low risk, low ceiling. Add a Job at a lower level, fix problems, raise conversion, lower CAC. Delegated to junior roles.
- **Global optimum:** changing segment, business model, market, or Core Job. High risk, multiplier-scale upside. Segment switches, moves up the Job Graph to a Big Job, B2C → B2B switches, business-model changes.
- **The Innovator's Dilemma:** failure to fund the global-optimum track because the local one still works.

**Hold focus on the local optimum AND fund a second, parallel investment track aimed at the global-optimum move.** Both tracks run at the same time. A team that holds the focus track but funds no second track drifts into the Innovator's Dilemma in 3–5 years. A team that funds the second track but doesn't enforce the focus track never wins the target segment.

**Examples:**
- Amazon: held retail focus while running a second investment track on AWS from ~2002
- Netflix: held DVD-by-mail focus while running a second track on streaming 2000–2007
- Stripe: refused enterprise sales while funding Atlas and Treasury exploration as a separate track
- Notion: refused Enterprise IT requirements until individual-knowledge-worker segment was saturated, while reserving a discovery track for enterprise expansion

---

### §10 — NMT as Alignment in Practice

Every function works on the same target segment, with the same Jobs, same success criteria, same language:

- **Discovery:** research to learn the real Job Graph and real success criteria of the target segment
- **Delivery:** builds value over those Jobs and criteria, using value-creation mechanics, ranked by RICE, with riskiest assumptions tested first via RAT
- **Marketing:** acquires people in motion toward those Jobs, using proxy signals derived from AJTBD interviews: subscriptions, communities, life events, search queries, role titles
- **Sales:** closes by hitting the same Jobs and criteria. In B2B, hits both Business Job and Personal Job of the decision-maker
- **Support:** sized for A/B customers. C/D/X filtered upstream by lead qualification, not absorbed downstream by an over-staffed support team
- **R&D:** invests in capabilities that perform the target segment's Core Jobs at higher prediction errors over time
- **Finance:** validates that the chosen segment, Job, and budget mix supports target margin, LTV > CAC stays positive at customer-flow scale, and per-unit math closes before the company invests in scaling

**The shared language — Jobs, success criteria, segments — is what makes alignment cheap.** Without it, alignment requires standing meetings. With it, alignment is automatic.

---

### §11 — NMT as a Diagnostic (12-point validation)

1. Is there an economic Map of Segments? Size, budget, frequency, reachability of each?
2. Have you picked one target segment using the four-factor screen (added value, target margin, scale, reachable demand)?
3. Do you know the Job Graph — Core, Big, Small, Micro Jobs?
4. Do you know the success criteria for the Core Job and the Big Job?
5. Have you surfaced the Aha Moment and moved it as far left in the chain as possible?
6. Do you have a value proposition in the formula `[segment] + [Job] + [how much more effectively] + [features]`?
7. Do you have proof of value (people pay; people use; people return)?
8. Do all three parallel conditions hold? (a) UE closes at segment level, not on average. (b) Acquisition channels modeled, tested, scaling. (c) Service/operations/R&D scalable without quality decay.
9. Are Discovery, Delivery, Marketing, Sales, Support, R&D, and Finance aligned around the same target segment?
10. Does conversion + retention keep UE closing as customer flow scales?

Failing any one breaks the chain. Investigate upstream gaps first.

---

### §12 — NMT as Investment-Analysis Lens

Doubles as an investment-thesis check:
- Is there a Chosen Company Strategy? Deliberate, chosen from visible alternatives, not picked by default.
- Is it unified? Product/marketing/sales = one Chosen Company Strategy in different operational forms.
- Are functions aligned around it?
- Is there focus? Resources concentrated on one or a few target segments?
- Is the cause-and-effect chain intact end-to-end?

A company answering "yes" to all compounds. A company that can't burns capital at the broken node and calls it "execution."

---

## PART 4 — ADDITIONAL FILES SUMMARIZED (from repo structure + README descriptions)

### Scientific Foundations (scientific-foundations.md)
The brain as an energy-budget investor. Why needs fail as a unit and Jobs succeed. Rests on Lisa Feldman Barrett's work on allostasis, prediction, and reward prediction error. Key sections: §1 allostasis, §2 AJTBD's key hypothesis of value, §3 neural common currency, §4 the same machinery firing during purchase decisions, §11 Red Queen mechanic.

### Job Structure (job-structure.md)
The eight elements that fully specify a single Job, element by element, with interview questions. Fifteen sections of detail. Levels 1–3 fidelity explained in full.

### Job Graph (job-graph.md)
The hierarchy of Jobs around the product; the four levels defined relative to the product's reach. §4 on how the graph is built (maker chooses which graph the Solution offers; customer accepts or rejects). §19 on Small Jobs as primary growth opportunities (capturing Previous Job or Next Job in the chain).

### Job Types and Properties (job-types-and-properties.md)
The taxonomy of Jobs as a diagnostic instrument:
- **Regular Jobs:** performed deliberately and consciously
- **Orientation Jobs:** performed when the customer doesn't know which Job to perform — "figure out what I actually want"
- **Tax Jobs:** performed only because they're a necessary prerequisite (filling out a form, reading instructions, verifying identity)
- **Fake Jobs:** what the customer says they want, but not what actually drives behaviour
- **Emotional Jobs:** the emotional state change the customer is really hiring for
- **Viral Jobs:** Jobs that produce new customers as a side effect of performing them

### Critical Chain of Jobs (critical-chain.md)
Chain pathologies, predictions during the walk, interruptions and their four outcomes, drop-off as Solution switch, the knows-how vs first-time path through orientation, triggers that re-launch the chain, per-step emotions.

### Value Creation (value-creation.md)
The deep canon on value: energy efficiency, success criteria as the specification of value, the Aha Moment. Full theory + 20 base mechanics. Includes the Red Queen mechanic (§6): yesterday's wow is today's baseline; value creation is continuous work.

### Value-Creation Mechanics Catalog (value-creation-mechanics.md)
The foundational catalog of value-creation mechanics:
- Kill a Job — a class of Jobs disappears
- Take a Job off the customer — do it for them
- Climb a level — turn a Big Job into your new Core Job
- Fix breaks in the Critical Chain
- Lower costs without removing Jobs
- Eliminate a negative emotion
*(Full 100+ catalog is paywalled; this file contains the foundational subset.)*

### Behaviour Change (behaviour-change.md)
Why switching is swapping one Job Graph for another. A Solution as a label for the sub-graph it installs. §2: switching Solutions = switching Job Graphs. §6: Aha Moment as Positive Prediction Error.

### Customers' Attention Management (customers-attention-management.md)
Attention as the metabolic resource every value-creation mechanism routes through. Attention is finite and the brain allocates it predictively. Every product interaction competes for it.

### Consideration Activators (consideration-activators.md)
Full treatment of the five Consideration Activators, the loading operation, how they relate to Barrier Removal, and how they make selling radically innovative products possible.

### Barrier Removal (barrier-removal.md)
Six classes of Barriers and the operator set of Barrier-Removal mechanics.

### Communication (communication.md)
Communication in the language of Jobs — the value-proposition formula and the landing-page structure. The 9 Job-language blocks mapped to the five Consideration Activators. Full creative-formula catalog and conversion mechanics.

### Segmentation (segmentation.md)
Segmentation by Job Graph similarity, not demographics. The most expensive cut to get wrong. Full segmentation methodology including causal segmentation criteria.

### ABCDX Segmentation (abcdx-segmentation-key-theses.md)
Splitting the paying base by margin × satisfaction:
- **A:** high margin, high satisfaction — double down
- **B:** high margin, lower satisfaction — invest to satisfy
- **C:** low margin, high satisfaction — deprioritize or fire
- **D:** low margin, low satisfaction — fire
- **X:** not yet customers, but excited about the product — signal of where to grow next (highest willingness-to-pay in the market; become A-grade customers if the specific friction stopping them is removed)

ABCDX needs a paying base — not applicable for new products with no customers. Minimum signal: 3-month data on a base large enough to produce a pattern.

### Riskiest Assumption Test (rat-key-theses.md)
Before you build: list the assumptions the idea rests on, rank them by how lethal they are if wrong, and buy the cheapest evidence against the deadliest first.

Key principle: **Every idea is already dead — you just don't know what will kill it yet.** RAT is how you find out cheaply, before you've paid for the build.

Every initiative is a stack of risky assumptions, any of which might not hold. Seven 60%-confidence assumptions = 3% joint survival probability. **The cheapest way to raise the chance of a product working = remove a risky assumption.**

### B2B (b2b.md)
The B2B deal as a Job Graph across roles. Why personal Jobs usually outweigh business Jobs. The integrator model. B2B vs B2B2C dynamics. The "ex" rule for end-user weight. Common B2B mistakes.

### AJTBD Interview Guide (basic-ajtbd-interview-guide-and-principles.md)
Practical interview guide — principles and a question bank that reconstruct Jobs, criteria, Aha Moments, and Barriers from what a customer actually did. Focuses on past behavior (not hypotheticals). Structured around the 8 Job elements.

### Focus as Company Attention Management (focus-as-company-attention-management.md)
Focus as pointing the whole company's attention at specific Core Jobs of one segment. The Innovator's Dilemma as focus that ossified. Five scopes. Two-track investment model. §7 on how to hold focus track while funding the global-optimum track.

### Local vs. Global Optimum (local-vs-global-optimum.md)
Two parallel investment tracks. The exit from the local optimum runs through the Job Graph: moving to Previous and Next Jobs, climbing to higher-level Big Jobs, finding segments that grow on a trend.

### Subtraction (subtraction.md)
Subtraction as the meta-operator across all four pillars. Four structural reasons it asymmetrically beats addition. Skill transfer across pillars.

### The Algorithm (the-algorithm.md)
How the pieces combine into a single cyclical algorithm — and the anti-patterns that kill products. The main algorithm in ~9 steps. Covers: diagnostic, choosing segment+Job, designing value, validating riskiest assumptions, aligning functions, scaling. Anti-patterns: feature factory, persona-first segmentation, skipping RAT, optimizing downstream metrics before fixing upstream causes.

---

## PART 5 — THE FIVE SKILLS: WHAT THEY ACTUALLY DO

### /ask-nmt
Conversational advisor. Not a producer — does not output artifacts. For: explaining concepts, diagnosing real situations, pressure-testing hypotheses like a skeptical senior PM, routing to the right producer skill. Reads the canon at runtime (not generic JTBD training data). The breakout hit in early user testing.

### /market-research
**Question answered:** *"Which Jobs of which segment should we compete for first?"*
**Output:** GO / NARROW / PIVOT one-pager, segments scored on a five-factor screen, direct and indirect competitors, action-first RAT plan, alternative Big-Job markets to pivot into.
**Modes:** Quick (no internet, ~3–5 min) and Deep (subagents + web research, 15–30+ min).
**Structure:** 3 waves of parallel subagents.
- Wave 1: Market & Sizing (1A) + Competitors & Reviews (1B) + Asset Extraction (P1)
- Wave 2: Segments Synthesis & Self-Critic
- Wave 3: Strategy & Differentiation + Pivot Evaluation

**Key design decisions:**
- Reads canon at runtime → stays grounded in AJTBD, not Christensen JTBD
- Requires `.claude/settings.json` with WebSearch/WebFetch for subagents in Deep mode
- Outputs to `Skills-Results/{slug}/market-research/` (can be changed via TEAM.md convention)
- Skills produce hypotheses, not conclusions — every number has a verification path attached

**Observed behavior from real runs:**
- Run 1 (training data only): useful directionally but all numbers are estimates
- Run 2 (live web): meaningfully better — live competitor intel, sourced market data
- Session limit (Pro plan ~5hr rolling) can interrupt multi-wave runs — type `continue` or `finish` to force synthesis from partial data
- GO verdict is often misread as build approval — skill should be read as "GO to validation"

### /craft-value-proposition
Takes chosen segment + Jobs and builds the strongest Value Proposition.
Value hypotheses mapped over the Job Graph and the value-creation mechanics, filtered on feasibility, unit-economics, and competitiveness, ranked, with the top RAT cards.
Output includes a PRD-ready implementation spec.

### /product-requirements
Turns chosen segment + value into a build-ready PRD (full functionality + edge cases).
First runs a **"challenge the build"** gate that hunts for a cheaper way to hit the same business goal before specifying the build. This is the RAT discipline embedded in the skill itself.

### /craft-go-to-market
Turns the value proposition into ready-to-publish go-to-market:
- Landing-page copy
- Ad / creative formulas
- Acquisition + growth-communication plan (channels loaded with Consideration Activators, lead magnets, viral loops, retention messaging)

---

## PART 6 — THE CLAUDE.MD / AGENTS.MD PATTERN

**CLAUDE.md** teaches Claude Code the correct AJTBD definitions + routing table to canon files.
**AGENTS.md** does the same for Codex, Cursor, and other agents.

**Why this matters:** Out of the box, an agent pattern-matches to generic JTBD (often Christensen's version) and gets the theses wrong. Without these files, even sophisticated multi-agent workflows drift back to Christensen JTBD despite explicit prompting. With these files, agents stay grounded in AJTBD definitions.

**Verified in practice:** Dimity (12-subagent market research workflow) confirmed that NMT skills with the canon loaded prevented JTBD drift that had persisted in his custom agents despite explicit prompting.

**Advanced pattern (Constantine K.):**
```
TEAM.md              ← single source of truth, agent-agnostic
CLAUDE.md            ← thin wrapper: "read TEAM.md + here's Claude runtime specifics"
AGENTS.md            ← thin wrapper: "read TEAM.md + here's Codex runtime specifics"

Canonical skill file (one file)
  ├── .claude/skills/{skill}  → symlink → same file (Claude reads here)
  └── .agents/skills/{skill}  → symlink → same file (Codex reads here)
```

---

## PART 7 — WHAT THE METHODOLOGY EXPLICITLY REJECTS

These are things the AJTBD/NMT methodology explicitly identifies as wrong or insufficient:

1. **Persona-first or demographics-first segmentation** — correlates, not causes; amputates market; embeds bias
2. **Feature-first product thinking** — features are trucks that deliver value, not value itself
3. **The "find the pain, build the painkiller" model** — insufficient because satisfied customers with no problem still buy
4. **Christensen's JTBD** — kept the deepest intuition (situation → desired state transition) but left the existing machinery behind because it never told how to research, segment, choose where to compete, or create value
5. **The Four Forces of Progress (archived)** — there are more than four forces; a Problem with current Solution is usually the trigger for evaluation, not a force in steady state
6. **Treating the customer-reported "problem" as the root cause** — it's almost always a consequence; reconstruct Job + Solution + Problem before working on any named problem
7. **Building before validating the riskiest assumptions** — RAT discipline; the idea is already dead; find out cheaply before you've paid for the build
8. **Optimizing downstream metrics without diagnosing upstream** — low conversion is almost never a funnel problem; investigate Segment + Job → Value → three parallel conditions before touching the funnel
9. **The Innovator's Dilemma** — failure to fund the global-optimum track because the local optimum still works; a company that does only local optimum drifts into disruption in 3–5 years
10. **Cross-function misalignment** — three strategies (product, brand, marketing) written separately; three segmentations (Jobs, demographics, industry) in the same company

---

## PART 8 — SCIENTIFIC FOUNDATIONS SUMMARY

*(The full file — scientific-foundations.md — was not fetched; this summary is from what's referenced throughout the canon files)*

The methodology rests on:
- **Lisa Feldman Barrett's work:** allostasis, prediction, and reward prediction error — what value actually *is* to a brain managing an energy budget
- **Allostasis:** the brain's primary job is to predict and manage the body's metabolic resources; perception, emotion, and action are all consequences of that predictive energy management
- **Neural common currency:** the same metabolic machinery fires during purchase decisions as during physical effort decisions
- **Reward prediction error:** the delta between delivered value and the customer's prior prediction is what drives behaviour change — not value itself
- **Theories of:** needs, emotions, habit, identity, and loss aversion — explain how a person changes behavior

**Key hypothesis of value (AJTBD's):** Value = energy efficiency for the brain in performing a Job — outcome (per success criteria) over cost (time, money, effort, cognitive load, negative emotion, Tax Jobs).

This scientific grounding is what separated AJTBD from prior JTBD work. Prior JTBD could describe Jobs but couldn't yield an algorithm for creating value because it lacked a precise definition of what value *is* at the neurobiological level.

---

## PART 9 — GAPS IN THE PUBLIC CANON (what's known to be missing)

Based on the README's explicit statement of what's paywalled + community feedback:

**Missing algorithms:**
- Product-diagnosis algorithm (for live products with stalling metrics)
- Per-question algorithms: launch & PMF, scale, save dying product, position, exit competition, grow conversion, raise AOV, improve retention, build acquisition channel

**Missing mechanics:**
- Full 100+ value-creation mechanics catalog (foundational subset only is public)

**Missing methodology areas:**
- Product and feature idea generation
- Goal-setting algorithm (finding company's real growth points)
- Demand creation and acquisition channels at delivery stage
- Branding on Jobs
- Company rollout process principles and algorithms
- Customer Success and Support built on Jobs
- Full unit-economics integration

**Structural gap identified by community:**
- No `/diagnose` skill entry point for live products (PM whose conversion dropped from 4% to 3% has no good starting point in the current skill set)
- No skill onboarding flow — skills assume you already understand the methodology

**Practical gaps from real usage:**
- Skills can accept user inputs as facts rather than hypotheses — validation debt counter pattern proposed as fix
- "GO" verdict misread as "build now" — should be "GO (to validation)"
- Output paths hardcoded to Skills-Results/{slug}/ — breaks team repo conventions
- Context budget ~40k tokens per skill run — expensive for harness environments invoking skills repeatedly

---

## PART 10 — THE MAIN ALGORITHM (VERBATIM, fetched live from nextmovetheory.com June 2026)

*This is the complete text of the-algorithm.md — the central document of the entire methodology.*

### 1. Context: Next Move Theory, the meta-framework

Next Move Theory is the integrative meta-framework. It combines Advanced Jobs To Be Done, Unit Economics, Riskiest Assumption Test, ABCDX segmentation, and Theory of Constraints. OKR is a supporting methodology.

The unit of analysis is the Chosen Company Strategy: a sequence of cross-function actions toward an expected outcome, across Discovery, Delivery, Marketing, Sales, Support, R&D, and Finance. It is anchored on the choice of Jobs of segments: which Jobs of which people will we compete for, why these, and why will we win?

**The goal is to align every function around one Chosen Company Strategy, in one shared language: the language of Jobs.** The product is a single organism — you can't change marketing in isolation from the product and the segment.

Subtraction is the meta-operator running through every step. The highest-leverage move is usually to remove, not to add — a Job from the customer's graph, a non-target segment, a risky assumption, or a feature.

The algorithm is a loop, not a one-shot run. Every action produces new data for the next pass.

### 2. The cause-and-effect chain to profit — the diagnostic spine

The chain is sequential up to value, then branches into three conditions that must hold simultaneously, then converges into conversion, retention, and profit. Every step inherits the quality of the step above it. The diagnostic runs top-down: investigate the upstream node first.

```
Market with money
  → Segment + Job          (one analytical entity, not two steps)
  → Added Value
  → ┌─ Business model & Unit Economics — positive per-unit math
    ├─ Ability to create demand & acquire customers — at target CAC and lead quality
    └─ Ability to scale, incl. customer service — without quality decay
  → Unit Economics keeps closing at scale — conversion + retention + repeat
  → Target Profit
```

- Market with money is defined in Job terms. Not "the EdTech market" but "the sum people spend to learn a skill in order to switch careers."
- Segment + Job is one entity. A segment is defined by its Job Graph: similar Core Jobs with similar success criteria. The Big Job above is motivational context, not the segmentation cut.
- The three conditions after value are tested in parallel, not in sequence — which is why RAT (Step 8) treats its baseline risks as simultaneous tests.
- **A broken metric almost never means a problem at that metric.** Low conversion, high CAC, and high churn are usually upstream: wrong Segment+Job, value that doesn't beat alternatives, or one of the three parallel conditions failing.

### 3. Architecture — ten steps, three phases, one loop

```
┌─►  I.  FRAME & HYPOTHESIZE — in your head / expert / LLM (fast, cheap)
│       1  Challenge the business goal — 5 Whys + "is this even the right goal?"
│       2  Diagnose the current state — segments, Job Graphs, decisions, owners, data
│       3  Assemble the layer — Map of Segments · Job Graph · Consideration Sets
│       4  Shortlist candidate mechanics — where the solutions could in theory live
│
│       II. RESEARCH & GENERATE — in the field (real time and money)
│       5  Field research, scoped by the shortlisted mechanics
│       6  Apply the surviving mechanics to the REAL Job Graph
│       7  Rank by RICE — unit-economics gate · opportunity cost
│
│       III. DE-RISK & SHIP — the biggest spend, only after value is proven
│       8  RAT — kill the riskiest assumptions cheaply (or pivot)
│       9  Validate value — sales first, then UX 4/4
└────── 10 Ship the top bet  →  new market data  →  back to 1
```

**Gate logic:**
- **Challenge the goal before anything else.** The goal you were handed is very often the wrong one. Analyzing how to hit a mis-set goal is the most expensive early waste.
- Every step is a gate. If it doesn't hold up, pivot (= swap the set of risky assumptions). Don't move forward.
- If at step N you find an assumption from step N−K was false, go back and rebuild from the point of error. Don't fake progress on a broken upstream node.
- Cost rises by phase. Phase I: fast/cheap (head, expert, LLM — an hour). Phase II: real research time and money. The big build spend comes only in Phase III, after the riskiest assumptions are killed and value is proven.

### 4. The ten steps (full detail)

**Step 1. Challenge the business goal**
Start here, because the goal you were handed is very often the wrong one. "Lift this metric" or "ship this feature" is frequently not the goal worth pursuing. Run 5 Whys up the goal — climb 3–5 levels, from feature to conversion to sales to margin to profit to the strategic goal. At each level, look for a more effective way to hit the higher goal.

Local vs. global optimum is an explicit gate. Local = improving current product/segment/model: low risk, low ceiling, delegable, additive. Global = changing segment, business model, market, or Core Job: high risk, multiplicative upside, subtractive. Only the founder or C-level has authority to override the team's addition bias. The two are parallel investment tracks, funded together.

Artifact: a Focus Goal at the right level, an explicit local-vs-global choice, and the alternatives you cut, with reasons.

**Step 2. Diagnose the current state**
Don't jump to solutions before you understand the situation — the strategist's main mistake (Rumelt). Pull together: Map of Segments + Job Graphs of target segments; decisions already taken and outcomes; ownership and constraints (responsible person? resources? conflicting goals? stakeholders?); existing research, customer feedback, analytics, cohorts, unit economics.

Define the context: new product vs. existing, and PMF stage (none / weak / strong / ripped-out-of-customers'-hands). For an existing product: run ABCDX on the paying base; find the 20% of customers giving 80% of margin; run switch interviews with churned users; ask "why do they stay?" before "why do they leave?"

Artifact: structured picture of current state + explicit context (PMF stage, new vs. existing).

**Step 3. Assemble the layer — data first, then hypothesis**
Don't just hypothesize. Start from structured data you already have (analytics, prior research, customer reviews) and hypothesize only the gaps. An LLM drafts the hypothesis parts fast — it's still a hypothesis to test in the field; aim for enough material to scope the research, not for accuracy.

- 3.1. Map of Segments — from existing data and reviews first; hypothesize gaps. Root: similar Core Jobs with similar success criteria. Big Job above is motivational context, not the cut; demographics are a secondary correlate.
- 3.2. Job Graph for the target segment — same rule. Big Job → Core Jobs → Small/Micro Jobs + the Critical Chain of Jobs.
- 3.3. Consideration Set per Core Job — list 3–5 current Solutions, including DIY and "do nothing" (both are Job Graphs), and how our Graph differs.

**Step 4. Shortlist candidate mechanics**
Walk the value-creation mechanics catalog and flag mechanics that could in theory solve this business goal on the layer. Keep the handful you most strongly believe in — that's your expert call.

Artifact: shortlist of mechanics, each with the unknowns you must learn in the field to judge whether it applies.

**Step 5. Field research, scoped by the mechanics**
**The shortlisted mechanics are the spec on the research — they tell you exactly what to learn and where to look.** "Move to the Previous Job" becomes "walk me step by step through everything you did from the moment the Big Job appeared up to buying your current Solution." "Kill a Job" becomes "what in the current process do you hate or always put off?" "Lower fears and barriers" becomes "when did you last almost buy but didn't, and what stopped you?" Without the mechanics in hand, you interview blind.

Tools: AJTBD interviews, switch interviews with churned/migrated users, expert interviews, product analytics, quantitative survey to size segments. **Recruit only past-payers** — the cheapest filter against Fake Jobs.

Research exists to get raw material for the mechanics you'll apply: real Job Graphs, success criteria, Critical Chains and their breaks, barriers, habits, fears, Consideration Activators, Aha Moments.

**Step 6. Apply the surviving mechanics to the real Job Graph**
**The real value usually sits outside the current Core Jobs** — in Previous and Next Jobs, Big Jobs, adjacent segments' Small Jobs, emotional and Orientation Jobs, and Critical Chain repairs.

Each hypothesis is `segment × Job × mechanic → concrete action`. Examples:
- *Kill a Job* × onboarding chain → "auto-import the customer's existing data so they never re-enter it — the setup Job disappears"
- *Move to the Previous Job* × lead-gen segment → "build the free estimator they use before they're ready to buy — capture them earlier than competitors"
- *Take the Job off the customer* × done-for-me segment → "run the whole workflow as a service; the customer only approves"
- *Create a link to a new Big Job* × status-first segment → "tie the Core Job to 'signal who I am,' raising willingness-to-pay without changing the product"
- *Repair a Critical Chain break* × new sub-segment → "the chain breaks at compliance review for enterprise; own that Job and the segment unlocks"

**A hypothesis only counts if it makes the Big Job land better by the segment's own success criteria.** A Core-Job criterion that doesn't ladder up to a Big-Job criterion the customer cares about won't carry the switch.

**Step 7. Rank by RICE**
- R — Reach: share of target segment the hypothesis creates value for
- I — Impact: expert estimate of value added, defined per business goal
- C — Confidence: the evidence hierarchy — opinion → analytics → survey → interview → MVP → sales. Higher level = higher Confidence
- E — Effort

Apply the unit-economics gate: can the hypothesis in principle deliver target margin per paying customer on the target segment? If not, bin it, however beautiful. Write down opportunity cost.

Artifact: ranked list + top few to test next.

**Step 8. RAT — Riskiest Assumption Test**
Write positively-stated risky assumptions under each top hypothesis — a cause-and-effect chain rooted in Segments and Jobs, each item falsifiable by a single experiment. Positive form: "the segment pays at our price," not "customers might not pay."

The five baseline risks (a real RAT has many more; the killing one usually hides in product-specific custom risks):
1. **Market** — exists, large enough, growing, free of blocking regulation
2. **Segments and Jobs** — segments performing similar Core Jobs exist, are large enough and reachable, and the chosen Core Jobs are the most attractive. **This is the root — more product cycles die here than anywhere else**, because a wrong choice cascades down the whole chain
3. **Value** — customers from those segments buy our product to perform those Core Jobs
4. **Unit economics** — average margin per paying customer hits target
5. **Acquisition channels** — repeatable channels exist that fit the unit-econ budget and scale

Add product-specific custom risks — usually where products actually die. Talk to a competitor's salesperson. Walk the operating model actor by actor.

Priority formula: `(P(risk hits) × cost if it hits) / cost of validation`. Validate whatever sits at the top.

**The goal of a new initiative is to kill it or pivot it, not to launch it.** The work is buying knowledge cheaply. A run that kills the initiative before the build is a successful RAT.

The MVP is a probe, not a product. Its success criterion is "did the risk reveal itself," not "did it sell."

**Survival is multiplicative.** Seven risks at 40% each ≈ 3% joint survival. The highest-leverage move is the drop-it exercise: remove a risky assumption so it no longer needs to be true.

A pivot = a change in the set of risky assumptions. Change the highest-priority un-validated one first; keep what's validated. The segment-Job pivot is usually the highest-leverage.

Gate: a key assumption falsified means stop and pivot.

**Step 9. Validate value — sales, then UX 4/4**
**The best validation of value is sales.** Communicate at the Big-Job level (where motivation lives) but promise only what the chain actually delivers — over-promising manufactures a Problem.

Run solution interviews in iterations of 6. If ~5 iterations produce no sales, there's a fundamental error in segment, Job, or value — pivot rather than run "one more round." The segment is the highest-leverage pivot.

Once sales start, run UX tests on the 4-of-4 rule (RITE): four of four users must complete the Core Job without critical errors. If even one fails, fix it, run another four, repeat until 4/4. Four questions at every step: what do you see, what are you thinking, what are you feeling, what do you want to do.

Place the first Aha Moment as far left in the Critical Chain as possible — every step before it is an abandonment window.

**Only after 4/4 sales and 4/4 UX should you invest in full-scale development.**

**Step 10. Execute + loop**
Ship the top hypothesis, get market data, return to Step 1. Re-challenge the goal, update the diagnosis, rebuild or continue.

A pivot swaps the set of risky assumptions, not just one. Change the most leveraged thing — most often the segment — not everything at once.

**Value is simplification of the Job Graph over time.** Keep the Graph as a time series: which Jobs died, which appeared, where the market is moving.

Hold focus on the current segment AND fund a second track for the global-optimum move. A team that funds no second track drifts into the Innovator's Dilemma in 3–5 years.

### 5. Contextual branches

**By PMF stage:**
- PMF = 0 → main business goal is Go-to-Market: first find the paying segments, then prove the value. Don't scale a product that doesn't exist yet.
- PMF weak → grow value, position and differentiate, bring margin to target.
- PMF strong → wide field: scale, launch new products, retention, AOV, scale in current segments, fund new high-risk initiatives.

**By product type:**
- New product → full cycle from Step 1. Main risk: picking a rare/low-frequency Job for a small audience, or a Fake Job (future-tense fantasy no one paid for).
- Existing product → fundamental risks already reduced; focus shifts to efficiency and scaling. Start with ABCDX + switch interviews. Constraints: customer expectations/habits, internal politics, PM's limited zone. Big changes must be argued: bigger segment, materially more value, or suboptimal model. The "if it ain't broke" trap = Innovator's Dilemma, escaped through the Job Graph.

### 6. The broken vs. the right value-creation process

**Broken:** came up with a feature → ran interviews to check whether it has value → decided to build or not. Fails for three reasons: (1) cognitive bias — you seek confirmation; (2) you start from the feature, not the Job — blind to the rest of the Graph; (3) of 100+ mechanics you guessed one — you don't see the whole graph or the other ways to create value.

**Right:** challenge the goal (5 Whys) → diagnose the state → assemble the layer → shortlist mechanics → research → build the real graph → apply mechanics → rank → RAT → validate by sales and UX 4/4 → execute → loop. The planning unit is the value hypothesis, not the feature.

### 7. Fractality of strategies

The same mechanic works at every level. *Move to the Next Job* is a button in the UI or a company strategy (design → design + renovation). **Level of application = scale: at the Big Job it's strategy, at the Micro Job it's micro-optimization.** Once you understand the mechanics, you apply them everywhere — from copywriting to picking a market.

---

## PART 11 — REPO UPDATES DISCOVERED (June 2026, post-first-share)

The repo has evolved since it was first shared in this conversation:

1. **Official one-line installer now exists:**
```bash
curl -fsSL https://nextmovetheory.com/install.sh | bash
```
Run from project root — drops the canon AND the skills into `.claude/skills` (Claude Code) and `.codex/skills` (Codex) automatically. This replaces the manual clone+symlink flow for new projects. A Windows PowerShell installer also exists.

2. **Version status made explicit:**
- Advanced JTBD: **v3.4 — stable.** The proven foundation.
- Next Move Theory: **v0.6 — in active development.** Integration of AJTBD + RAT + ABCDX + ToC + Unit Economics into one operational system, "forming in the open — track it to 1.0" with a public changelog.

3. **Scale claim updated:** "Hundreds of companies run on Next Move Theory" with dozens of documented cases where metrics moved significantly.

4. **Repo traction:** from 10 stars/0 forks at first share → 133 stars/34 forks within days.

---

## PART 12 — HOW TO RUN THE COMPLETE METHODOLOGY IN CLAUDE CODE (definitive answer)

**Critical understanding: the complete runnable methodology is the repo itself, not this document.** This document is your reference companion — the map. The repo is the engine. You already have the engine installed.

**Your setup (already done):**
- Repo cloned at `~/Next-Move-Theory-Canon-and-Skills`
- Skills symlinked via `.claude/skills → Skills/`
- `.claude/settings.json` enables WebSearch/WebFetch for Deep mode
- Research outputs saved to `my-research/` under git

**To stay complete forever:**
```bash
cd ~/Next-Move-Theory-Canon-and-Skills && git pull
```
Every canon improvement, every skill fix Ivan ships lands in your setup automatically through the symlink.

**The Tier-4 harness pattern (from community best practice) — the layers on top of the base install:**

Layer 1 — TEAM.md (your single source of truth):
```markdown
# Product Context
[Your product's current state — update after each research run]

# Methodology Rules
- AJTBD, never Christensen JTBD
- A Job = situation → desired state transition
- Segment by Job Graph similarity, never demographics
- All inputs are hypotheses until field-validated
- GO always means GO (to validation), never GO (build)

# Validation Debt Rule
Every artifact must state: N unverified assumptions, M fatal,
cheapest test for each before building.

# Output Convention
All outputs → my-research/{date}-{skill}.md, committed same day.
```

Layer 2 — Validation gate (QA loop) — run after every producer skill:
```
Apply validation-gate: count unverified assumptions in this output,
mark the fatal ones, list the cheapest test for each, and confirm
which RAT items from the previous run have actually been tested.
Block progression to /product-requirements until at least one
fatal assumption has field evidence.
```

Layer 3 — Headless mode for repeatable runs:
```bash
claude -p "/market-research [input]" --allowedTools "Read,Edit,Bash" \
  --output-format json > my-research/$(date +%Y-%m-%d)-run.json
```

Layer 4 — Session-limit discipline (Pro plan):
- Quick mode for iteration, Deep mode for the validated final pass
- If the limit hits mid-run: type `finish` to force synthesis from partial data
- Schedule Deep runs at the start of a fresh 5-hour window

**The remaining verbatim canon files** (RAT key theses, ABCDX, segmentation, value-creation, etc.) are all in your local repo at `Next-Move-Theory-Canon/` — readable any time with `cat` or by asking Claude Code to read them. They are also all readable on nextmovetheory.com/library/canon. The skills read them automatically at runtime; you never need to paste them anywhere.
