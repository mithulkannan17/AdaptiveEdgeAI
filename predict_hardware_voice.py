"""
AuraForest — 5-Second Hardware Voice & Acoustic Event Predictor
==============================================================

Loads and predicts raw 5-second PCM16 audio recorded by the ESP32-S3 hardware
(e.g., test_audio.pcm, 16000 Hz, signed 16-bit little-endian mono).

Usage:
    python predict_hardware_voice.py
    python predict_hardware_voice.py test_audio.pcm
    python predict_hardware_voice.py path/to/recording.pcm
"""

from __future__ import annotations

import sys
import os
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.audio_service import AudioInferenceService


def predict_audio_file(file_path: str | Path) -> None:
    path = Path(file_path)
    if not path.is_file():
        print(f"[!] Error: Audio file '{path}' not found.")
        print("    Ensure the ESP32 has saved test_audio.pcm or specify a valid file path.")
        sys.exit(1)

    audio_bytes = path.read_bytes()
    byte_count = len(audio_bytes)
    duration_s = byte_count / (16000 * 2) if path.suffix.lower() == ".pcm" else "Variable"

    print("=" * 65)
    print("   🌲 AURAFOREST — HARDWARE VOICE & ACOUSTIC PREDICTOR")
    print("=" * 65)
    print(f"[*] Audio File : {path.name} ({path.resolve()})")
    print(f"[*] Payload Size: {byte_count:,} bytes (~{duration_s:.1f}s at 16kHz PCM16)" if isinstance(duration_s, float) else f"[*] Payload Size: {byte_count:,} bytes")
    print("[*] Loading Neural Acoustic Engine & Pre-warm Kernels...")

    service = AudioInferenceService()

    print("[*] Running MobileNetV3-Small Inference & CADIE Context Fusion...")
    t0 = time.time()
    result = service.infer_pcm16(
        audio_bytes=audio_bytes,
        sample_rate=16000,
        top_k=5,
    )
    inference_time = (time.time() - t0) * 1000

    prediction = result.get("prediction") or {}
    label = prediction.get("label", "Unknown")
    confidence = float(prediction.get("confidence", 0.0))
    top_k = prediction.get("top_k", [])

    cadie = result.get("decision") or (result.get("edge_runtime") or {}).get("decision") or {}
    risk_level = str(cadie.get("risk_level", "LOW")).upper()
    action = cadie.get("recommended_action", "MONITOR")
    score = float(cadie.get("decision_score", 0.0))
    factors = cadie.get("contributing_factors", [])

    print("\n" + "=" * 65)
    print(f"   🎯 ACOUSTIC PREDICTION: {label.upper()}")
    print("=" * 65)
    print(f"   • Primary Label       : {label}")
    print(f"   • Model Confidence    : {confidence * 100.0:.2f} %")
    print(f"   • Processing Latency  : {inference_time:.1f} ms")
    print(f"   • CADIE Triage Risk   : {risk_level} (Score: {score:.3f})")
    print(f"   • Recommended Action  : {action}")

    if factors:
        print("\n[*] CADIE Multimodal Evidence Factors:")
        for factor in factors:
            print(f"   - {factor}")

    if top_k:
        print("\n[*] Top-5 Class Probability Distribution:")
        for idx, item in enumerate(top_k, 1):
            if isinstance(item, dict):
                c_lbl = item.get("label")
                c_cnf = float(item.get("confidence", 0.0)) * 100
            elif isinstance(item, (tuple, list)):
                c_lbl = item[0]
                c_cnf = float(item[1]) * 100
            else:
                continue
            bar_len = int(c_cnf / 4)
            bar = "█" * bar_len + "░" * (25 - bar_len)
            print(f"   {idx}. {c_lbl:<18} [{bar}] {c_cnf:>6.2f}%")

    print("=" * 65 + "\n")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "test_audio.pcm"
    predict_audio_file(target)
