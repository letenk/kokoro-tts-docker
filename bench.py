#!/usr/bin/env python3
"""Benchmark the self-hosted Kokoro TTS server: latency (p50/p95) and real-time
factor (RTF) across short / medium / long text.

Uses only the Python standard library, so it runs anywhere (host or container)
without installing anything.

Usage:
    python bench.py [--url http://localhost:8179] [--runs 5]

Tip: run `docker stats kokoro-server whisper-server` in another terminal while
this runs to capture peak RAM of both services side by side.
"""
import argparse
import json
import statistics
import time
import urllib.request

SAMPLES = {
    "short": "Hello! Thanks for stopping by. Whenever you're ready, we can begin.",
    "medium": (
        "That's a really interesting point. Could you walk me through the specific "
        "steps you took, and how you decided which one to tackle first?"
    ),
    "long": (
        "Great answer — you covered a lot of ground there. Let me summarize what I heard so I "
        "can make sure I understood correctly. You started by identifying the main bottleneck in "
        "your deployment pipeline, then you proposed a caching layer to reduce repeated work, and "
        "finally you measured the impact before rolling it out to everyone. That's a solid, "
        "data-driven approach. Now, if you had to do it again with half the time available, what "
        "would you cut, and what would you absolutely keep? Take your time and think it through."
    ),
}


def synth(url, text):
    body = json.dumps({"text": text}).encode()
    req = urllib.request.Request(
        url + "/tts", data=body, headers={"Content-Type": "application/json"}
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req) as resp:
        resp.read()
        wall = time.perf_counter() - start
        gen = float(resp.headers.get("X-Gen-Seconds", "0"))
        audio = float(resp.headers.get("X-Audio-Seconds", "0"))
    return wall, gen, audio


def p95(values):
    s = sorted(values)
    return s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8179")
    ap.add_argument("--runs", type=int, default=5)
    args = ap.parse_args()

    print(f"Benchmarking {args.url}  ({args.runs} runs per length)\n")
    header = f"{'length':8}{'chars':>7}{'wall_p50':>10}{'wall_p95':>10}{'gen_p50':>9}{'audio_s':>9}{'RTF_p50':>9}"
    print(header)
    print("-" * len(header))

    for name, text in SAMPLES.items():
        walls, gens, audios = [], [], []
        for _ in range(args.runs):
            wall, gen, audio = synth(args.url, text)
            walls.append(wall)
            gens.append(gen)
            audios.append(audio)
        gen_p50 = statistics.median(gens)
        audio_s = statistics.median(audios)
        rtf = gen_p50 / audio_s if audio_s else 0.0
        print(
            f"{name:8}{len(text):>7}{statistics.median(walls):>10.3f}"
            f"{p95(walls):>10.3f}{gen_p50:>9.3f}{audio_s:>9.3f}{rtf:>9.3f}"
        )

    print("\nRTF < 1.0 = faster than real-time. The first (cold) request is usually")
    print("slower due to model warm-up; look at p50 for steady-state performance.")


if __name__ == "__main__":
    main()
