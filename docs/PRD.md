# PRD — Sales Call Intelligence for GCC Mid-Market

**Working name:** Sahil (سهّل — "make it easy")
**Version:** 4.0
**Owner:** Himanshu
**Status:** Pre-MVP. Building the transcription and extraction pipeline against mock calls.

---

## 1. The one-line version

Post-call summaries, next steps, and objection tagging for GCC sales teams who will never buy Gong.

---

## 2. Positioning — stated honestly

This is not a technology moat. Gong, Chorus, Clari Copilot, Avoma, and Fireflies all analyze sales calls, and this product analyzes sales calls. Anyone reading this PRD will notice that immediately, so it's worth being direct about where the opening actually is.

**It isn't the technology. It's the price point, the vertical, and the scope.**

Gong is an enterprise platform: annual contracts, six-figure deals, procurement cycles, and a feature surface built for VP-of-Sales buyers at software companies. A 40-agent brokerage in Dubai is not going to buy it, cannot justify it, and would use perhaps 10% of it. That segment currently does nothing — managers spot-check a handful of calls a month and coach on instinct.

The play is a deliberately small product for that gap: three outputs, low price, no procurement cycle, live in a week. Depth comes from the vertical — an objection taxonomy and coaching rubric built specifically for Dubai real estate, which is not something a Palo Alto roadmap will ever prioritize.

**The risk this creates:** competing on price and scope in a category with well-funded incumbents is a hard commercial position, and it only works if customer acquisition stays cheap. That's a real strategic weakness, not a footnote. It's the honest cost of the simpler product.

---

## 3. Who this is for

**Beachhead ICP:** Dubai and Abu Dhabi real estate brokerages, 20–150 agents, already recording calls through their dialer or CRM.

Why this segment:
- Agent quality variance is extreme, and owners know it
- AED 1.5M+ average ticket makes a small conversion shift material
- RERA registration makes the agent population enumerable and reachable
- Lead-generation budget already exists to redirect

**Not the ICP:** enterprise software sales teams, and shops under 20 agents.

**Primary user:** the sales manager or brokerage owner. Not the agent. The manager has the pain and the budget, and decides whether the tool gets used or quietly ignored.

---

## 4. Riskiest assumptions

| # | Assumption | Why it's risky | How we test it |
|---|---|---|---|
| **A1** | Extraction of next steps and objections is accurate enough to trust | If a manager catches two wrong summaries, they stop reading all of them | Run the pipeline on 15 calls, hand-label ground truth, measure precision |
| **A2** | Managers act on the output rather than skimming it | The category's standard failure mode — insights read, nothing changes | Track whether flagged coaching moments produce a conversation with the rep |
| **A3** | Brokerages will share recordings, with consent handled properly | UAE PDPL exposure sits with them, and owners know it | 10 discovery calls; 3 written data agreements before production use |

**A1 is where to start, and it's testable without a customer.** Mock calls with a scripted ground truth give a precision number this week.

---

## 5. Scope

### MVP — four outputs, nothing else

**F1 — Transcription with speaker separation.** Audio in, timestamped transcript out, rep and customer distinguished.

*Design decision:* prefer dual-channel recordings, where the dialer captures rep and customer on separate tracks. Splitting channels gives perfect speaker separation for free and avoids diarization entirely, which is the single most failure-prone step in this pipeline. Mono audio falls back to a diarization model with a known accuracy penalty. This constrains the ICP to teams whose dialer records stereo — worth confirming during discovery.

**F2 — Call summary.** What the customer wants, budget signals, timeline, and current state of the deal. Under 150 words. A summary a manager won't read is worthless.

**F3 — Next-step extraction.** What the rep committed to and by when. The most immediately useful output and the easiest to verify — a manager can check it against the call in thirty seconds, which builds trust in everything else.

**F4 — Objection tagging.** Three categories at launch: price, timing, competitor. Three, not five, because narrow scope keeps precision high and these cover most of what appears in this vertical. *(Addendum 2026-08-08: expanded to 10 categories — see the scope-expansion note below. Re-run the precision eval before trusting the wider taxonomy at the same bar as the original three.)*

### Deliberately cut, with reasons

