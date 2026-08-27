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
split, perfect separation, no ML — and falls back to labeling everything
`unknown` for mono audio rather than faking diarization. Real diarization for
genuinely mono calls is an explicit Phase 1 cut, not a silent gap (PRD section 5).

**Real-world wrinkle found in testing**: a file can be a 2-channel container
without the two speakers actually landing on separate channels — a recorder
that mixes both parties onto one track and leaves the other silent produces
exactly this. `multichannel=true` can't split audio that was never separated
in the source, so Deepgram returns real content on only one channel index.
`deepgram_provider.py` detects this (fewer than 2 channels carry any
transcript) and falls back to Deepgram's diarization (`speaker` field)
specifically for that failure case — first diarized speaker to talk is
labeled the rep, everyone else is labeled the customer. This is a heuristic,
not a guarantee (wrong if the customer calls in first, or if hold
music/an IVR segment gets diarized as its own "speaker"), and diarization
confidence runs noticeably lower than channel-based separation in practice.
Genuinely mono files (dual_channel=False) are unaffected by this — they still
stay labeled `unknown`, per the Phase 1 scope cut above.

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
    routers/         FastAPI routes (calls, agents, leads, org, settings)
    pipeline.py      orchestrates ASR -> extraction -> analysis
    analysis.py      rule-based conversation-shape + behavior-flag computation,
                     derived from the transcript/extraction — no LLM call
    rollups.py       agent/org/lead aggregate views over stored calls
    storage.py       filesystem persistence (calls, agents, leads, settings)
    schemas.py       F1-F4 data model + Agent/Lead/RubricSettings
  eval/
    mock_calls/      6 scripted calls + hand-labeled ground truth (PRD section 9)
    run_precision_eval.py
  tests/
frontend/
  src/
    screens/         Calls, CallHistory, Agents, Org, Leads, Rubric
    components/      Sidebar, TopHeader, AudioPlayer, TranscriptView,
                      NextStepsPanel, ObjectionsList, CoachingPanel,
                      ConversationShapePanel, LeadCard, ScoreCard, modals
    api/client.js
docs/
  PRD.md
```

### What's beyond the original Phase 0 scope

The frontend redesign (see the mockup this repo's UI now follows) called for
screens the original Phase 0 backend didn't support — agent performance,
organization rollups, a lightweight lead/CRM view, and a rubric/flags settings
screen. Rather than build a second frontend next to a thin backend, these got
real (if minimal) backend support:

- **Agents & leads** are auto-created from the `agent_name` / `lead_phone` fields
  on upload — no separate onboarding flow, still filesystem-backed like calls.
- **Behavior flags** (`app/analysis.py`) are rule-based thresholds computed from
  the real transcript and extraction result — monologue length, discovery
  question count, a dated next step, a disclosure-phrase check, a discount-before-
  question check. Thresholds are editable on the Rubric & flags screen. This is
  deliberately not the composite score PRD section 5 cut — it's the "behavior-level
  flags instead" alternative the PRD itself proposed.
- **Conversation shape** (talk ratio, questions asked, longest rep turn, words/min)
  is computed purely from transcript timing/text. Sentiment is a small lexicon
  heuristic over the same text, surfaced as unscored context per the PRD's own
  caution about sentiment analysis (section 5) — never fed into a flag or score.
- **Composite call score** stays cut. The Rubric screen has a toggle for it (the
  mockup's own Phase-3 preview framing), but no scoring pipeline exists behind it;
  turning it on shows an explicit "not built" state instead of a fabricated number.
- **Org metrics** (coverage, extraction precision, manager engagement, behavior
  improvement rate) are computed from real stored data per the PRD section 6
  definitions — nothing sampled or seeded.

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

## Deploy: backend on Render, frontend on Vercel

Deploy the backend first — the frontend needs its URL before its first build,
and the backend needs the frontend's URL for CORS, so there's an unavoidable
two-step handshake either way. Order: **Render backend → note its URL →
Vercel frontend with that URL → back to Render to set CORS with the Vercel
URL.**

**Two things about the backend specifically that don't show up until deploy:**

- **Storage is ephemeral by default.** Calls, agents, leads, and settings are
  files on disk (`server/app/storage.py`, no database — see "Stack, and why"
  above), and Render wipes the default disk on every restart/redeploy. Without
  a persistent disk (Render's paid plans only — not available on Free), every
  redeploy silently erases all data. `render.yaml` provisions a 1 GB disk and
  sets `DATA_DIR` to its mount path; on Free, drop the `disk:` block and
  `DATA_DIR` override and accept that data doesn't survive a redeploy.
- **The default ASR path needs ffmpeg + a model download.** faster-whisper
  (`ASR_PROVIDER=faster_whisper`, the default) decodes audio through `ffmpeg`
  and pulls a Whisper model from Hugging Face on first use — fine in Docker
  (this repo's `server/Dockerfile` installs ffmpeg explicitly) but adds cold-
  start latency and memory pressure on a small instance. `ASR_PROVIDER=deepgram`
  avoids both — hosted, no local model, no ffmpeg — same tradeoff as the
  extraction-provider switch, just for transcription instead of extraction.

### Backend on Render (Web Service)

`render.yaml` in the repo root is a best-effort
[Blueprint](https://render.com/docs/blueprint-spec) for this — try
"New > Blueprint" in the Render dashboard pointed at this repo first. If that
doesn't parse cleanly, the steps below set up the same service by hand.

1. New Web Service → connect this repo.
2. Root Directory: `server`. Environment: **Docker** (Render should detect
   `server/Dockerfile` automatically; if it offers a native Python runtime
   instead, pick Docker explicitly — see the ffmpeg note above).
3. Health Check Path: `/api/health`.
4. Environment variables — see `server/.env.example` for the full list and
   what each does. At minimum: `EXTRACTION_PROVIDER` + its API key
   (`GEMINI_API_KEY` or `GROQ_API_KEY`), `ASR_PROVIDER` + its config
   (`WHISPER_*` or `DEEPGRAM_API_KEY`). Leave `CORS_ALLOW_ORIGINS` unset for
   now — the Vercel frontend doesn't exist yet.
5. For persistent storage: add a Disk (e.g. 1 GB, mounted at `/var/data`,
   requires a paid instance type) and set `DATA_DIR=/var/data`.
6. Deploy, then note the assigned URL (`https://<name>.onrender.com`) — the
   frontend needs it next.

