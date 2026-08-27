# ffmpeg is a hard requirement of the default ASR path (faster-whisper decodes
# audio through it — see app/asr/faster_whisper_provider.py) and isn't reliably
# present on a generic Python buildpack, so this pins it explicitly rather than
# hoping the deploy platform provides it.
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# DATA_DIR defaults to ./data (see app/config.py), i.e. /app/data here — fine
# for ephemeral storage, but that means every restart/redeploy loses all calls,
# agents, leads, and settings unless DATA_DIR is overridden at runtime to a
# mounted persistent volume.
ENV PORT=8000
EXPOSE 8000

# Shell form (not exec array) so $PORT actually expands — the platform injects
# it at runtime and the app must bind to it, not the hardcoded default above.
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
