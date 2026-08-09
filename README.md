# CallEvals — Sahil, Phase 0

Sales call intelligence for GCC mid-market real estate brokerages: transcript in,
summary + next steps + objection tags out, plus a scored rubric, sentiment,
buying intent, coaching notes, and rule-based compliance checks per call (see
"Analytics expansion" below) — rolled up per agent, per team, and org-wide,
per period, each level with its own benchmark against its peers (see
"Agent Performance" and "Team & Organization rollups" below), with leads
tracked through a Kanban pipeline board and CRM-grade metrics — calls-to-
close, lost reasons, lead source — down to a full per-lead history (see
"Lead pipeline" and "CRM-grade lead metrics" below).
Full product spec: [docs/PRD.md](docs/PRD.md).

This repo is the Phase 0 build the PRD calls for (section 9) — prove that
extraction (F2–F4) is accurate enough to trust, against scripted mock calls,
before any customer is involved. It replaced an earlier scaffold that spiked on
two ASR/LLM providers but never attempted extraction; see "What changed" below.

## Stack, and why

Everything here runs on free tiers — no GCP billing account, no paid API:

- **ASR — `faster-whisper`, self-hosted, by default.** Runs locally on CPU, no
  API key, no per-minute billing. This is also the engine the PRD's own
  architecture diagram names and the one it expects to self-host at scale (PRD
  section 7) — so Phase 0 is already on the intended long-term path rather than
  a throwaway. **Deepgram is available as an opt-in alternative** (set
  `ASR_PROVIDER=deepgram` and `DEEPGRAM_API_KEY` in `.env`) — it gets native
  multichannel transcription (no local channel-split step) and, closer to the
  PRD's own per-minute cost assumption in section 7.
- **Extraction — Gemini Developer API free tier** (ai.google.dev), by default.
  Structured JSON output (F2 summary, F3 next steps, F4 objections), no GCP
  billing account required, unlike Vertex AI or Cloud Speech. **Groq is
  available as an opt-in alternative** (set `EXTRACTION_PROVIDER=groq` and
  `GROQ_API_KEY` in `.env`) — see "Groq extraction" below for why you'd want
  to and what the tradeoffs are.
- **Storage — filesystem**, no database. Matches the PRD's own scope discipline
  (section 8: no vector DB at MVP) — a handful of design partners don't need
  Postgres yet.

**Speaker separation** prefers dual-channel (stereo) recordings — trivial channel
split, perfect separation, no ML. The original Phase 0 plan was to label mono
audio `unknown` rather than attempt diarization at all (PRD section 5) — that
held until real testing showed most calls arriving in practice are mono, at
which point trying to identify speakers at all beat refusing to on principle.

**On the Deepgram path**, `deepgram_provider.py` now always requests
`diarize=true`. Real channel separation still wins whenever it's actually
available (free, and more reliable than diarization); diarization is used
directly for mono calls, and as a fallback for "dual-channel" files that
didn't actually separate — a real failure mode found in testing, where a
recorder mixes both parties onto one track and leaves the other channel
silent, so `multichannel=true` has nothing to split and Deepgram returns
content on only one channel index. Either way, role assignment is a
heuristic: **the diarized speaker with the most total talk time across the
call is labeled the rep**, everyone else the customer.

That specifically isn't "whoever talks first" — the first version of this
heuristic was, and real testing caught it getting the roles backwards. In an
actual phone call, whoever *answers* talks first (a bare "hello") before the
caller says anything, so on an outbound call the first voice is almost always
the customer, not the rep — the opposite of what "first speaker = rep"
assumes. Total talk time doesn't have that problem: reps pitch, explain, and
walk customers through steps, so they consistently talk more than a customer
mostly giving short replies. Still a heuristic, not a guarantee — wrong if
the customer is unusually talkative, or the call is too short for talk time
alone to distinguish the two sides. Diarization confidence also runs
noticeably lower than channel-based separation in practice — expect
occasional misattributed short turns ("okay", "yeah") even when the
rep/customer split itself is right.

**On the faster-whisper path**, mono calls still come back `Speaker.UNKNOWN`
— Whisper itself has no diarization, so matching Deepgram's mono behavior
would mean a new dependency (e.g. `pyannote.audio`), more model weights, more
CPU/GPU cost, and likely a Hugging Face token for a gated model. Not done;
dual-channel audio through faster-whisper still gets real rep/customer labels
via the local channel split, same as always.

## Call insights (agent/customer behavior signals)

Beyond F2–F4, each call gets a small set of objective, transcript-derived
behavior readouts — rep talk-time share, longest uninterrupted rep
monologue, questions asked per side, interruption count. All computed
directly from segment timestamps and text (`app/insights.py`), not via an
LLM call, so there's no added cost and no new precision risk.

Deliberately **not** a combined score: the PRD (section 5) rejected
single-number call scoring outright — "gets gamed... reads as
surveillance" — and this follows the same "flags, not scores" pattern
already used for next-step and objection extraction. Each stat is shown to
the manager individually, with no color-coding, ranking, or pass/fail
framing; what (if anything) to coach on is their call, not the tool's.

**Objection-handling completeness** extends F4 rather than adding a new
category: each objection now also carries `addressed: true/false` — did the
rep come back to it later in the call with a relevant response, or did it
just hang there. This rides the extraction LLM call that's already
happening (marginal cost only, no new API call) and is verified live: fed
`GeminiExtractor` a call where the rep offers a payment-plan alternative
after a price objection (`addressed: true`) and one where the rep changes
the subject without ever responding (`addressed: false`) — both came back
correct.

Only computed when the transcript actually distinguishes rep from customer
— a mono call with no diarization has nothing to compute these from, and
the UI says so plainly rather than showing zeros.

## Analytics expansion (2026-08-08) — score, sentiment, buying intent, coaching, compliance

A sales-manager analytics requirements doc, external to the original PRD,
called for a fuller Gong-style rubric than Phase 0 scoped. Building the gap
was an explicit product decision, made with the PRD's original reasoning
still visible rather than quietly deleted — see the dated addendum in
[docs/PRD.md](docs/PRD.md) section 5. What's new:

- **`overall_score`** (0–100) and **`score_breakdown`** — the doc's
  8-dimension weighted rubric (opening/rapport, discovery, active listening,
  pitch, objection handling, communication, closing, compliance). Every
  dimension carries a transcript-grounded evidence string, not just a
  number — the doc's own principle (its section 19): "every score should be
  supported by transcript evidence rather than being a black-box number."
  This is the one output that directly reverses a PRD cut (composite call
  scoring, cut for gaming/surveillance risk) rather than extending prior
  scope, and that tension is called out, not hidden, in the PRD addendum.
- **`sentiment`** — overall + beginning/middle/end arc, plus signal phrases
  and a confidence figure. Also a direct reversal of a PRD cut (sentiment
  was rejected as low-precision and the least actionable output in this
  category) — kept explicitly labeled as an AI-derived read, never a fact.
- **`buying_intent`** — level (high/medium/low), the quotes that drove it,
  and a follow-up-priority recommendation. Deliberately kept separate from
  sentiment: a positive customer isn't necessarily a ready one.
- **`coaching`** — top strength/weakness and one behavior each to stop,
  continue, start, each grounded in the specific call rather than generic
  advice.
- **Objection taxonomy: 3 → 10 categories** (price, timing, competitor,
  need, trust, authority, product, implementation, contract,
  switching_cost) — the PRD's original three were a deliberate precision
  trade-off ("three, not five, because narrow scope keeps precision high");
  widening to ten trades some of that back for coverage, and the precision
  eval needs re-running at the new taxonomy's scope before trusting it at
  the original bar.
