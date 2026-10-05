@echo off
title OPS Native AI — Scheduled Trigger

set AGENT=C:\Users\patkar\OneDrive - TomTom\Deployed\OPS_Native_AI_Product\MultiAgent_Briefing

cd /d "%AGENT%"
python fire_all_now.py >> "%AGENT%\output\task_scheduler.log" 2>&1
