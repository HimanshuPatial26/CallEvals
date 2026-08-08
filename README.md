# CallEvals — Sahil, Phase 0

Sales call intelligence for GCC mid-market real estate brokerages: transcript in,
summary + next steps + objection tags out, plus a scored rubric, sentiment,
buying intent, coaching notes, and rule-based compliance checks per call (see
"Analytics expansion" below) — and, per agent per period, a cross-call
performance rollup with team benchmarking (see "Agent Performance" below).
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
- **Extraction — Gemini Developer API free tier** (ai.google.dev). Structured
  JSON output (F2 summary, F3 next steps, F4 objections), no GCP billing account
  required, unlike Vertex AI or Cloud Speech.
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

**Foundation:**

- **`CallRecord.agent_name`** — every call is now attributed to a rep at
  upload time (a required form field; existing/unlabeled records default to
  `"Unassigned"` rather than breaking). Nothing about "agent-level" analytics
  is possible without this, and it didn't exist until now — the app was
  purely per-call.
- **`CallRecord.outcome`** (`app/schemas.py`'s `CallOutcome`) — a manager-set
  funnel stage (untagged/qualified/demo booked/proposal sent/won/lost) plus
  deal size, set via `POST /api/calls/{id}/outcome` and a new Outcome control
  on the call review page. This is the *only* data source behind every
  CRM-shaped metric the doc asked for (conversion rate, qualified-lead rate,
  revenue, the quality-vs-outcome matrix) — there's no CRM/dialer
  integration (PRD section 8 defers that to Phase 2), so those numbers are
  either this manually-recorded fact or nothing. No fabricated CRM data
  anywhere in this build.

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
    extraction/      ExtractionProvider interface + Gemini implementation
    routers/         FastAPI routes
    insights.py      rule-based behavior readouts (talk time, monologues, questions, interruptions)
    compliance.py    rule-based script-adherence checks (analytics doc section 14)
    agent_performance.py  cross-call rollups per agent/period — pure aggregation, no LLM call
    pipeline.py      orchestrates ASR -> extraction -> insights/compliance/overall_score
    storage.py       filesystem persistence
    schemas.py       F1-F4 + score/sentiment/intent/coaching/compliance + agent-performance data model
  eval/
    mock_calls/      6 scripted calls + hand-labeled ground truth (PRD section 9)
    run_precision_eval.py
  tests/
frontend/
  src/
    components/      UploadPanel, CallList, CallDetail, TranscriptView,
                      NextStepsPanel, ObjectionTags, CallInsightsPanel,
                      ScoreBreakdownPanel, SentimentPanel, BuyingIntentPanel,
                      CoachingPanel, ComplianceChecklist, OutcomePanel,
                      AgentPerformancePage + AgentOverviewPanel,
                      AgentScoreBreakdownPanel, AgentBehaviorPanel,
                      AgentFunnelPanel, AgentSentimentIntentPanel,
                      AgentQualityTrendPanel, AgentCoachingPanel
    api/client.js
docs/
  PRD.md
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
of the same exchange). `EXTRACTION_PROMPT` in `gemini_extractor.py` now
explicitly instructs the model to merge near-duplicate next
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
- No auth, no multi-tenant storage, no CRM integration beyond the manual
  per-call outcome tag described above — all explicitly Phase 1+ per the PRD
  roadmap (section 9).