### Frontend on Vercel

CRA is one of Vercel's zero-config framework presets — no `vercel.json`
needed, just point it at the `frontend` subdirectory.

1. New Project on Vercel → import this repo.
2. Root Directory: `frontend`. Vercel should auto-detect "Create React App"
   and fill in the build command (`npm run build` / `react-scripts build`)
   and output directory (`build`) itself — confirm rather than override
   unless something looks off.
3. Environment Variable `REACT_APP_API_BASE` = the Render backend URL from
   above. Create React App bakes `REACT_APP_*` vars in **at build time**, not
   runtime — set this before the first deploy, or trigger a redeploy after
   adding/changing it (Vercel's dashboard has a "Redeploy" action for
   exactly this; editing the env var alone doesn't touch an already-built
   deployment).
4. Deploy. Vercel's production URL is `https://<project-name>.vercel.app`
   unless you attach a custom domain — every PR/branch also gets its own
   preview URL, which won't be in the backend's CORS list unless you add it
   too (fine to ignore for now, or add multiple origins to the JSON array).
5. Back on Render: set the backend's `CORS_ALLOW_ORIGINS` to the Vercel URL
   as a JSON array string, e.g. `["https://your-project.vercel.app"]` — the
   brackets and quotes matter, this is parsed as JSON, not a comma list.
   Saving it triggers a backend redeploy automatically.

## Known limitations / not yet verified

- **Neither ASR path has completed a real transcription through this app.** The
  dev sandbox this was built in blocks both `huggingface.co`
  (faster-whisper's model download) and `api.deepgram.com` at the
  network-policy level, so a real upload fails at the ASR step no matter which
  provider is configured — confirmed by actually trying both, not assumed.
  Deepgram's real response shape *has* been checked against a live call
  (outside this sandbox) and matches what `deepgram_provider.py` parses
  exactly (`results.utterances[].{start,end,channel,transcript}`) — but that
  test call was mono, so the multichannel `channel: 0 → rep` / `channel: 1 →
  customer` mapping is still unexercised against a real payload. faster-whisper
  has no live confirmation at all yet. Do one real dual-channel upload
  somewhere without the network restriction before trusting F1 fully on
  either provider.
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
- No auth, no multi-tenant storage — explicitly Phase 1+ per the PRD roadmap
  (section 9). Leads are a lightweight in-app record (name/phone/unit/budget/
  stage), created from upload fields — not a CRM integration; there's no sync
  with an external CRM.
