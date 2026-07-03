# Kokoro TTS Server — Docker Setup

A self-hosted, **CPU-only** text-to-speech (TTS) HTTP server powered by
[**Kokoro-82M**](https://huggingface.co/hexgrad/Kokoro-82M) — a small (82M parameter),
high-quality, **Apache 2.0** open-weight model — served through
[`kokoro-onnx`](https://github.com/thewh1teagle/kokoro-onnx) + ONNX Runtime.

It exposes a tiny HTTP API (`/health`, `/tts`) and runs entirely on your own hardware, so no
audio or text ever leaves your server. It's light enough to run on modest machines (a mini PC,
an old laptop, even a Raspberry Pi) without a GPU.

## Credits & References

- Original model: **Kokoro** by hexgrad — <https://github.com/hexgrad/kokoro>
- Model weights & voices: <https://huggingface.co/hexgrad/Kokoro-82M>
- ONNX runtime wrapper used here: <https://github.com/thewh1teagle/kokoro-onnx>
- License: **Apache 2.0** (free for personal and commercial use)

## Features

- 🔊 Natural English speech, far better than free/legacy TTS engines
- 🖥️ **CPU-only** — no GPU/CUDA required (default CPU `onnxruntime`)
- 🔐 Fully self-hosted — text and audio stay on your machine
- ⚡ Real-time or faster on modest hardware
- 🐳 Single `docker compose up` — model auto-downloads on first run
- 🎚️ Configurable model precision (f32 / fp16 / int8), voice, speed, and threads

## File Structure

```
kokoro/
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── app.py            ← FastAPI server (health + tts)
├── bench.py          ← latency / RTF benchmark (stdlib only)
├── requirements.txt
├── models/           ← auto-created, stores .onnx + voices .bin (gitignored)
└── README.md
```

## Requirements

- Docker + Docker Compose
- ~1 GB free disk for the model (fp16) and a few hundred MB RAM at runtime
- Internet access on first run (to download the model)

## API

| Method | Path      | Body                                              | Response |
|--------|-----------|---------------------------------------------------|----------|
| GET    | `/health` | —                                                 | `{"status":"ok"}` |
| POST   | `/tts`    | `{"text": "...", "voice"?, "speed"?, "lang"?}`    | `audio/wav` bytes |

The `POST /tts` response includes timing headers so clients/benchmarks can compute the real-time
factor without decoding the audio: `X-Gen-Seconds`, `X-Audio-Seconds`, `X-Sample-Rate`.

---

## How to Run

Run these on the Docker host (server/PC where Docker is installed).

### 1. Get the project onto the host

Clone or copy this folder onto the machine that will run it:

```bash
git clone <your-repo-url> kokoro && cd kokoro
# or copy the folder over with scp/rsync
```

### 2. Build & start

```bash
docker compose up -d --build
```

On first run the model + voices are downloaded into `./models/` (persisted on the host, so not
re-downloaded on restart). Follow progress with:

```bash
docker compose logs -f
```

### 3. Health check

```bash
curl http://localhost:8180/health
# {"status":"ok"}
```

### 4. Smoke test (generate audio)

```bash
curl -X POST http://localhost:8180/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello, how was your day?"}' \
  --output out.wav
```

Play `out.wav` and judge how natural it sounds.

### 5. Benchmark + watch RAM (two terminals)

```bash
# terminal 1 — latency / RTF for short, medium, long text
python bench.py --runs 5

# terminal 2 — live memory usage
docker stats kokoro-server
```

### 6. Compare against the Decision Gate

| Metric   | Target                                                                 |
|----------|------------------------------------------------------------------------|
| Latency  | short/medium generated in **< ~2s**; ideally **RTF < 1** (faster than real-time) |
| RAM      | container steady **< ~1.5 GB** (leave headroom for anything else on the box) |
| Quality  | clearly natural / pleasant to listen to (subjective)                   |

If a target fails: switch to a lighter model precision (`fp16` → `int8`), lower `KOKORO_THREADS`,
or tighten `mem_limit`.

> **Note:** `bench.py` uses only the Python standard library, so it runs on the host without any
> `pip install`. The first (cold) request is slower due to model warm-up — read the **p50** column
> for steady-state performance.

---

## Configuration

Edit the `environment` section in `docker-compose.yml`:

| Variable            | Default                  | Notes |
|---------------------|--------------------------|-------|
| `KOKORO_MODEL_FILE` | `kokoro-v1.0.fp16.onnx`  | `kokoro-v1.0.onnx` (f32, 310MB) · `kokoro-v1.0.fp16.onnx` (169MB) · `kokoro-v1.0.int8.onnx` (88MB) |
| `KOKORO_VOICE`      | `af_heart`               | US: `af_*` / `am_*` · UK: `bf_*` / `bm_*` (26 voices in `voices-v1.0.bin`) |
| `KOKORO_LANG`       | `en-us`                  | `en-us`, `en-gb`, ... |
| `KOKORO_SPEED`      | `1.0`                    | 0.5–2.0 |
| `KOKORO_THREADS`    | `4`                      | match CPU core count (sets `OMP_NUM_THREADS`) |
| `KOKORO_PORT`       | `8180`                   | any free port |

### Model precision

- **fp16** (default) — best balance of quality, RAM, and speed on CPU.
- **int8** — smallest/lightest (88MB); use if RAM or latency is tight, at a slight quality cost.
- **f32** — full precision (310MB); highest quality, heaviest.

## Connecting from Another Container

By default this server runs on its own bridge network (`kokoro-tts-network`). To let another
container (e.g. your app or another model server) reach it by name, put both on the same network.

Option A — attach your other service to this network:

```yaml
networks:
  kokoro-network:
    external: true
    name: kokoro-tts-network
```

Option B — put this server on an existing shared network by editing the `networks:` block at the
bottom of `docker-compose.yml` to `external: true` with your network's name.

Then reach the server by container name:

```env
KOKORO_URL=http://kokoro-server:8180
```

## Troubleshooting

- **Model download 404** — the download URLs in `entrypoint.sh` point at the `thewh1teagle/kokoro-onnx`
  GitHub release `model-files-v1.0`. If a file moves, update the release tag/URL there.
- **`espeak-ng` errors** — `kokoro-onnx` uses `espeak-ng` for phoneme fallback; it's installed in the
  image. If you build a custom base image, keep the `espeak-ng` apt package.
- **High latency / OOM** — lower `KOKORO_THREADS`, switch `KOKORO_MODEL_FILE` to `int8`, or raise/lower
  `mem_limit` in `docker-compose.yml`.

## License

This project's configuration is provided as-is. The Kokoro model and its weights are licensed under
**Apache 2.0** by their respective authors — see the links under **Credits & References**.