- **`compliance`** — the one new output that is *not* an LLM call:
  `app/compliance.py` runs deterministic keyword/phrase rules over the
  transcript (required intro, required recording disclosure, prohibited
  guaranteed-return claims, unapproved-discount mentions) and reports
  pass/fail/detected per rule plus an adherence percentage. Same
  zero-marginal-cost, no-new-precision-risk shape as `app/insights.py`. The
  recording-disclosure rule specifically exists because the PRD (section 10)
  already flags UAE PDPL consent as a product requirement, not a legal
  footnote — this is what "automated disclosure support" turns into as a
  check. The seeded rule set is illustrative for the Dubai/Abu Dhabi
  brokerage ICP (PRD section 3), not a compliance guarantee; a real
  deployment needs an org-supplied rule list, which the doc itself asks for
  (section 14: "create configurable rules based on the company's sales
  process").

**Architecture:** sentiment, buying intent, coaching, and the 7 LLM-scored
rubric dimensions all ride the same single Gemini structured-output call
that already produces F2–F4 — marginal cost only, no new API call, same
pattern already used for `addressed` on objections. `overall_score` is
computed in `pipeline.py` by summing those 7 dimensions with the
compliance-derived 8th (`adherence_pct / 100 * 5`), not returned by the
model directly, so the one number that's most exposed to gaming risk is at
least partly grounded in a deterministic check rather than being 100%
LLM-judged.

**Verification status — deliberately not oversold.** The new extraction
fields were smoke-tested live against `gemini-2.5-flash` on a realistic
6-turn mock call and came back well-formed and sensible (correct sentiment
arc, evidence-grounded dimension scores, a concrete coaching read). The full
precision-eval re-run against all 6 mock calls — needed to get real
numbers on the *expanded* objection taxonomy specifically, since precision
against 10 categories isn't guaranteed to match precision against 3 — was
blocked by the Gemini free tier's daily request quota (20 requests/day per
model) being exhausted by prior runs in this session. `app/compliance.py`
is unit-tested directly (`tests/test_compliance.py`) since it's
deterministic and needs no API key. Re-run
`python -m eval.run_precision_eval` once the daily quota resets (or against
a paid-tier key) before treating the wider objection taxonomy as being at
the same precision bar as the original three categories.

## Agent Performance (2026-08-08) — cross-call rollups per rep, per period

A second requirements doc asked for an "Agent Performance" page: not another
per-call output, but "given all the calls this agent handled in a period,
how well are they performing, and is it improving?" That's a different
shape of feature — it needed two foundational pieces that didn't exist
before this pass, and it deliberately does *not* build everything the doc
asked for.

**Foundation (superseded 2026-08-08 by the "Roster & leads" section below —
kept here for history, not current):**

- ~~`CallRecord.agent_name`~~ — a required free-text field at upload time.
  Replaced by a real `agent_id` foreign key into a managed roster; see
  "Roster & leads" below.
- ~~`CallRecord.outcome` (`CallOutcome`)~~ — a manager-set funnel stage +
  deal size on the *call*. Replaced by `Lead.stage`, since a lead can span
  many calls and the call-level version had no way to represent that
  without an arbitrary "which call owns the outcome" choice. See "Roster &
  leads" below for what replaced it and why.

This section originally described those two fields as the foundation for
everything that follows; the aggregation logic they fed
(`app/agent_performance.py`, described next) is unchanged in shape, just
rewired onto the real roster/lead model.

**`app/agent_performance.py`** computes the full rollup — pure aggregation
over `CallRecord`s already in storage, no LLM call, same zero-marginal-cost
shape as `insights.py` and `compliance.py`: overview KPIs, an 8-dimension
agent score, talk-time/discovery/objection aggregates, closing-funnel and
conversion analytics, sentiment movement, buying-intent-to-conversion,
quality distribution, a consistency score (100 − stdev of per-call scores —
"how reliably good," not just "how good"), a weekly trend, strengths/
weaknesses backed by real sampled evidence (not generated text), rule-based
coaching recommendations, team benchmarking against other agents' calls in
the same period, and the quality-vs-outcome 2×2 matrix. Exposed via
`GET /api/agents` and `GET /api/agents/{name}/performance?start=&end=`, and
a new "Agent Performance" tab in the frontend with an agent + date-range
picker.

**Two things this doc asked for are explicitly not built, not silently
skipped** — every report carries a `notes` field naming them:

1. **Dialer-level call volume** (calls assigned/attempted/connected/missed).
   This app only ever sees a call once someone uploads a recording — there's
   no data source for "attempted but never connected." Only
   `calls_analyzed` (successfully processed uploads) is shown.
2. **Itemized discovery fields** (need/budget/timeline/decision-maker
   identified individually, as separate percentages). The per-call
   extraction only produces one aggregate discovery score + evidence string;
   adding seven new boolean fields there is a schema change out of scope
   for this pass. Only the aggregate score is rolled up.

**Rubric reconciliation.** This doc's Agent Score (Discovery 20% / Objection
15% / Pitch 15% / Closing 15% / Communication 10% / **Sentiment 10%** /
Compliance 10% / **Call Discipline 5%**) doesn't match the `ScoreBreakdown`
rubric already built and tested (Opening&Rapport 10 / Discovery 20 / Active
Listening 10 / Pitch 15 / Objection 15 / Communication 10 / Closing 15 /
Compliance 5 — no scored Sentiment, no Call Discipline). Rather than touch
the already-verified per-call extraction prompt again, the remap happens
only at the aggregation layer: Opening/Rapport + Active Listening +
Communication/Professionalism are averaged into one "Communication"
dimension, the per-call sentiment label is converted to a 0–100 score
(positive=100/neutral=60/negative=20), and Call Discipline — which has no
defined scoring method in either source doc — is excluded, with the
remaining 7 weights renormalized from 95 back up to 100 rather than
silently capping the total below it.

