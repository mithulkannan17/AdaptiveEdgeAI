@echo off
TITLE AuraForest Sentinel — Cloudflare Public Tunnel
COLOR 0B
cls
echo =================================================================
echo    AURAFOREST SENTINEL — CLOUDFLARE PUBLIC CLOUD BRIDGE
echo =================================================================
echo.
echo [*] Exposing local FastAPI backend (Port 8000) to the internet...
echo.

IF EXIST "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    SET "CF_BIN=C:\Program Files (x86)\cloudflared\cloudflared.exe"
) ELSE IF EXIST "C:\Program Files\cloudflared\cloudflared.exe" (
    SET "CF_BIN=C:\Program Files\cloudflared\cloudflared.exe"
) ELSE (
    SET "CF_BIN=cloudflared"
)

echo [!] Copy the *.trycloudflare.com URL shown below.
echo [!] In Streamlit Cloud Settings -^> Secrets, set:
echo     AURAFOREST_API_URL = "https://<your-url>.trycloudflare.com"
echo =================================================================
echo.
"%CF_BIN%" tunnel --url http://localhost:8000
pause

