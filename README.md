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
  PRD's own per-minute cost assumption in section 7, real mono diarization via
  `diarize=true`. That diarization flag is deliberately not wired in, though —
  see `app/asr/deepgram_provider.py` — turning it on would silently undo the
  Phase 1 scope cut this build otherwise respects.
- **Extraction — Gemini Developer API free tier** (ai.google.dev). Structured
  JSON output (F2 summary, F3 next steps, F4 objections), no GCP billing account
  required, unlike Vertex AI or Cloud Speech.
- **Storage — filesystem**, no database. Matches the PRD's own scope discipline
  (section 8: no vector DB at MVP) — a handful of design partners don't need
  Postgres yet.

**Speaker separation** prefers dual-channel (stereo) recordings — trivial channel
split, perfect separation, no ML — and falls back to labeling everything
`unknown` for mono audio rather than faking diarization. Real diarization for
mono calls is an explicit Phase 1 cut, not a silent gap (PRD section 5).

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
| next steps | 75% | 100% |
| objections | 50% | 100% |

Below the PRD's 85% next-step launch gate (section 6) — do not treat this as
trustworthy yet. But recall was 100% on both: the model never missed a real
commitment or objection a manager would want flagged. Every precision miss was
the model splitting one real conversational moment into two extracted items —
e.g. one ground-truth next step ("draft the offer letter and send it
tomorrow") got extracted as two separate items (the rep's and the customer's
side of the same exchange) — not a hallucinated commitment that never
happened. One miss (a "not looking to move fast" line tagged as a timing
objection) is a genuinely debatable ground-truth call, not a clear model
error. That's a specific, fixable prompt issue — instruct the model to
consolidate related commitments/objections into one item — rather than a sign
extraction is unreliable in general. Re-run after any prompt change; 6 calls
is too small a sample to treat these percentages as more than directional.

### Backend tests

```bash
cd server && source .venv/bin/activate
python -m pytest tests/
```

These use fake ASR/extraction providers and synthetic in-memory WAV files, so
they run without network access, an API key, or a downloaded Whisper model.

## Known limitations / not yet verified

- **Neither ASR path has completed a real transcription in this repo.** The
  dev sandbox this was built in blocks both `huggingface.co`
  (faster-whisper's model download) and `api.deepgram.com` at the
  network-policy level, so a real upload fails at the ASR step no matter which
  provider is configured — confirmed by actually trying both, not assumed.
  `deepgram_provider.py`'s request/response parsing is covered by mocked
  tests, and `faster_whisper_provider.py`'s channel-split logic is covered
  against synthetic WAVs, but do one real upload somewhere without that
  restriction before trusting F1 (transcription) on either provider.
- **Gemini extraction is verified live**, not simulated — the precision
  numbers above are from an actual run against `gemini-2.5-flash`, as is the
  upload/status/error-surfacing mechanics check (a call with no reachable ASR
  provider correctly ends up `status: "failed"` with a clear error, not
  silently stuck). That live run is also what caught a real bug:
  `google-genai==0.6.0` (originally pinned) builds a `$ref`/`$defs`-based JSON
  schema for nested Pydantic models that Gemini's structured-output API
  rejects outright — every extraction call failed with a
  `pydantic.ValidationError` before hitting the network. Upgraded to
  `google-genai==2.17.0`, which resolves nested models inline instead.
  `tests/test_gemini_extractor_helpers.py::test_wire_schema_is_gemini_compatible`
  guards against regressing this without needing network access.
- No auth, no multi-tenant storage, no CRM integration — all explicitly Phase 1+
  per the PRD roadmap (section 9).