**Verification status.** The aggregation math is unit-tested directly
(`tests/test_agent_performance.py`, 14 tests covering the weight
renormalization, consistency scoring, funnel-leakage detection, conversion
math, and team-benchmark isolation) with no API key needed — it's pure
computation, same as the compliance tests. The full dashboard was then
browser-tested live end to end (Playwright, not just `npm run build`):
backend and frontend dev servers started for real, 18 synthetic-but-
realistic `CallRecord`s seeded directly into storage for two different
agents (bypassing the ASR/Gemini pipeline, which the exhausted free-tier
quota can't currently drive at this volume), and every panel — score
breakdown, talk time, objections, funnel, conversion, sentiment, buying
intent, quality distribution, weekly trend, strengths/weaknesses with real
sampled evidence text, coaching recommendations, team benchmark — confirmed
rendering correctly with zero console errors, including switching between
agents and seeing genuinely different numbers. The one thing not yet
exercised against a *real* multi-call dataset is the full pipeline end to
end at this volume (12+ calls through actual ASR + Gemini extraction) —
that's a quota/budget question, not a correctness one.

**What this layer is not, yet:** call-level context beyond one agent's own
calls — clicking through to TEAM or ORGANIZATION rollups is covered in
"Team & Organization rollups" below.

## Roster & leads (2026-08-08) — real identity, CRM-grade conversion

[docs/ROADMAP.md](docs/ROADMAP.md) Phase A + C1, for the target scenario of
~100 agents across 10 teams under 10 managers. Two things didn't exist
before this pass and everything else in this section depends on them:

- **A real roster.** `agent_name` (free text) is gone. Every call now
  carries `agent_id`, a foreign key into a managed `Team`/`Agent` roster
  (`POST /api/teams`, `POST /api/agents`, `PATCH /api/agents/{id}`, plus
  `POST /api/agents/import` for bulk CSV/JSON onboarding — standing up a
  100-agent org one API call at a time isn't realistic). A manager is an
  `Agent` record with `is_manager: true` and a `Team.manager_agent_id`
  pointing at them, not a separate entity — no reason to duplicate a
  person's identity depending on whether they also take calls.
- **A real `Lead` entity.** A prospect gets called more than once before
  converting; the old call-level `CallOutcome` had no way to represent
  that — five calls to the same person looked like five independent,
  possibly-contradictory outcome tags. Now every call also carries
  `lead_id`, and the lead's funnel stage (`POST /api/leads/{id}/stage`) is
  the single source of truth for conversion, with a full `stage_history`
  audit trail (who set it, when) rather than a value that silently
  overwrites itself.

**Addendum (2026-08-08) — `lead_id` no longer has to already exist.** The
first version of this required calling `POST /api/leads` before you could
upload a call against it, on the theory that "API-only for now" was an
acceptable stopgap without a lead-creation UI. In practice that was pure
friction — a manager typing an arbitrary tracking number into the upload
form got a 400 telling them to go create the lead first, for no benefit.
`lead_id` is now caller-chosen and free-form: type a phone number, a CRM
deal ID, or anything else you already use to track a prospect, and
`lead_storage.get_or_create` makes it a real `Lead` on first use
(`display_name` defaults to `"Lead {id}"`, `assigned_agent_id` defaults to
whoever uploaded it). Reusing the same value on a later call attributes it
to the same lead rather than creating a duplicate — that's the "unique"
part, and it's exactly the behavior the `Lead` entity existing separately
from `Call` was for in the first place. `agent_id` did **not** get the same
treatment and still requires a real roster entry — an agent is a managed
list a manager actually curates; a lead identifier is whatever a manager
is already using to track a prospect, which this app has no business
gatekeeping.

**The one correctness property that actually matters here, and is
unit-tested directly:** a lead currently sitting at "won" only counts
toward a period's `conversion_rate_pct` if its `stage_history` shows it
*transitioning* to won during that specific period — not merely being won
by the time someone runs the report. A lead that converted in June doesn't
retroactively inflate August's numbers just because its current stage
still reads "won." `ClosingAgg` (funnel counts) and `ConversionAgg`
(conversion rate) deliberately answer different questions for exactly this
reason — see both classes' docstrings in `schemas.py` — and can legitimately
disagree: a lead can show up in this period's "won" *snapshot* while
contributing zero to this period's *conversion rate*, if it won earlier.

**Team benchmarks got more honest as a side effect.** Before the roster
existed, "team benchmark" in the Agent Performance dashboard was computed
against *every other agent in the org*, because there was no real team
concept to benchmark against. Now it's computed against actual teammates
only — confirmed live: two agents on different teams with different
average scores now produce genuinely different, correctly-scoped benchmark
numbers, and an agent with no team (or a team with no other active
teammates yet) gets an explicit note instead of a benchmark quietly
computed from the wrong population.

**Manual, not CRM-integrated, and that's deliberate.** There's still no
dialer/CRM integration (PRD section 8 defers that to Phase 2) — a lead's
stage is a fact a manager records, same as before, just attached to the
right entity now. `assigned_agent_id` on a Lead doesn't have to match the
`agent_id` on any particular call to it (someone can cover a call for a
teammate without reassigning the lead), and there's no dedup-by-phone-number
safeguard yet, so creating a duplicate `Lead` for a prospect who already
has one is possible — noted as a real gap in ROADMAP.md rather than solved
here.

**Upgrading an existing deployment with real historical calls?** This
schema change broke a real user's environment the same day it shipped:
`GET /api/calls` started 500ing with `agent_id`/`lead_id` "Field required"
on every call saved before this pass, because those records only had the
old `agent_name`/`outcome` fields. If you have calls in `server/data/`
from before this update:

```bash
cd server && source .venv/bin/activate && python -m scripts.migrate_legacy_calls
```

This backfills each old record with a real `Agent` (deduped by the old
`agent_name`) and a new `Lead` per call (carrying over the old
`outcome.stage`/`deal_size_aed` if one was set) rather than discarding
anything. It's idempotent — safe to run again, records already on the
current schema are left untouched. `storage.list_all()` was also hardened
separately to skip an unreadable record with a logged warning instead of
crashing the whole endpoint, so one un-migrated file can no longer take
down the entire call list for everyone.

**Verification.** 42 new/updated backend tests: `test_roster_storage.py`
and `test_lead_storage.py` (filesystem persistence, including that
`stage_history` is appended to, never overwritten), a full rewrite of
`test_agent_performance.py` (17 tests, including the period-scoped
conversion property above and a test that specifically proves team
benchmarks exclude non-teammates), and new `test_roster_router.py` /
`test_leads_router.py` covering the CRUD + bulk-import + validation paths.
All backend tests run against an isolated temp directory
(`tests/conftest.py`) rather than the real `server/data/` — the previous
test suite didn't need this because nothing wrote through the API before;
adding roster/lead CRUD endpoints changed that, and the fix landed before
any test could pollute real data. The full stack was then verified live,
through the real API, not synthetic shortcuts: teams and agents created via
`POST /api/teams`/`POST /api/agents`, leads via `POST /api/leads`, stages
set via `POST /api/leads/{id}/stage`, calls attributed to the resulting
real IDs, and the Agent Performance dashboard confirmed rendering correct,
agent-specific team-benchmark numbers for two agents on different teams —
zero console errors, real data throughout except the ASR/Gemini pipeline
itself (still gated by the free-tier quota noted above).

**Demo roster.** `server/scripts/seed_demo_roster.py` populates exactly the
target scenario — 10 teams (Dubai/Abu Dhabi neighborhood names, for
flavor) x 10 agents each (one manager per team) — with randomly-combined
first/last names from pools reflecting the PRD's ICP, none referring to a
real person — plus 4 explicitly-requested real names (Himanshu, Rohan,
Rajveer, Purab), added unassigned to any team since none was specified,
kept in a separate `EXTRA_AGENT_NAMES` list so the file is honest about
which names are synthetic and which aren't. IDs are `uuid5`-derived from
each name, so it's idempotent — safe to re-run after editing the pools
without creating duplicates. Demo data only; never presented as, or
intended to look like, real customer data. Run it with:

```bash
cd server && source .venv/bin/activate && python -m scripts.seed_demo_roster
```

## Team & Organization rollups (2026-08-08) — the full CALL → AGENT → TEAM → ORGANIZATION hierarchy

[docs/ROADMAP.md](docs/ROADMAP.md) Phase B. Extends the Agent Performance
layer one and two levels up, rather than reinventing it: the aggregation
math that used to live entirely inside `agent_performance.py` was
extracted into a new **population-agnostic engine**,
`app/performance_metrics.py`. Its functions take an already-filtered
`list[CallRecord]` and have no idea whether that list is one agent's
calls, one team's calls, or every call in the org — each level's own
module does the filtering and calls the same engine:

- `app/agent_performance.py` — filters to one `agent_id` (unchanged
  behavior, now a ~80-line wrapper instead of ~615 lines of inline math).
- `app/team_performance.py` (new) — filters to every agent on one team;
  peer group for benchmarking is every *other* team.
- `app/org_performance.py` (new) — no filtering at all, every call in the
  period; no peer group (there's one org, nothing to benchmark it against).

New endpoints: `GET /api/teams/{id}/performance` and
`GET /api/organization/performance`, same `start`/`end` query params as
the agent endpoint. Both return a report built on the same
`PerformanceMetrics` base Pydantic class `AgentPerformanceReport` already
used (fields flatten into the subclass, not nested — no JSON shape change
for the existing agent report), plus a level-specific `agent_leaderboard`
or `team_leaderboard` (`LeaderboardRow`: id, name, overall score,
conversion rate, calls analyzed — sorted best-first, unscored entries last
rather than omitted).

**Frontend: one Organization tab, not three disconnected pages.** It opens
on the org-wide rollup with a team leaderboard; clicking a team row drills
into that team's rollup (same panels, filtered population, plus an "Org
average" benchmark and an agent leaderboard) in place, with an "← All
teams" link back. Clicking an agent row on the team view hands off to the
existing Agent Performance tab, pre-selected to that agent — completing
the drill from ORGANIZATION down to a single AGENT (and from there, the
Calls tab already reaches individual CALLs). All 7 of the Agent
Performance dashboard's panel components are reused as-is at the team/org
level — they took small optional `title`/`benchmarkTitle` props (defaulting
to their original agent-level text, so the Agent Performance tab needed no
changes) rather than being duplicated. Only one component is net-new:
`LeaderboardPanel`.

**A real bug the test suite couldn't have caught, found by actually
clicking through the UI.** Switching levels (org → team, or back) sets
`teamId` and lets a `useEffect` fetch the new report — but React renders
*once* in between with the new `teamId` and the *still-old*,
differently-shaped report (`team_leaderboard` vs. `agent_leaderboard`)
before that fetch lands. `LeaderboardPanel` crashed reading `.length` off
a field that didn't exist on that report shape, taking down the whole
page — a pure frontend state-sequencing issue invisible to any backend
test. Fixed by setting `loading` synchronously inside the same click
handler that changes `teamId` (`OrganizationPage.js`'s `selectTeam`), so
the inconsistent-shape render is skipped entirely rather than papered over.

**Verification.** 25 new backend tests — `test_performance_metrics.py`
(the shared engine directly: `distinct_leads`, `reached_stage_in_period`,
`peer_benchmark` with an empty peer population, population-agnostic
pooling), `test_team_performance.py` (team pooling is by call volume, not
an average of per-agent averages; agent leaderboard sorting; org-benchmark
correctly isolates *other* teams, not teammates), `test_org_performance.py`
(org-wide pooling, team leaderboard, confirming `OrgPerformanceReport` has
no peer-benchmark field at all), plus router tests for both new endpoints
— 133 backend tests passing overall, including all 17 pre-existing
agent-performance tests unchanged (pure refactor, confirmed no behavior
drift). Then a live pass against the real seeded roster (10 teams/100
agents): two synthetic calls saved directly to two different teams, one
lead tagged to WON, backend responses spot-checked with `curl`, then the
actual running frontend driven with Playwright through
Organization → Corniche Team → Ahmed Hussain, catching the bug above,
fixing it, and re-confirming the full click-through before cleaning the
synthetic calls/lead back out of `server/data/`.

## Groq extraction (2026-08-08) — opt-in alternative to Gemini

**Why:** Gemini's free tier caps out at 20 `generate_content` requests/day,
*total, per project, per model* — not per user, not per call. That's not a
theoretical constraint; it's the exact error this app throws once a normal
day of testing/demoing burns through the quota:
`429 RESOURCE_EXHAUSTED ... GenerateRequestsPerDayPerProjectPerModel-FreeTier
... limit: 20`. The fix that actually scales is a paid Gemini tier (see
ROADMAP.md F3), but for demoing or developing past the daily wall *today*
without attaching billing, Groq's free tier supports far more request
volume, at the cost of extraction quality coming from an open-weight model
(Llama) instead of Gemini.

**What changed to add it.** The prompt, wire schema (the Pydantic shape the
model's JSON is validated against before becoming an `ExtractionResult`),
and the Wire→domain mapping used to live entirely inside
`gemini_extractor.py`; they're now shared in `app/extraction/common.py` so
adding a second provider didn't mean copy-pasting ~160 lines of prompt and
schema. `app/extraction/groq_extractor.py` calls Groq's OpenAI-compatible
`chat/completions` endpoint directly via `httpx` (already a dependency —
same pattern as `deepgram_provider.py`; no new SDK added for one endpoint),
with `response_format: {"type": "json_object"}` and an explicit JSON-shape
reminder appended to the prompt. `app/extraction/factory.py` selects the
provider from `EXTRACTION_PROVIDER` in config the same way
`app/asr/factory.py` already does for ASR — Gemini stays the default, so no
existing deployment's behavior changes without opting in.

**The real difference from Gemini, and why it matters.** Gemini's
`response_schema` mode constrains the model's output at decode time — it
structurally cannot emit a shape that doesn't validate. Groq (and most
open-weight-model APIs) has no equivalent; `json_object` mode only
guarantees the response parses as *some* JSON, not this JSON. Pydantic
validation against the same `WireExtractionResult` schema both providers
share is what actually enforces correctness on the Groq path — a
shape-mismatched response fails loudly as a `ValidationError` (surfaced to
`record.status = "failed"` / `record.error` same as any other pipeline
failure) rather than silently becoming a wrong or partially-empty call
review. Expect to need more prompt iteration and a real precision run
(`eval/run_precision_eval.py` is Gemini-hardcoded today, not yet
provider-parameterized) before trusting Groq's numbers at the same bar as
the Gemini precision results already in this README.

**Verification.** 9 new backend tests: `test_extraction_factory.py`
(defaults to Gemini, selects Groq when configured, clear error on a missing
key — mirrors `test_asr_factory.py`) and `test_groq_extractor.py` (missing
key raises, a successful response maps correctly including
segment-index→timestamp resolution, the request is sent with the configured
model and JSON mode, malformed JSON content raises, JSON that doesn't match
the wire shape raises a `pydantic.ValidationError`, and a non-2xx response
raises with the response body included, not just the status code) — all
against a mocked `httpx.post`, same pattern as the existing Deepgram tests,
no network call.

**This sandbox cannot reach Groq at all to verify any of this against the
real API** — its outbound proxy blocks `api.groq.com` and
`console.groq.com` outright (policy denial, confirmed via the proxy's own
status endpoint and a blocked `WebFetch`), so unlike Gemini and Deepgram
(both confirmed working end to end against real APIs earlier in this
README's "Known limitations" section), nobody building from this
environment can independently verify Groq's response shape/behavior or
check whether `GROQ_MODEL`'s value is still a live model id. That gap
turned out not to be hypothetical: `llama-3.3-70b-versatile` (this
repo's original default) got decommissioned by Groq and started 404ing
in production — a real user hit `404 Not Found` from
`api.groq.com/openai/v1/chat/completions`, which read as a broken
integration. Two things were wrong, fixed together:

1. `response.raise_for_status()` raised with only the status code,
   dropping the response body — the one place Groq puts the actual reason
   (`"code": "model_decommissioned"` for a retired model, indistinguishable
   from a wrong-URL 404 without it). Now raises with the full body
   included.
2. `GROQ_MODEL` now defaults to `openai/gpt-oss-120b`, confirmed live
   against the real API by that same user (not from this sandbox — it
   still can't reach Groq). JSON mode
   (`response_format: {"type": "json_object"}`) stayed in the request; an
   earlier draft of the fix dropped it, but the user confirmed that was
   just simplification while debugging, not something the new model
   required removing, so keeping it is strictly safer.

Groq rotates model ids over time regardless of what's default today —
check https://console.groq.com/docs/models if this one goes stale too;
there's no way to keep it current without network access to Groq, which
this dev environment does not have.

**Third incident (2026-08-09): one bad objection category failed the
whole call.** A real upload hit `Processing failed: 1 validation error for
WireExtractionResult objections.1.category ... Input should be 'price',
'timing', ... 'switching_cost' [input_value='taxes']`. The extractor
invented `taxes` as an objection category — a real, plausible objection
in a real-estate call, just not one of the 10 the prompt (and the
`ObjectionCategory` enum) asks for. Groq's open-weight models have no
schema-constrained decoding the way Gemini's `response_schema` mode does
(see above), so nothing actually stops a model from returning a value
outside the taxonomy despite the prompt saying "skip anything that
doesn't clearly fit."

The bug wasn't the invented category itself — some drift there is
expected from an LLM boundary — it was the blast radius: Pydantic
rejected the *entire* `WireExtractionResult` over that one field,
discarding a correctly-extracted summary, score breakdown, next steps,
sentiment, buying intent, coaching, and every *other* valid objection
along with it, and forcing a full re-upload (re-paying ASR + LLM cost) to
get anything at all.

**Fix:** `sanitize_wire_payload()` in `app/extraction/common.py` runs on
the raw JSON dict before Pydantic validation, for both providers (this
wasn't Groq-specific — Gemini's `response.parsed` can also fall back to
manual parsing). It drops only the objection(s) with an unrecognized
category (logged via `logging.warning`, not silent) and normalizes case
(`"Price"` → `"price"`) rather than losing a valid objection to a casing
mismatch. Everything else in the payload is untouched — a manager loses
one objection tag on the call, not the entire analysis.

**Verification.** 5 new tests in `test_gemini_extractor_helpers.py`:
drops an out-of-taxonomy category while keeping valid ones, normalizes
case, leaves an all-valid payload byte-for-byte unchanged, tolerates a
missing/non-list `objections` key, and an end-to-end regression that
replays the exact reported payload shape (`category='taxes'` alongside a
valid `price` objection) through `WireExtractionResult.model_validate`
and confirms it now succeeds with the one valid objection surviving.
Caught a real bug in the first draft of the fix during this pass: the
function's "did anything change" tracking only fired on *drops*, so a
category that was valid-but-differently-cased (`"Price"`) got silently
kept unnormalized because the function took its early-return path before
applying the casing fix — the normalize-case test failed against the
real function, not a hypothetical, and pointed straight at the bug. Fixed
by tracking "changed" (drop OR normalize) instead of "dropped" alone.
163 backend tests passing overall.

## Lead pipeline (2026-08-08) — Kanban board, ROADMAP.md C5

**Why this before C2–C4/C6:** taken out of order at explicit request — it's
the most visibly CRM-like piece of Phase C, and turned out to need zero
backend changes to build. `GET /api/leads` (already supports
`assigned_agent_id`/`stage`/`q` filters) and `POST /api/leads/{id}/stage`
already covered everything a board needs; `lead_storage.set_stage` has
never restricted which stage a lead can move to from which, so every
column-to-column move is already a valid write.

**What it replaces.** Until now, changing a lead's stage meant opening one
of its calls and using the `<select>` dropdown in `LeadPanel` (still there,
unchanged, for in-context editing while reviewing a specific call). The new
`Leads` tab adds an org-wide view: six columns (Untagged → Qualified → Demo
booked → Proposal sent → Won / Lost), an agent filter, and a name/phone
search — reusing the same filters `GET /api/leads` already had.

**Two ways to move a card, one code path.** Cards are natively draggable
(`draggable`/`onDragStart`/`onDrop` — no drag-and-drop library added) for
the primary Kanban interaction, and every card also has `‹`/`›` buttons
that step to the adjacent stage in `FunnelStage` order. Both call the exact
same `moveLead` function and the exact same `POST /api/leads/{id}/stage`
request — the buttons are a keyboard/touch-accessible fallback, not a
second, divergent implementation. Dropping (or arrow-moving) a lead into
Won without an existing `deal_size_aed` opens a small modal to capture it,
skippable rather than mandatory — matches `LeadPanel`'s existing behavior
of treating deal size as optional even for a won lead. The Won column
header shows a running total of every visible deal there, computed
client-side from whatever leads are currently loaded (respects the active
agent filter/search — it's a sum of what's on screen, not a separate
server-computed number).

**Verification.** No new backend tests — no backend code changed; C5 is a
pure consumer of endpoints Phase A's `test_leads_router.py` already covers.
Live-verified instead: real leads created via the actual API across two
agents on different teams and four different stages (including one already
Won), then driven through the real running frontend with Playwright —
dragged a card between columns, used the arrow-button fallback, dragged a
card into Won and confirmed the deal-size modal appears and the column
total updates correctly to the sum of both Won deals, and confirmed the
agent filter and search both narrow the board — zero console errors.
Seeded leads removed from `server/data/` afterward.

## CRM-grade lead metrics (2026-08-08) — ROADMAP.md C2, C3, C4, C6

The rest of Phase C, shipped in one pass after C5. Together with C1
(lead-level conversion, in "Roster & leads" above) and C5 (the Kanban
board, above), this closes out every Phase C line item.

- **C2 — calls-to-close.** New `CallsToCloseAgg` on the shared
  `PerformanceMetrics` base (so it's on every agent/team/org report for
  free): `calls_per_lead_distribution` buckets every distinct lead touched
  in the period ("1 call", "2 calls", "3-4", "5+"), and
  `avg_calls_to_close`/`avg_days_to_close` are computed only over leads
  that transitioned to won *within that period* — counting only calls
  placed up to and including the day of that transition. A courtesy call
  placed after the deal already closed does not inflate "how many calls
  did it take" — confirmed with a test that places a 3rd call after the
  won date and checks it's excluded from the average.
- **C3 — lost reasons.** New `LostReason` enum (price / timing /
  competitor / financing / unresponsive / not_qualified / changed_mind /
  other) and `Lead.lost_reason`, settable via the existing
  `POST /api/leads/{id}/stage` (now takes an optional `lost_reason`
  alongside `deal_size_aed`). `LostReasonAgg`'s breakdown uses
  current-snapshot semantics, same as `ClosingAgg.lost_leads` — a lead
  lost without a reason recorded (pre-C3 data, or a manager who skipped
  the field) is counted in `ClosingAgg.lost_leads` but not in
  `LostReasonAgg`, by design; see both classes' docstrings.
- **C4 — lead source.** `Lead.source` already existed as free text, but
  there was no way to ever set it after a lead's creation — not even via
  the API. Added `PATCH /api/leads/{id}` (display_name/phone/source) to
  close that gap, which `lead_storage.get_or_create`'s own docstring had
  already flagged as missing. `SourceAgg` groups touched leads by their
  raw source string and reports a conversion rate per source, bucketing
  untagged leads under `"Unknown"` rather than dropping them — no fixed
  channel taxonomy is enforced, matching the deliberate choice already
  documented on the `source` field itself.
- **C6 — lead detail + reassignment history.** Call history and the
  stage-change audit trail already existed in the API (`LeadDetail.calls`,
  `Lead.stage_history`) — they just had no page. Reassignment history did
  not exist *at all*: there was no way to change a lead's
  `assigned_agent_id` after creation, full stop. New `AssignmentEvent`
  schema, `Lead.assignment_history` (append-only, same pattern as
  `stage_history`), `lead_storage.reassign()`, and
  `POST /api/leads/{id}/reassign` close that gap. The new
  `LeadDetailModal` surfaces all three — stage history, assignment
  history, call history — plus a reassign control, reached via a
  dedicated "view details" (ⓘ) button on each Kanban card rather than the
  card itself, since the card is also a drag handle and click-after-drag
  is inconsistent across browsers.

**Frontend.** `LeadPanel` (the in-context stage editor on `CallDetail`)
gained a `lost_reason` dropdown that appears when stage is set to Lost
(mirroring the existing `deal_size_aed`-when-Won pattern) and a `source`
field with a `<datalist>` of common suggestions (Website, Referral,
Walk-in, Portal, Social media, Cold call) plus free text. The Kanban board
gained a matching skippable lost-reason modal on dropping (or
arrow-moving) a card into Lost, same shape as C5's Won deal-size modal,
and the reason now shows on the card. A new `AgentPipelineInsightsPanel`
(calls-to-close distribution, lost-reason breakdown, lead-source
breakdown) is wired into both the Agent Performance page and the
Organization page, next to the existing funnel/conversion panel — free at
every rollup level since it reads fields already on `PerformanceMetrics`.

**Verification.** 16 new backend tests across `test_performance_metrics.py`
(the post-close-call exclusion above, lost-reasons only counting leads
with a reason recorded, source grouping including the Unknown bucket),
`test_lead_storage.py` (`lost_reason` persists without being cleared by a
later stage change with no reason of its own; `reassign` appends to
`assignment_history`), and `test_leads_router.py` (the `/stage` endpoint's
new `lost_reason` field, the new `/reassign` endpoint including rejecting
an unknown agent, and the new `PATCH /{lead_id}` including rejecting a
blank display name) — 158 backend tests passing overall. Then a live pass:
four leads seeded directly against `storage`/`lead_storage` covering a won
lead with a post-close courtesy call, a lost lead with a reason, and two
different sources (one lead with none, to exercise the Unknown bucket),
driven through the real running frontend with Playwright — the three new
Agent Performance panels confirmed rendering correct numbers, a drag into
Lost confirmed opening the reason modal and showing the reason on the card
afterward, the detail modal confirmed showing stage/call history and a
live reassignment appearing immediately in assignment history, and
`LeadPanel`'s new lost-reason/source fields confirmed saving correctly
from the Calls tab.

Two real issues were caught and fixed during this pass, neither of which
any backend test could have caught:

1. **Not a product bug — a test-viewport issue.** The first drag-into-Lost
   attempt appeared to silently do nothing (no modal, lead stayed put).
   The Kanban board had grown to 6 columns plus more leads than C5's
   original verification pass; at the default Playwright viewport width,
   the Lost column was outside the horizontal scroll area, and the
   simulated drag didn't reliably complete against an off-screen target.
   Widening the test viewport (not the app) resolved it and confirmed the
   underlying drag logic was correct the whole time.
2. **A real CSS bug in `LeadDetailModal`.** Its two history columns used
   plain `<section>` elements instead of `<section className="panel">`,
   so they never picked up the `.call-detail-columns .panel { flex: 1 }`
   rule everywhere else in the app relies on — `.insights-list` rows
   collapsed to content width, so labels ran directly into their
   timestamps ("Won8/8/2026, 7:58:53 PM") with no visible gap. Fixed with
   a scoped `.lead-detail-modal .call-detail-columns > section` rule
   rather than adding the `.panel` class outright, since nesting another
   bordered card inside the modal (itself already a `.panel`) would have
   looked doubled-up.

Seeded leads/calls removed from `server/data/` afterward.

## Visual design refresh (2026-08-08) — dark theme reskin

**What.** A full visual restyle of all four tabs (Calls, Agent Performance,
Organization, Leads) plus the CallDetail and Kanban-modal views, using a
dark "command deck" theme (purple/cyan accent palette, monospace labels,
sidebar navigation) as reference. Requested against an imported Claude
Design mockup (`Call Intelligence.dc.html`) that used fictional data and a
fictional product name ("VoxPrism"); per explicit direction this was used
purely as a visual/interaction reference, never ported literally. Three
scope decisions were confirmed up front: (1) reskin all four tabs, not
just one; (2) for the mockup's features with no backend today (AI chat
assistant, per-call deal-risk scoring, topic/competitor extraction, audio
waveform playback), build real-data UI wherever an equivalent already
exists and an honestly-labeled placeholder — never fabricated numbers or
canned responses — for what doesn't; (3) keep the CallEvals product name
and branding, not the mockup's.

**What changed.**
- `App.css` rewritten around a CSS custom-property design-token system
  (`--bg-base`, `--accent-purple`, `--font-mono`, etc.) — dark background,
  purple/cyan/green/amber/rose accents, "Space Grotesk"/"JetBrains Mono"
  font-family names in the stack (no external font fetch — see below).
- `App.js` rewritten around a sidebar-nav shell (`.app-sidebar`,
  `.side-nav`) replacing the old top-tab bar, plus a topbar with a
  breadcrumb/title per tab and an "Ask CallEvals" button. The Calls badge
  in the nav and the sidebar's "model status" widget both show real
  counts (`calls.length`, live `processingCount` from the actual call
  list) — no fabricated latency/throughput numbers.
- Two new shared chart primitives, `Sparkline.js` and `TrendLineChart.js`
  — small reusable inline SVGs that only render when the caller has a real
  ≥2-point numeric series to plot; both take real `PerformanceMetrics`
  data (`report.trend`), never synthetic/randomized data.
- `AgentOverviewPanel.js` gets real sparklines on exactly the 3 of 7 KPI
  tiles that actually have a per-week series in `report.trend`
  (`avg_score`, `calls`, `conversion_rate_pct`); the other 4 (qualified-lead
  rate, sentiment, compliance, trend-vs-prior) deliberately get none.
- `AgentQualityTrendPanel.js`'s Weekly Trend section gets a
  `TrendLineChart` (score + conversion, dual-line) above the existing
  precise numeric table, which stays for exact lookups.
- The "Ask Prism" AI assistant from the mockup became "Ask CallEvals" — a
  toggleable panel with plainly-labeled placeholder copy, not a working
  chat, since there is no backend for it.
- CallDetail, the Kanban board, and all three lead modals (Won-size
  prompt, Lost-reason prompt, `LeadDetailModal`) needed **no
  component-level changes** — they already inherit the new theme
  correctly through shared `.panel`/`.modal`/`.insights-list` classes,
  confirmed by screenshot review rather than assumed.

**Two real bugs found and fixed during the rewrite**, neither reachable by
a backend test:
1. `.kpi-tile` silently lost its `display: flex; flex-direction: column`
   during the CSS rewrite (present in the prior theme, dropped by
   omission), collapsing KPI value/label onto one line instead of
   stacking them. Fixed, plus JSX in `AgentOverviewPanel.js` reordered so
   label renders before value in every tile (matches the intended reading
   order).
2. `.kpi-label` had no minimum height, so tiles with a longer wrapping
   label (e.g. "QUALIFIED-LEAD RATE") pushed their value down relative to
   tiles with a short single-line label, misaligning the whole KPI row's
   value baseline. Fixed with a `min-height` on `.kpi-label` sized to the
   longest label at two lines.

**A real reliability issue found, not shipped.** The first draft of
`App.css` pulled "Space Grotesk"/"JetBrains Mono" via a Google Fonts
`@import url(...)`. `curl` reached the URL fine (200 OK), but the actual
Playwright/Chromium browser context hit `net::ERR_CONNECTION_RESET` on it,
and a second run hung for the full 30s `networkidle` timeout waiting on
the retrying request — a genuine failure mode on any network that can't
reach `fonts.googleapis.com`, not just this sandbox. Fixed by dropping the
`@import`/`<link>` entirely; the font-family *names* stay in the CSS
stacks as harmless first-choice values (falling back to `system-ui`)
since referencing an unavailable family name triggers no network request
— only `@import`/`<link>`/`@font-face` do.

**Verification.** 158 backend tests still passing (this was a
frontend-only change). Live Playwright pass across all four tabs, the
CallDetail page, and the Kanban lead-detail modal, screenshotted and
reviewed panel-by-panel against the previous theme's class list (`comm
-23` diff on extracted selectors, confirming only 3 selectors —
`.app-header`/`.app-nav`/`.subtitle` — were intentionally dropped, matching
the shell restructure, with nothing else silently lost). Seeded
`verify-reskin-*` calls/leads removed from `server/data/` afterward.

### Palette swap (2026-08-08) — "Amber Ledger," a second reference clip

A separate uploaded reference (a short promo clip for an unrelated crypto
dashboard product) prompted a follow-up color pass: near-black teal-tinted
surfaces, a deep teal ambient background glow, and one warm amber/orange
accent standing in for every active/brand moment (nav, buttons, focus
rings, the brand mark) in place of the purple/cyan pair from the reskin
above. Sampled directly from the clip's frames (`ffmpeg` frame extraction
+ pixel averaging, not guessed) before choosing hex values.

**What did *not* go monochrome, on purpose.** The reference clip is a
single-metric dashboard — it never had to solve telling two things apart
in the same view. CallEvals does, in a few places, so three color systems
were deliberately kept independent of the new brand accent rather than
flattened to it:
- The dual-line Weekly Trend chart (`TrendLineChart.js`) — score stayed
  amber (`#f0923e`), but conversion became a muted teal-grey dashed line
  (`#7fa39d`) instead of a second bright hue, so the two series stay
  readable without reintroducing a competing brand color.
- The objection-tag category palette (`.tag-price`, `.tag-competitor`,
  `.tag-authority`, etc. in `App.css`) — untouched; nine categories need
  more than one hue to stay scannable at a glance.
- The existing green/amber/rose sentiment-and-status semantic scale
  (`--accent-green`/`--accent-amber`/`--accent-rose`) — untouched. This
  creates one real naming wrinkle worth knowing about: `--accent-amber`
  (`#fbbf24`, semantic "moderate/warning," e.g. Medium buying-intent
  chips) and the new brand accent (`#f0923e`, carried by the
  `--accent-purple*` variable names for historical reasons — renaming
  ~200 call sites across the stylesheet wasn't worth it for a values-only
  swap) are both in the amber family but visually distinct — golden-yellow
  vs. deep orange — confirmed side by side in the live screenshots below,
  not just asserted.

A handful of "neutral middle state" chips (`.sentiment-neutral`,
`.intent-low`, `.compliance-not_applicable`, `.addressed-no`,
`.tag-contract`) previously rode the old purple-family wash as a generic
neutral tint, which worked because purple was the base brand hue. With
amber now meaning "active/brand," reusing it for these would have sent
the wrong signal (amber usually reads as caution, not neutral-default), so
these five were pointed at a true neutral teal-grey instead of following
the brand-accent swap.

**Verification.** 158 backend tests still passing (palette-only change).
Three leads and three calls seeded directly via `tests/factories.py`
(`make_call`/`make_lead`) across two weeks, so the Weekly Trend chart,
KPI sparklines, and Kanban board could be checked with real multi-point
data rather than empty states — confirmed the score/conversion lines
stay visually distinct, the semantic amber/brand amber pair reads as two
different colors side by side, and the categorical objection-tag and
sentiment/intent badges were untouched by the swap. Seed data removed
from `server/data/` afterward.

### Animated score hero (2026-08-08) — React Bits "Strands" on the call screen

An ambient WebGL background (React Bits' `Strands` component, built on
`ogl`) behind the overall score number on the CallDetail page — the
single most important number on that screen. `Strands.js`/`Strands.css`
are the component as published, unmodified; the integration work was
deciding where it belongs and tuning it to fit.

**Placement, not a redesign.** Rather than a full-page background (risky
on a page this data-dense — six-plus panels of transcript, objections,
sentiment, coaching, compliance below it), the animation is scoped to a
new `.score-hero` modifier on the existing `.overall-score` wrapper in
`ScoreBreakdownPanel.js` only — `AgentScoreBreakdownPanel.js` (used on the
Agent/Team/Org pages) shares the base `.overall-score`/`.overall-score-value`
classes but was deliberately left untouched, confirmed via a Playwright
canvas count on the Organization page (0). Colors pulled from the Amber
Ledger token set (`#f0923e` amber, `#2dd4bf` teal, `#d9752c` deep orange)
so it reads as part of the theme rather than a bolted-on effect; `speed`,
`intensity`, `opacity`, and `scale` were all turned down from the
component's own defaults (0.35/0.45/0.55/1.9 vs. defaults of
0.5/0.6/1/1.5) so it stays ambient rather than competing with the score
digits for attention.

**Legibility over the moving background** was the real design problem,
not the animation itself: a `radial-gradient` scrim
(`.score-hero-backdrop::after`) fades the canvas back to the panel's own
background color under the text, and the score digits get a
`text-shadow` and `z-index` above the canvas, so "100/100" stays readable
regardless of what the strands are doing underneath at any given frame —
checked by diffing two screenshots taken 1.5s apart (confirmed the canvas
is genuinely animating, not a static frame) with the score still legible
in both.

**Respects `prefers-reduced-motion`.** A `usePrefersReducedMotion` hook
skips mounting the `<Strands>` component (and therefore the WebGL
context) entirely when the OS-level setting is on — not just a CSS
animation-pause, so reduced-motion users also don't pay the GPU/battery
cost. Verified with Playwright's `reducedMotion: 'reduce'` context option:
0 canvas elements render, and the score hero falls back to a plain static
panel.

**Verification.** `npm install ogl` (new runtime dependency, not a
devDependency). Live Playwright pass: rendered correctly under this
sandbox's software-WebGL fallback (Chromium logs an expected
SwiftShader-fallback warning, no errors), confirmed genuinely animating
frame-to-frame, confirmed absent under reduced-motion, confirmed the
Organization/Agent Performance score panels are unaffected. 158 backend
tests still passing (frontend-only change).

### Strands on the Calls tab's empty state (2026-08-09)

Extended the same `Strands` background to the right-hand panel shown
before a call is selected ("Select a call to review it.") — previously a
single line of muted `<p className="hint">` text with no visual weight,
sitting in a mostly-empty flex row next to the upload/call-list sidebar.

**`usePrefersReducedMotion` extracted to `src/hooks/`.** It was private to
`ScoreBreakdownPanel.js`; a second consumer (`CallEmptyState.js`) made
duplicating it the wrong call, so it's now a shared hook both components
import.

**Sizing took real tuning, not a guess.** The score-hero band is a wide,
short strip (~700×110px) — good for one flat wave across the width. The
empty-state panel is a much taller, closer-to-square area (~990×540px in
the reference viewport), and reusing the score-hero's tuning made the
strands collapse into one thin horizontal streak, leaving most of the
panel's height empty. Fixed by tuning `amplitude` way up (0.7 → 3.2) and
`scale` down (1.9 → 1.3) specifically for this container's aspect ratio,
plus `taper` down (2.6 → 1.4) so the weave doesn't pinch to a point before
reaching the panel edges — verified by screenshotting three different
points in the animation cycle and confirming the fill looks intentional
(not a lucky freeze-frame) in all three, not just the first one checked.
`min-height: min(560px, calc(100vh - 210px))` keeps the panel substantial
on a normal screen without forcing a scroll on a short one.

Same legibility approach as the score hero: a radial-gradient scrim
(`.call-empty-backdrop::after`) centered behind the text, `text-shadow`
on both lines, and the same `usePrefersReducedMotion` guard (0 canvas
elements under `reducedMotion: 'reduce'`, verified directly).

**Verification.** Live Playwright pass at 1600×950: confirmed the panel
fills the available width/height without overflow, confirmed the text
stays legible across three animation frames ~2s apart (not just a static
check), confirmed reduced-motion still renders 0 canvases, confirmed the
populated CallDetail score-hero still renders correctly after the shared-
hook refactor (no regressions from moving `usePrefersReducedMotion` out
of `ScoreBreakdownPanel.js`). 163 backend tests still passing
(frontend-only change).

### Finishing pass (2026-08-09) — self-hosted fonts, focus states, motion

**The fonts were never actually loading.** `App.css`'s design tokens have
named `"Space Grotesk"`/`"JetBrains Mono"` as the first-choice fonts since
the original reskin, but the Google Fonts `@import` that would have
fetched them was deliberately removed earlier (see "Animated score hero"
section above — it caused a real `ERR_CONNECTION_RESET` and a 30s
`page.goto` hang on this network). Every screenshot since then was
actually rendering in the `system-ui` fallback, not the intended
typeface. Fixed properly this time instead of re-adding the same risk:
`@fontsource/space-grotesk` and `@fontsource/jetbrains-mono` (weights
400/500/600/700 and 400/500/600) are now real npm dependencies, imported
once in `index.js` and bundled by webpack — the font files ship with the
build and are served from the app's own origin, so there's no runtime
fetch to `fonts.googleapis.com` to fail. Verified with
`document.fonts.check()` (not just reading the CSS `font-family`
property, which reports the declared value regardless of whether it
loaded) — both families report `loaded`, and a live screenshot shows the
visibly different letterforms.

**Keyboard focus was inconsistent.** Only 3 components had explicit
`:focus` styling; everything else fell back to the browser's default blue
outline, which reads as visually broken against this dark theme. A single
`:focus-visible` rule now covers every button/select/input/textarea/link
with a consistent amber ring — `:focus-visible` specifically, so it only
appears for keyboard navigation, not every mouse click. Verified by
tabbing through the Calls page and screenshotting the ring on the agent
`<select>`.

**Reduced-motion had a real gap.** The Strands background already skipped
mounting its WebGL canvas under `prefers-reduced-motion: reduce` (JS-side,
per-component). Everything else on the page — modal entrances, the model-
status sweep, the pulsing status dot — was still a plain CSS `animation`
with no reduced-motion handling at all. A global `@media
(prefers-reduced-motion: reduce)` rule now collapses every
animation/transition duration to effectively zero for users with that OS
setting, closing the gap for every animated element at once instead of
patching them one at a time.

**Motion added:**
- Tab switches and call selection now fade in (`.app-content > *` /
  `.main > *`, both keyed off a genuine React mount — tab switches render
  a different component type at that tree position and calls now carry
  `key={selectedCall.id}` — so the CSS mount-triggered `fade-in` animation
  actually re-fires each time instead of only playing once on first load).
- Buttons get a tactile `scale(0.97)` on `:active` press, skipped
  automatically for reduced-motion users by the global media query above.

**What this pass deliberately didn't touch:** per-panel staggered
entrance animations, hover affordances on non-interactive elements (KPI
tiles, leaderboard rows) — adding a hover state to something that isn't
clickable is a false affordance, not polish — and any layout restructuring.
The four tabs, CallDetail, and the Kanban board were already screenshot-
verified panel-by-panel across the last several passes; this round is the
typography/motion/accessibility layer on top of that, not a redesign.

**Verification.** Live Playwright pass across Calls (empty + populated),
Agent Performance, and Leads (board + modal open): confirmed fonts load
before/after the fix via `document.fonts.check()`, confirmed the focus
ring renders on keyboard tab, confirmed 0 console errors, confirmed the
Kanban lead-detail modal's entrance animation and the new fonts render
correctly together. 163 backend tests still passing (frontend-only
change).

## What changed from the original scaffold

The uploaded `call_center_analyser` project was two competing API spikes
(Google Cloud STT v2/Chirp, and Gemini multimodal transcription), a default
Create React App page, hardcoded blank API keys, `GOOGLE_APPLICATION_CREDENTIALS=""`
(which breaks credential resolution rather than just being empty), and
`CORS allow_origins=["*"]` combined with `allow_credentials=True`. None of
F2–F4 (summary, next steps, objections) existed, and there was no way to
measure extraction precision — the PRD's own riskiest assumption (A1).

This build commits to one ASR path behind a swappable interface, adds the
extraction step, adds the mock-call/ground-truth harness Phase 0 is supposed to
produce, fixes the config/security issues, and gives the frontend an actual
review UI instead of a raw JSON dump.

## Layout

```
server/
  app/
    asr/            ASRProvider interface + faster-whisper (default) and
                     Deepgram (opt-in) implementations, selected via factory.py
    audio/           dual-channel split
    extraction/      ExtractionProvider interface + Gemini (default) and
                     Groq (opt-in) implementations, selected via factory.py;
                     shared prompt/wire-schema/mapping in common.py
    routers/         FastAPI routes
    insights.py      rule-based behavior readouts (talk time, monologues, questions, interruptions)
    compliance.py    rule-based script-adherence checks (analytics doc section 14)
    performance_metrics.py shared, population-agnostic rollup engine behind agent/team/org performance
    agent_performance.py  filters to one agent, calls performance_metrics.py
    team_performance.py    filters to one team, calls performance_metrics.py
    org_performance.py     no filtering (whole org), calls performance_metrics.py
    roster_storage.py      filesystem CRUD for Team/Agent
    lead_storage.py        filesystem CRUD for Lead, incl. stage_history append-on-change
    pipeline.py      orchestrates ASR -> extraction -> insights/compliance/overall_score
    storage.py       filesystem persistence for calls
    schemas.py       F1-F4 + score/sentiment/intent/coaching/compliance + roster/lead + agent-performance data model
  eval/
    mock_calls/      6 scripted calls + hand-labeled ground truth (PRD section 9)
    run_precision_eval.py
  scripts/
    seed_demo_roster.py     synthetic demo roster (10 teams x 10 agents)
    migrate_legacy_calls.py backfills agent_id/lead_id onto pre-Phase-A call records
  tests/
    conftest.py      redirects filesystem storage at a temp dir for the whole test session
frontend/
  src/
    components/      UploadPanel, CallList, CallDetail, TranscriptView,
                      NextStepsPanel, ObjectionTags, CallInsightsPanel,
                      ScoreBreakdownPanel, SentimentPanel, BuyingIntentPanel,
                      CoachingPanel, ComplianceChecklist, LeadPanel,
                      AgentPerformancePage + AgentOverviewPanel,
                      AgentScoreBreakdownPanel, AgentBehaviorPanel,
                      AgentFunnelPanel, AgentPipelineInsightsPanel,
                      AgentSentimentIntentPanel,
                      AgentQualityTrendPanel, AgentCoachingPanel,
                      OrganizationPage (team+org rollups, drill-down),
                      LeaderboardPanel,
                      LeadPipelinePage (Kanban board), LeadCard,
                      LeadDetailModal (C6: history + reassign)
    api/client.js
docs/
  PRD.md
  ROADMAP.md
```

## Setup

### Backend

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# put a free key from https://ai.google.dev into .env as GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Requires `ffmpeg` on PATH (faster-whisper decodes audio through it). On
Debian/Ubuntu: `apt-get install ffmpeg`.

### Frontend

```bash
cd frontend
npm install
npm start
```

Runs on `localhost:3000`, talks to the backend on `localhost:8000` (override with
`REACT_APP_API_BASE`).

### Phase 0 precision eval

The actual Phase 0 deliverable — run extraction against the scripted mock calls
and measure precision against hand-labeled ground truth:

```bash
cd server && source .venv/bin/activate
python -m eval.run_precision_eval
```

Deliberately transcript-only, not audio-in: this measures extraction precision
(A1), which is a property of the LLM step, decoupled from ASR word-error-rate —
conflating the two would muddy which risk actually failed. F1 (transcription
accuracy) needs its own check against real call audio once real audio exists to
check it against.

**Real run, against live `gemini-2.5-flash` (6 mock calls):**

| | precision | recall |
|---|---|---|
| next steps | 100% | 100% |
| objections | 75% | 100% |

Meets the PRD's 85% next-step launch gate (section 6) — on this mock set; 6
calls is too small a sample to treat these percentages as more than
directional, and this still needs re-running against real brokerage calls
before anyone trusts it in production.

This wasn't the first run. The first pass came back at 75%/50% (both at 100%
recall) — the model never missed a real commitment or objection, but it kept
splitting one real conversational moment into two extracted items (e.g. one
ground-truth next step, "draft the offer letter and send it tomorrow," came
back as two separate items — the rep's side and the customer's acknowledgment
of the same exchange). `EXTRACTION_PROMPT` (now in `app/extraction/common.py`,
shared with the Groq path — see "Groq extraction" below) explicitly
instructs the model to merge near-duplicate next
steps/objections about the same underlying commitment or concern into one
entry before finalizing its answer. Re-ran against the same 6 calls and same
model afterward: next-step precision went 75% → 100%, objections 50% → 75%,
recall held at 100% throughout. The one remaining objection miss ("I'm not
really looking to move fast on this right now" tagged as a timing objection)
is the same genuinely-debatable ground-truth call flagged in the first pass,
not a new model error.

### Backend tests

```bash
cd server && source .venv/bin/activate
python -m pytest tests/
```

These use fake ASR/extraction providers and synthetic in-memory WAV files, so
they run without network access, an API key, or a downloaded Whisper model.

## Known limitations / not yet verified

**The original dev sandbox this was built in blocks both `huggingface.co`
(faster-whisper's model download) and `api.deepgram.com` at the
network-policy level** — a real upload fails at the ASR step there no matter
which provider is configured, confirmed by actually trying both. Everything
below happened outside that sandbox, on a real Windows machine, end to end
through the actual app (not raw curl):

- **faster-whisper — confirmed working end to end.** First real run failed
  immediately with `Error opening '...': System error.` —
  `_transcribe_track` wrote audio via `tempfile.NamedTemporaryFile`, which
  keeps its own handle open on the file; `soundfile` opening that same path a
  second time to write to it works on Linux/Mac but Windows locks the file
  against a second opener. Fixed by writing to a plain path inside a
  `TemporaryDirectory` instead. Re-tested after the fix: real transcription,
  real text, matching the call's actual content (with the accuracy tradeoffs
  you'd expect from the `base` model — a few misheard words, no punctuation
  polish). Mono only so far; dual-channel through faster-whisper is
  implemented and unit-tested but not yet confirmed against a real
  dual-channel file.
- **Deepgram — confirmed working end to end, including diarization, after
  fixing a real heuristic bug.** Response shape confirmed live and matches
  what `deepgram_provider.py` parses. Surfaced a real-world channel-separation
  failure (a "stereo" file with both speakers mixed onto one channel, the
  other silent) — fixed with a diarization fallback. That fallback's first
  version then turned out to have the rep/customer roles backwards: it
  assumed whoever talks first is the rep, but in a real phone call whoever
  *answers* talks first, before the caller says anything — on an outbound
  call that's almost always the customer. Fixed by switching to "whoever
  talks the most overall" as the signal instead, and confirmed live: the rep
  is now labeled correctly. Not yet confirmed: a file where
  `multichannel=true` genuinely produces two populated channels (real channel
  separation, not the diarization fallback).
- **Gemini extraction is verified live**, not simulated, and iterated on
  live. Two real bugs surfaced only once a real API key was used, not before:
  `google-genai==0.6.0` (originally pinned) builds a `$ref`/`$defs`-based JSON
  schema for nested Pydantic models that Gemini's structured-output API
  rejects outright — every extraction call failed with a
  `pydantic.ValidationError` before hitting the network. Upgraded to
  `google-genai==2.17.0`, which resolves nested models inline instead — and
  that upgrade itself required bumping `pydantic` from `2.10.5` to `2.13.4`
  and `pydantic-settings` from `2.7.1` to `2.15.0`, since `google-genai>=2.x`
  needs `pydantic>=2.12.5`. `test_wire_schema_is_gemini_compatible` guards
  the schema-compatibility half of this without needing network access.
  The precision numbers above are from two real runs against
  `gemini-2.5-flash`, not one — the second after a prompt fix for
  over-segmentation, with the improvement measured, not assumed.
- **The score/sentiment/buying-intent/coaching/10-category-objection
  expansion (see "Analytics expansion" above) is smoke-tested live, not
  precision-measured.** The Gemini free tier's 20-requests/day quota was
  exhausted by prior runs in this session before the full 6-call precision
  eval could be re-run against the new prompt. Re-run
  `python -m eval.run_precision_eval` once the quota resets to get real
  numbers on the wider objection taxonomy before trusting it at the
  original 3-category precision bar.
- **Agent Performance is unit-tested and browser-verified against seeded
  data, not against a real multi-call pipeline run.** `app/agent_performance.py`'s
  math is directly unit-tested (no API key needed), and the dashboard was
  Playwright-driven against 18 realistic `CallRecord`s seeded straight into
  storage — but running 12+ real calls per agent through actual ASR +
  Gemini extraction to populate it end to end wasn't done, since the free
  tier's daily quota (already exhausted this session) can't support that
  volume. The aggregation logic itself doesn't care where the per-call data
  came from, so this is a volume/budget gap, not a correctness one — worth
  re-confirming against a real multi-call run before trusting the numbers
  in front of an actual manager.
- **Team & Organization rollups are unit-tested and browser-verified
  against a small, real-shaped dataset, not a real 100-agent volume.** The
  aggregation math (`app/performance_metrics.py` and its team/org callers)
  is directly unit-tested and is the same, already-verified engine the
  Agent layer used — it doesn't care how many agents or calls it's handed.
  The live pass used two synthetic calls across two teams against the real
  seeded 10-team/100-agent roster, which is enough to confirm the
  drill-down UI and the pooling/benchmark/leaderboard logic are correct,
  but not enough to say anything about dashboard load time at real call
  volume — that's Phase D's (storage/scale) job, not this pass's.
- **The new C2/C3/C4/C6 breakdowns are only as good as what a manager
  actually records, and every reason/source field is skippable by
  design.** `LostReasonAgg`/`SourceAgg` are computed over whatever subset
  of leads happen to have a reason or source recorded — a team that never
  fills in lost reasons will show an empty "Lost reasons" panel forever,
  correctly (it's not a bug, it's the panel being honest about missing
  data), but it also means these breakdowns can quietly stay useless in
  practice if no one is disciplined about filling in the modals. No UI
  nudge or required-field enforcement exists to prevent that.
- **No auth at all, and Phase C made that gap sharper, not just
  unchanged.** The new `POST /api/leads/{id}/reassign` and
  `PATCH /api/leads/{id}` endpoints mean any caller can now reassign any
  lead to any agent or rewrite its name/phone/source with zero scoping —
  previously the closest thing was creating a lead in the first place.
  This is explicitly Phase E's job (access control), not fixed here; it's
  a real reason to prioritize E sooner rather than later now that Phase C
  is fully built. No multi-tenant storage, no CRM integration beyond the
  manual lead-stage tagging described in "Roster & leads" above — all
  explicitly Phase 1+ per the PRD roadmap (section 9). No
  dedup-by-phone-number on Lead creation either — see that section for
  the gap.
