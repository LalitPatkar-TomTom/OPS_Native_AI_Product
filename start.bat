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
set ROOT=%~dp0
set ONBOARDING=%ROOT%AI Architecture\Onboarding_Server
set AGENT=%ROOT%MultiAgent_Briefing

echo   Root    : %ROOT%
echo   Server  : %ONBOARDING%
echo   Agents  : %AGENT%
echo.

:: ── Install dependencies ───────────────────────────────────────
echo   [1/3] Installing Onboarding Server dependencies...
pip install -r "%ONBOARDING%\requirements.txt" --quiet
if errorlevel 1 (
    echo   [WARN] Some Onboarding Server packages failed to install — check manually.
)

echo   [2/3] Installing MultiAgent Briefing dependencies...
pip install -r "%AGENT%\requirements.txt" --quiet
if errorlevel 1 (
    echo   [WARN] Some MultiAgent packages failed to install — check manually.
)
echo   Dependencies ready.
echo.

:: ── Start Onboarding Server in a new window ───────────────────
echo   [3/3] Starting Onboarding Server on http://localhost:8010 ...
start "OPS Native AI — Onboarding Server" cmd /k "cd /d "%ONBOARDING%" && python server.py"

:: Give the server a moment to start
timeout /t 3 /nobreak >nul

:: ── Open onboarding form ───────────────────────────────────────
set FORM=%ROOT%AI Architecture\HighLevelDocs\UserOnboarding.HTML
if exist "%FORM%" (
    echo   Opening Onboarding Form in browser...
    start "" "%FORM%"
) else (
    echo   [WARN] Onboarding form not found at: %FORM%
)

:: ── Instructions ──────────────────────────────────────────────
echo.
echo ============================================================
echo   WHAT TO DO NEXT
echo ============================================================
echo.
echo   STEP 1 — Fill the Onboarding Form (opens in browser)
echo            Connect Microsoft account when prompted.
echo            Submit — your skill profile is auto-generated.
echo.
echo   STEP 2 — Wait ~30 seconds for your skill file to appear in:
echo            AI Architecture\skills\Personal Skills\
echo.
echo   STEP 3 — Run a use case manually:
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
echo ============================================================
echo   Onboarding Server is running in the other window.
echo   Close that window to stop it.
echo ============================================================
echo.
pause