| Cut | Reason |
|---|---|
| Composite call score (86/100) | Single-number scoring gets gamed — reps optimize the rubric, not the customer — and it reads as surveillance. Behavior-level flags instead. |
| Deal probability prediction | Needs labeled historical outcomes; roughly 500+ closed deals per org before it beats a manager's instinct. Phase 3 at the earliest. |
| Sentiment analysis | Low precision and consistently rated the least actionable output in this category. |
| Executive dashboard | At this ICP size, the buyer and the manager are the same person. |
| Real-time in-call assist | Far higher latency and accuracy bar. Solve async first. |
| WhatsApp and chat ingestion | Out of scope in this version. Calls only. |

**Addendum (2026-08-08) — two of these cuts were explicitly reversed.** A
sales-manager analytics requirements doc (not part of the original PRD)
called for a full Gong-style rubric: a weighted composite score and
per-call sentiment, among other things. Building that gap was an explicit,
informed product decision — not scope creep discovered after the fact —
made with the reasoning above still on the table: composite scoring can get
gamed and reads as surveillance to reps, and sentiment is genuinely
lower-confidence than the other outputs. Both are now built (section 18-style
weighted score, section 11-style sentiment arc), and both ship labeled with
per-dimension evidence and a confidence figure rather than presented as
settled facts, per that same doc's own principle (section 35): "show
confidence where AI classification is uncertain." **The tension with this
PRD's own positioning is real** — "three outputs, low price, no procurement
cycle, live in a week" (section 2) describes a smaller product than what's
now built — and is noted here rather than silently rewritten. Also built in
this pass, extending rather than reversing prior scope: discovery/pitch/
closing rubric scoring, buying-intent signals, rule-based compliance/script-
adherence checks, AI coaching output, and the objection taxonomy expanded
from 3 to the doc's 10 categories.

**Correcting the v1.0 roadmap:** CRM integration sat in Phase 3 while win rate and revenue metrics sat in Phases 1–2. Those are computed from CRM outcome data. CRM moves to Phase 2 as a hard dependency.

---

## 6. Metrics

### North star

**Behavior Improvement Rate** — the share of flagged behaviors that measurably improve across a rep's next five calls.

Why not "revenue influenced," which the original draft proposed: attribution is unwinnable. Lead source, price, market timing, and the rep all touch every deal, and claiming the AI moved it invites an argument you lose in front of a CFO. Behavior improvement is leading, product-controlled, and measurable from calls alone — no CRM required. It connects to revenue through a chain stated openly rather than assumed:

> flagged behavior → behavior change → better discovery and objection handling → higher meeting-to-viewing rate → conversion

Each link gets measured separately. Revenue stays a lagging business metric.

### Supporting metrics

**Coverage** — % of a team's calls successfully ingested and transcribed above the confidence threshold. Target 85%. Below that the summaries have blind spots and managers stop trusting them.

**Extraction precision** — % of extracted next steps a manager confirms as correct, sampled weekly. Target 85%+ for next steps, since it's the output they can verify fastest and the one that sets trust for everything else.

**Manager engagement** — % of summaries opened within 24 hours. Leading churn indicator.

### Hypotheses, not claims

The original draft asserted +15% conversion, 20% cycle reduction, +10% win rate, 80% review reduction. Round numbers, no baseline, no derivation. Restated as testable:

- **H1:** Managers using the tool review more calls per week than before adoption. *Self-reported baseline at week 0 vs. product telemetry at week 8. Direction is confident; magnitude unknown until measured.*
- **H2:** Reps whose flagged behaviors improve show higher lead-to-viewing conversion than reps whose don't. *Within-org cohort comparison, 12 weeks.*
- **H3:** Extracted next steps get logged in CRM at a higher rate than manually entered ones. *Requires Phase 2 CRM integration.*

Publishing a range with nothing behind it is worse than publishing none.

---

## 7. Unit economics

Calls-only makes inference cost the dominant COGS, and it doesn't shrink with scale the way chat would have.

*Illustrative — verify current rate cards before external use.*

| Component | Assumption | Cost |
|---|---|---|
| Transcription | 30-min call, ASR at ~$0.006/min | ~$0.18 |
| LLM extraction | ~8k input / 800 output, mid-tier model | ~$0.04 |
| Storage | Amortized | ~$0.01 |
| **Per call** | | **~$0.23** |

A broker doing 40 calls a month costs about **$9 in inference**. At a $49/seat price that's roughly 80% gross margin.

