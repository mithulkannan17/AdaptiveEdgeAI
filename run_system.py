"""
AuraForest Sentinel — Unified Production System Launcher
=========================================================

Simultaneously launches and orchestrates:
  1. FastAPI Tactical Backend Server (Port 8000)
  2. Streamlit Sentinel RBAC Command Dashboard (Port 8501)

Features:
  - Concurrent process management with health monitoring.
  - Automatic graceful shutdown on Ctrl+C.
  - Cross-platform support (Windows / Linux / macOS).
"""

from __future__ import annotations

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

def check_backend_health(port: int | str = 8000, timeout: float = 1.0) -> bool:
    """Check if FastAPI backend is healthy and responding."""
    try:
        with urlopen(f"http://127.0.0.1:{port}/docs", timeout=timeout) as response:
            return response.status in (200, 307)
    except Exception:
        return False

def check_dashboard_health(port: int | str = 8501, timeout: float = 1.0) -> bool:
    """Check if Streamlit dashboard is responding."""
    try:
        with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False

def main() -> None:
    print("=" * 65)
    print("   🌲 AURAFOREST SENTINEL — TACTICAL EDGE DEFENSE PLATFORM")
    print("=" * 65)
    print(f"[*] Workspace Root: {PROJECT_ROOT}")
    print(f"[*] Python Runtime: {PYTHON_EXE}")

    backend_port = os.environ.get("BACKEND_PORT", "8000")
    dashboard_port = os.environ.get("PORT", os.environ.get("STREAMLIT_PORT", "8501"))

    os.environ["PYTHONPATH"] = str(PROJECT_ROOT)
    os.environ["AURAFOREST_API_URL"] = f"http://127.0.0.1:{backend_port}"

    backend_cmd = [
        PYTHON_EXE,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(backend_port),
        "--workers",
        "1",
    ]

    dashboard_cmd = [
        PYTHON_EXE,
        "-m",
        "streamlit",
        "run",
        str(PROJECT_ROOT / "dashboard" / "app.py"),
        f"--server.port={dashboard_port}",
        "--server.address=0.0.0.0",
        "--browser.serverAddress=localhost",
        "--server.headless=true",
        "--theme.base=dark",
    ]

    print(f"\n[1/2] 🚀 Starting FastAPI Tactical Backend on http://0.0.0.0:{backend_port} ...")
    backend_proc = subprocess.Popen(backend_cmd, cwd=str(PROJECT_ROOT))

    # Wait for backend readiness
    for _ in range(20):
        time.sleep(0.5)
        if check_backend_health(port=backend_port):
            print("      ✅ Backend REST API is online & healthy.")
            break

    print(f"\n[2/2] 🚀 Starting Streamlit Command Dashboard on http://0.0.0.0:{dashboard_port} ...")
    dashboard_proc = subprocess.Popen(dashboard_cmd, cwd=str(PROJECT_ROOT))

    print("\n" + "=" * 65)
    print("   🟢 AURAFOREST SYSTEM SUCCESSFULLY DEPLOYED & ARMED")
    print("=" * 65)
    print(f"   🌐 Sentinel Gateway URL : http://localhost:{dashboard_port}")
    print(f"   📡 Backend REST API Docs: http://localhost:{backend_port}/docs")
    print("   👑 Chief Ranger Login   : Username: chief | Passcode: auraadmin123")
    print("   🛑 Press Ctrl+C to safely terminate all services.")
    print("=" * 65 + "\n")

    def handle_signal(sig, frame):
        print("\n[!] Initiating graceful shutdown of all AuraForest services...")
        try:
            dashboard_proc.terminate()
            backend_proc.terminate()
            dashboard_proc.wait(timeout=4)
            backend_proc.wait(timeout=4)
        except Exception:
            dashboard_proc.kill()
            backend_proc.kill()
        print("[✓] All services successfully stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        while True:
            time.sleep(1.0)
            if backend_proc.poll() is not None:
                print("[!] Backend server exited unexpectedly.")
                break
            if dashboard_proc.poll() is not None:
                print("[!] Dashboard server exited unexpectedly.")
                break
    except KeyboardInterrupt:
        handle_signal(None, None)

if __name__ == "__main__":
    main()
