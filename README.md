# CallEvals — Sahil, Phase 0

Sales call intelligence for GCC mid-market real estate brokerages: transcript in,
summary + next steps + objection tags out. Full product spec: [docs/PRD.md](docs/PRD.md).

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
heuristic: the first diarized speaker to talk is labeled the rep, everyone
else the customer. Right when the rep opens the call (the norm for outbound
sales calls), wrong if the customer calls in first or if hold music / an IVR
segment gets diarized as its own "speaker." Diarization confidence also runs
noticeably lower than channel-based separation in practice — expect
occasional misattributed short turns ("okay", "yeah").

**On the faster-whisper path**, mono calls still come back `Speaker.UNKNOWN`
— Whisper itself has no diarization, so matching Deepgram's mono behavior
would mean a new dependency (e.g. `pyannote.audio`), more model weights, more
CPU/GPU cost, and likely a Hugging Face token for a gated model. Not done;
dual-channel audio through faster-whisper still gets real rep/customer labels
via the local channel split, same as always.

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
    pipeline.py      orchestrates ASR -> extraction
    storage.py       filesystem persistence
    schemas.py       F1-F4 data model
  eval/
    mock_calls/      6 scripted calls + hand-labeled ground truth (PRD section 9)
    run_precision_eval.py
  tests/
frontend/
  src/
    components/      UploadPanel, CallList, CallDetail, TranscriptView,
                      NextStepsPanel, ObjectionTags
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

- **Neither ASR path has completed a real transcription through this app from
  inside the original dev sandbox.** That sandbox blocks both
  `huggingface.co` (faster-whisper's model download) and `api.deepgram.com`
  at the network-policy level, so a real upload fails at the ASR step no
  matter which provider is configured there — confirmed by actually trying
  both, not assumed. Both providers have since been exercised for real
  outside that sandbox, on a real Windows machine, and both surfaced real
  bugs that only showed up under those conditions:
  - **Deepgram**: response shape confirmed live and matches what
    `deepgram_provider.py` parses (`results.utterances[].{start,end,channel,transcript}`).
    Also surfaced a real-world failure mode: a "stereo" recording where both
    speakers were mixed onto one channel and the other was silent, so
    `multichannel=true` couldn't actually separate them. Fixed with a
    diarization fallback for that specific case — see `deepgram_provider.py`.
    Not yet confirmed: a file where `multichannel=true` genuinely produces
    two populated channels.
  - **faster-whisper**: first real run on Windows failed immediately —
    `Error opening '...': System error.` — because `_transcribe_track` wrote
    the audio via `tempfile.NamedTemporaryFile`, which keeps its own handle
    open on the file. `soundfile` opening that same path a second time to
    write to it works on Linux/Mac (multiple handles to one path are fine
    there) but Windows locks the file against a second opener. Fixed by
    switching to a plain path inside a `TemporaryDirectory` instead. Not yet
    confirmed: a successful end-to-end transcription after that fix.
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
- No auth, no multi-tenant storage, no CRM integration — all explicitly Phase 1+
  per the PRD roadmap (section 9).
