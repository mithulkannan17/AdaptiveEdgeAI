@echo off
TITLE AuraForest Sentinel — Defense Command Platform
COLOR 0A
cls
echo =================================================================
echo        AURAFOREST SENTINEL — TACTICAL EDGE DEFENSE PLATFORM
echo =================================================================
echo.
cd /d "%~dp0"

IF EXIST ".venv\Scripts\python.exe" (
    SET "PY_CMD=.venv\Scripts\python.exe"
) ELSE (
    SET "PY_CMD=python"
)

echo [*] Launching AuraForest Unified System Services...
echo.
%PY_CMD% run_system.py
pause
