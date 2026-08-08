# CallEvals — Sahil, Phase 0

Sales call intelligence for GCC mid-market real estate brokerages: transcript in,
summary + next steps + objection tags out, plus a scored rubric, sentiment,
buying intent, coaching notes, and rule-based compliance checks (see
"Analytics expansion" below). Full product spec: [docs/PRD.md](docs/PRD.md).

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
    pipeline.py      orchestrates ASR -> extraction -> insights/compliance/overall_score
    storage.py       filesystem persistence
    schemas.py       F1-F4 + score/sentiment/intent/coaching/compliance data model
  eval/
    mock_calls/      6 scripted calls + hand-labeled ground truth (PRD section 9)
    run_precision_eval.py
  tests/
frontend/
  src/
    components/      UploadPanel, CallList, CallDetail, TranscriptView,
                      NextStepsPanel, ObjectionTags, CallInsightsPanel,
                      ScoreBreakdownPanel, SentimentPanel, BuyingIntentPanel,
                      CoachingPanel, ComplianceChecklist
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
- No auth, no multi-tenant storage, no CRM integration — all explicitly Phase 1+
  per the PRD roadmap (section 9).
