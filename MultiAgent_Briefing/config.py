"""
MultiAgent_Briefing — central configuration
Reads the personal SKILL profile and exposes system paths.
All secrets are loaded from the single root OPS_Native_AI/.env.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Single .env for the whole OPS_Native_AI app — load it once here at import time
_ROOT_ENV = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ROOT_ENV, override=False)

BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parent

# ── Skill profiles ─────────────────────────────────────────────────────────────
# Directory containing all personal *_skill.md files (one per user).
# The trigger engine and orchestrator scan this directory — no hardcoded user.
SKILLS_DIR = REPO_ROOT / "AI Architecture" / "skills" / "Personal Skills"

# ── Output ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Jira / Confluence ──────────────────────────────────────────────────────────
JIRA_BASE_URL           = os.getenv("JIRA_BASE_URL", "https://tomtom.atlassian.net")
JIRA_PROJECT            = os.getenv("JIRA_PROJECT", "")  # fallback; primary source is skill.md
JIRA_EMAIL              = os.getenv("JIRA_EMAIL", "lalit.patkar@tomtom.com")
JIRA_API_TOKEN          = os.getenv("JIRA_API_TOKEN", "")       # set in .env
# Numeric project ID required for pre-filled ticket-creation links in email.
# Find it: Jira → Project Settings → Details → Project ID in the URL.
JIRA_PROJECT_NUMERIC_ID = os.getenv("JIRA_PROJECT_NUMERIC_ID", "")

# SLA thresholds (hours without an update)
SLA_WARNING_HOURS    = 48
SLA_ESCALATION_HOURS = 72

# ── Quality thresholds ─────────────────────────────────────────────────────────
FTA_TARGET     = 95.0   # percent
FTA_ALERT      = 92.0   # P1 alert below this
FTA_AMBER      = 95.0   # amber watch below this

COQ_HEALTHY    = 5.0    # percent (< 5%)
COQ_MONITOR    = 7.0    # 5-7% P3
COQ_INVESTIGATE = 10.0  # 7-10% P2
# > 10% P1 Escalate

YIELD_TARGET = 95.0   # percent (first-pass yield, higher is better)
YIELD_ALERT  = 94.0   # amber below this

EFF_ALERT_DROP = 20.0   # percent drop from previous sprint → flag

# ── Use-case triggers ──────────────────────────────────────────────────────────
USE_CASES = {
    "UC1": {"name": "Daily Operational Briefing",          "trigger": "Calendar 07:30 daily"},
    "UC2": {"name": "Jira SLA & Status Follow-Up",         "trigger": "Jira event + 2-hour poll"},
    "UC3": {"name": "Automated Weekly Report Generation",  "trigger": "Calendar Friday 16:00"},
    "UC4": {"name": "Quality & Metric Early Warning Alert","trigger": "Metric 30-min PBI poll"},
    "UC5": {"name": "Plan vs. Actual Auto-Update & CRD",   "trigger": "Calendar 17:00 daily"},
}
