#!/usr/bin/env python3
"""
Prepares standardized audio files for ASR benchmarking using the live WiseAI TTS service.
Records actual audio metadata (duration, sample rate, channels, size).
"""
import os
import sys
import wave
import json
import urllib.request
import urllib.parse

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data", "audio")
WORKLOADS_FILE = os.path.join(BASE_DIR, "data", "text", "workloads.json")

os.makedirs(DATA_DIR, exist_ok=True)

with open(WORKLOADS_FILE, "r") as f:
    workloads = json.load(f)

tts_workloads = workloads["tts"]
audio_manifest = {}

for size, item in tts_workloads.items():
    out_file = os.path.join(DATA_DIR, f"audio_{size}.wav")
    print(f"Generating {size} audio ({item['char_count']} chars)...")
    
    data = urllib.parse.urlencode({
        "text": item["text"],
        "language": item["language"],
        "model": item["model"],
        "reference_audio_id": item["speaker"],
        "output_type": "audio"
    }).encode("utf-8")
    
    req = urllib.request.Request("http://localhost:8071/generate_from_text", data=data)
    with urllib.request.urlopen(req) as resp:
        audio_bytes = resp.read()
        
    with open(out_file, "wb") as f:
        f.write(audio_bytes)
        
    # Analyze wave file
    with wave.open(out_file, "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        duration_sec = nframes / float(framerate)
        
    print(f"  -> Saved {out_file}: {duration_sec:.2f}s, {framerate}Hz, {channels}ch, {len(audio_bytes)} bytes")
    audio_manifest[size] = {
        "id": f"asr_{size}",
        "file": out_file,
        "duration_seconds": round(duration_sec, 3),
        "sample_rate": framerate,
        "channels": channels,
        "bytes": len(audio_bytes),
        "source_text": item["text"],
        "language": "nepali"
    }

manifest_path = os.path.join(DATA_DIR, "audio_manifest.json")
with open(manifest_path, "w") as f:
    json.dump(audio_manifest, f, indent=2)

print(f"Audio manifest written to {manifest_path}")
