@echo off
title OPS Native AI — Scheduled Trigger

set AGENT=C:\Users\patkar\OneDrive - TomTom\Deployed\OPS_Native_AI_Product\MultiAgent_Briefing

cd /d "%AGENT%"
rem Pull profiles saved by the OPS Hub onboarding form in Azure (never blocks the run)
python sync_skills.py >> "%AGENT%\output\task_scheduler.log" 2>&1
python fire_all_now.py --scheduled >> "%AGENT%\output\task_scheduler.log" 2>&1
