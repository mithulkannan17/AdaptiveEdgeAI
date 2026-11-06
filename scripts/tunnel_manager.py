import os
import re
import sys
import time
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def find_cloudflared() -> str:
    candidates = [
        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
        r"C:\Program Files\cloudflared\cloudflared.exe",
        "cloudflared",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "cloudflared"

def update_file(path: Path, pattern: str, replacement: str):
    text = path.read_text(encoding="utf-8")
    new_text = re.sub(pattern, replacement, text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print(f"[✓] Updated {path.name}")

def main():
    cf_bin = find_cloudflared()
    print(f"[*] Starting Cloudflare Tunnel using: {cf_bin}")
    proc = subprocess.Popen(
        [cf_bin, "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    tunnel_url = None
    for line in iter(proc.stderr.readline, ""):
        sys.stderr.write(line)
        m = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
        if m:
            tunnel_url = m.group(0)
            break

    if not tunnel_url:
        print("[!] Failed to obtain tunnel URL.")
        return

    print("\n" + "=" * 60)
    print(f"🚀 ACTIVE CLOUDFLARE TUNNEL URL: {tunnel_url}")
    print("=" * 60)

    # Save to local file
    (PROJECT_ROOT / ".tunnel_url").write_text(tunnel_url, encoding="utf-8")

    # Update app.py and runtime_data_source.py
    app_py = PROJECT_ROOT / "dashboard" / "app.py"
    rtds_py = PROJECT_ROOT / "dashboard" / "runtime_data_source.py"

    pattern = r'ACTIVE_TUNNEL_URL = "https://[a-zA-Z0-9\-]+\.trycloudflare\.com"'
    repl = f'ACTIVE_TUNNEL_URL = "{tunnel_url}"'

    update_file(app_py, pattern, repl)
    update_file(rtds_py, pattern, repl)

    # Git push to trigger automatic redeployment of Streamlit Cloud
    try:
        subprocess.run(["git", "add", "dashboard/app.py", "dashboard/runtime_data_source.py"], cwd=str(PROJECT_ROOT), check=True)
        subprocess.run(["git", "commit", "-m", f"chore: sync active cloudflare tunnel URL to {tunnel_url}"], cwd=str(PROJECT_ROOT), check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(PROJECT_ROOT), check=True)
        print("[✓] Pushed updated tunnel URL to GitHub main branch!")
    except Exception as e:
        print(f"[!] Git push warning: {e}")

    print("\n[✓] Tunnel running. Press Ctrl+C to terminate.")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()

if __name__ == "__main__":
    main()
