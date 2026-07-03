"""Minimal self-hosted Kokoro-82M TTS server.

Endpoints:
    GET  /health          -> {"status": "ok"}
    POST /tts             -> WAV audio bytes (audio/wav)

The POST /tts response carries timing headers so a benchmark can compute the
real-time factor without decoding the audio:
    X-Gen-Seconds    wall-clock time spent synthesizing
    X-Audio-Seconds  duration of the produced audio
    X-Sample-Rate    audio sample rate (Hz)
"""
import io
import os
import time

import soundfile as sf
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from kokoro_onnx import Kokoro

MODEL_DIR = os.environ.get("KOKORO_MODEL_DIR", "./models")
MODEL_FILE = os.environ.get("KOKORO_MODEL_FILE", "kokoro-v1.0.fp16.onnx")
VOICES_FILE = os.environ.get("KOKORO_VOICES_FILE", "voices-v1.0.bin")
DEFAULT_VOICE = os.environ.get("KOKORO_VOICE", "af_heart")
DEFAULT_SPEED = float(os.environ.get("KOKORO_SPEED", "1.0"))
DEFAULT_LANG = os.environ.get("KOKORO_LANG", "en-us")

app = FastAPI(title="Kokoro TTS")

# Load the model once at startup (a few seconds); reused for every request.
kokoro = Kokoro(
    os.path.join(MODEL_DIR, MODEL_FILE),
    os.path.join(MODEL_DIR, VOICES_FILE),
)


class TTSRequest(BaseModel):
    text: str
    voice: str | None = None
    speed: float | None = None
    lang: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tts")
def tts(req: TTSRequest):
    text = (req.text or "").strip()
    if not text:
        return JSONResponse(status_code=400, content={"error": "text is empty"})

    voice = req.voice or DEFAULT_VOICE
    speed = req.speed or DEFAULT_SPEED
    lang = req.lang or DEFAULT_LANG

    start = time.perf_counter()
    samples, sample_rate = kokoro.create(text, voice=voice, speed=speed, lang=lang)
    gen_seconds = time.perf_counter() - start

    audio_seconds = len(samples) / float(sample_rate)

    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV", subtype="PCM_16")

    return Response(
        content=buf.getvalue(),
        media_type="audio/wav",
        headers={
            "X-Gen-Seconds": f"{gen_seconds:.3f}",
            "X-Audio-Seconds": f"{audio_seconds:.3f}",
            "X-Sample-Rate": str(sample_rate),
        },
    )
