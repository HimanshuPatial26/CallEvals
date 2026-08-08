# CallEvals — Sahil, Phase 0

Sales call intelligence for GCC mid-market real estate brokerages: transcript in,
summary + next steps + objection tags out. Full product spec: [docs/PRD.md](docs/PRD.md).

This repo is the Phase 0 build the PRD calls for (section 9) — prove that
extraction (F2–F4) is accurate enough to trust, against scripted mock calls,
before any customer is involved. It replaced an earlier scaffold that spiked on
two ASR/LLM providers but never attempted extraction; see "What changed" below.

## Stack, and why

Everything here runs on free tiers — no GCP billing account, no paid API:

- **ASR — `faster-whisper`, self-hosted.** Runs locally on CPU, no API key, no
  per-minute billing. This is also the engine the PRD's own architecture diagram
  names and the one it expects to self-host at scale (PRD section 7) — so Phase 0
  is already on the intended long-term path rather than a throwaway.
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
    asr/            ASRProvider interface + faster-whisper implementation
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

### Backend tests

```bash
cd server && source .venv/bin/activate
python -m pytest tests/
```

These use fake ASR/extraction providers and synthetic in-memory WAV files, so
they run without network access, an API key, or a downloaded Whisper model.

## Known limitations / not yet verified

- The full audio pipeline (upload → whisper → extraction) has not been run
  end-to-end against real recorded audio in this repo — the dev sandbox this was
  built in doesn't have a working `ffmpeg` install or a Gemini API key. The unit
  tests cover the pipeline logic, channel-splitting on synthetic WAVs, and the
  scoring harness's matching logic in isolation; run the eval script yourself
  with a real key to get the actual precision number.
- No auth, no multi-tenant storage, no CRM integration — all explicitly Phase 1+
  per the PRD roadmap (section 9).
