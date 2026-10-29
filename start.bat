@echo off
setlocal enabledelayedexpansion
title OPS Native AI — POC Launcher

echo.
echo ============================================================
echo   OPS Native AI — POC Launcher
echo ============================================================
echo.

:: ── Check Python ──────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python not found. Install Python 3.11+ and re-run.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   Python : %%v

:: ── Paths ─────────────────────────────────────────────────────
:: The laptop onboarding server is retired (_archive/, 29 Oct 2026): users onboard in OPS Hub.
set ROOT=%~dp0
set AGENT=%ROOT%MultiAgent_Briefing

echo   Root    : %ROOT%
echo   Agents  : %AGENT%
echo.

:: ── Install dependencies ───────────────────────────────────────
echo   [1/1] Installing MultiAgent Briefing dependencies...
pip install -r "%AGENT%\requirements.txt" --quiet
if errorlevel 1 (
    echo   [WARN] Some MultiAgent packages failed to install — check manually.
)
echo   Dependencies ready.
echo.

:: ── Instructions ──────────────────────────────────────────────
echo.
echo ============================================================
echo   WHAT TO DO NEXT
echo ============================================================
echo.
echo   STEP 1 — Onboard in OPS Hub (profiles are created there):
echo            https://tomtom-ops-hub.bravewave-803863cf.westeurope.azurecontainerapps.io/onboarding
echo.
echo   STEP 2 — Run a use case manually:
echo.
echo            cd "%AGENT%"
echo            python run_now.py
echo.
echo            Or fire directly:
echo            python run_now.py --uc UC1
echo            python run_now.py --uc UC2
echo            python run_now.py --uc UC4
echo.
echo   The email will arrive in your Outlook inbox.
echo.
pause