**The sensitivity that matters:** a telesales team doing 150 calls a month costs $35 while the seat price stays flat, and margin collapses toward 30%. Two responses, and the second is the better product decision:

1. Seat price plus a monthly call-minutes allowance, with overage billing
2. Self-hosted `faster-whisper` on a GPU instance instead of a per-minute API. Fixed infrastructure cost, near-zero marginal cost per call. Worth switching once volume passes roughly 20,000 calls a month.

---

## 8. Architecture

```
Call recording (dialer / CRM export)
              │
              ▼
   Dual-channel split  ──or──  diarization fallback
              │
              ▼
        ASR (Whisper)
              │
              ▼
   LLM extraction — summary, next steps, objections
              │
              ▼
        Review UI + email digest
```

No vector database at MVP. The earlier draft included one, and it belongs in Phase 2, when cross-call search ("who mentioned Emaar payment plans this month") and retrieval of comparable won calls for coaching actually have data to work with. Adding it now would be stack decoration.

**Region:** UAE cloud at launch.

---

## 9. Roadmap

**Phase 0 — Prove extraction (weeks 1–2).** No customers. Build the pipeline. Record 5–8 mock sales calls with scripted ground truth, deliberately varied — one price objection, one vague buyer, one where the rep talks too much. Measure extraction precision (A1). This is the portfolio artifact whether or not the company happens.

**Phase 1 — MVP (weeks 3–10).** Batch upload, transcription, four outputs, simple review UI, daily digest. Three design partners, unpaid, with written data agreements.

**Phase 2 — Prove the loop (weeks 11–22).** CRM integration for outcome data, behavior improvement tracking, rep self-review, coaching rubric v1, cross-call search. First paid conversions.

**Phase 3 — Predict.** Call scoring and deal risk, once labeled outcomes exist. Expanded objection taxonomy. Second vertical — automotive or insurance telesales.

---

## 10. Risks

**Reps treat it as surveillance.** The top cause of failed rollouts in this category, and it doesn't show up as complaints — it shows up as calls quietly not getting recorded. Mitigation: rep-private mode for the first 30 days, where reps see their own analysis before any manager does. No leaderboards at launch. Every insight framed as a suggestion with a rationale, never a verdict.

**Extraction is wrong in a way the manager catches.** Trust is asymmetric here — two bad summaries undo twenty good ones. Mitigation: surface confidence, link every extracted claim to its transcript timestamp so it's verifiable in one click, and treat precision as a launch gate rather than something to optimize later.

**Consent and UAE PDPL.** Recording without disclosure creates real exposure, and the liability sits with the brokerage. Product requirement, not a legal footnote: automated disclosure support, per-org retention settings, and deletion honored across transcripts and derived data.

**Incumbent moves down-market.** Gong or Avoma ships a cheap tier. This is the main strategic risk of a price-and-scope position, and the only durable answer is vertical depth plus accumulated coaching history creating switching cost.

**Audio quality.** Mobile calls in cars, noisy offices, poor connections. Word error rate degrades and extraction degrades with it. Measure ASR quality on real customer audio during Phase 1 rather than assuming benchmark numbers transfer.

---

## 11. Open questions

1. Do brokerage owners want coaching, or compliance monitoring? Different products, different buyers. The discovery calls should settle it.
2. Do their dialers record dual-channel? This determines whether diarization is a solved problem or the hardest part of the build.
3. Is the objection taxonomy stable enough to hard-code, or does it need learning per-org?
4. At what call volume does per-seat pricing break, and should self-hosted ASR come earlier than planned?

---

## Portfolio framing

*One paragraph for the case study page:*

The obvious version of this product is a Gong clone, and I want to be direct that the technology here isn't the differentiator — the scope discipline is. The first draft had nine features, a composite 86/100 call score, a north star of "revenue influenced," and four impact numbers with no derivation behind them. I cut it to four outputs, killed the composite score because single-number scoring gets gamed and reads as surveillance to the reps whose adoption you need, replaced the north star with behavior improvement rate because revenue attribution is an argument you lose in front of a CFO, and converted the impact claims into hypotheses with measurement designs attached. Then I modeled per-call inference cost, which surfaced the actual pricing decision: margin holds at 40 calls a month per rep and collapses at 150, so the product needs a minutes allowance rather than flat per-seat pricing. The riskiest assumption is extraction precision, so Phase 0 builds the pipeline against mock calls with scripted ground truth before any customer is involved.
