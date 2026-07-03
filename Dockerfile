# ─────────────────────────────────────────
# Kokoro-82M TTS server (CPU-only, self-hosted)
# ─────────────────────────────────────────
FROM python:3.11-slim

# System deps:
#   espeak-ng   → grapheme→phoneme fallback used by kokoro-onnx
#   libsndfile1 → required by python-soundfile to encode WAV
#   curl        → model download (entrypoint) + healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng \
    libsndfile1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App + entrypoint
COPY app.py ./app.py
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

EXPOSE 8180

ENTRYPOINT ["./entrypoint.sh"]
