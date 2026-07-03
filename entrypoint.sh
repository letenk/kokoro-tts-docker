#!/bin/bash
set -e

MODEL_DIR="${KOKORO_MODEL_DIR:-./models}"
MODEL_FILE="${KOKORO_MODEL_FILE:-kokoro-v1.0.fp16.onnx}"
VOICES_FILE="${KOKORO_VOICES_FILE:-voices-v1.0.bin}"
HOST="${KOKORO_HOST:-0.0.0.0}"
PORT="${KOKORO_PORT:-8180}"
THREADS="${KOKORO_THREADS:-4}"

# Cap the ONNX Runtime / OpenMP thread pool to the box's core count.
export OMP_NUM_THREADS="$THREADS"

# Model + voice files live in a single GitHub release. The voices file is shared
# across every model precision (f32 / fp16 / int8).
RELEASE_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"

mkdir -p "$MODEL_DIR"

download() {
    file="$1"
    path="$MODEL_DIR/$file"
    if [ ! -f "$path" ]; then
        echo "Model file $file not found, downloading..."
        curl -L --fail --progress-bar "$RELEASE_URL/$file" -o "$path"
        echo "Download complete: $path"
    else
        echo "Model file $file already exists, skipping download."
    fi
}

download "$MODEL_FILE"
download "$VOICES_FILE"

echo "Starting Kokoro TTS server..."
echo "  Model   : $MODEL_DIR/$MODEL_FILE"
echo "  Voices  : $MODEL_DIR/$VOICES_FILE"
echo "  Host    : $HOST"
echo "  Port    : $PORT"
echo "  Threads : $THREADS"

exec uvicorn app:app --host "$HOST" --port "$PORT"
