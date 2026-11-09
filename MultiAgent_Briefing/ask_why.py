"""
"Ask why" (idea 1, 9 Nov 2026; OSI-039, OSI-045): every headline number in an email links to an OPS Hub page
that shows where the number came from — process types, work units, operators (when the email shows them),
8-week trend, root cause and action.

How it works (ADR-015):
  1. Before an email is built, snapshot() saves the numbers the email is made from, already computed by SQL and
     rules, as one JSON file on the opshub-config share (Native AI: /data/config/drill, OPS Hub: /app/config/drill).
  2. The email's links carry only that file's random id and the metric: <OPS Hub>/why?r=<id>&m=fta.
  3. OPS Hub shows the file to its owner (or an admin) with a fixed template, so the page always matches the email.

No LLM anywhere (ADR-001): nothing here or on the page generates text. Files are never deleted or overwritten
(rule book: never delete data). ASK_WHY=1 switches the links on; the default is off until the OPS Hub page is live,
so no email ever links to a page that does not exist yet.
"""
from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

OPSHUB_BASE = "https://tomtom-ops-hub.bravewave-803863cf.westeurope.azurecontainerapps.io"
METRICS = {"fta": "FTA", "efficiency": "Efficiency", "coq": "CoQ", "yield": "Yield"}

# What the page may show: the same parts of the analytics result the email is built from. Anything else (raw
# rows, client objects, Jira) stays out, so the file holds nothing the email did not already say.
_KEEP = ("week_label", "data_label", "scope_label", "report_type",
         "fta_current", "fta_prev_week", "fta_rag", "efficiency_vs_bl", "efficiency_rag", "coq_current", "coq_rag",
         "copq_pct", "yield_current", "yield_rag", "yield_note", "sampling_pct", "prod_tasks", "total_qc",
         "prod_hrs", "qc_hrs", "process_breakdown", "workunit_breakdown", "planning_breakdown",
         "operator_breakdown", "operator_levels", "root_cause", "metrics_4w", "trend_weeks", "overall_trend")


def enabled() -> bool:
    """ASK_WHY=1 on the job turns the links on (off by default: the OPS Hub page must be live first)."""
    return os.getenv("ASK_WHY", "0").strip().lower() in ("1", "true", "on")


def drill_dir() -> Path:
    """Where snapshots go: ASK_WHY_DIR, else the opshub-config share on Azure, else the local output folder."""
    if os.getenv("ASK_WHY_DIR"):
        return Path(os.environ["ASK_WHY_DIR"])
    if Path("/data/config").is_dir():
        return Path("/data/config/drill")
    from config import OUTPUT_DIR
    return Path(OUTPUT_DIR) / "drill"


def new_id() -> str:
    """32 hex characters from the OS random source: not guessable, and OPS Hub accepts nothing else."""
    return secrets.token_hex(16)


def snapshot(analytics: dict | None, skill: dict | None, uc: str) -> dict[str, str]:
    """Save the email's numbers and add analytics["why_links"] = {metric: url}. Returns the links ({} when off,
    without data, or when saving fails — the email then goes out exactly as before, without links)."""
    if not enabled() or not analytics or analytics.get("no_scope") or not analytics.get("live", True):
        return {}
    owner = str((skill or {}).get("user") or "").strip().lower()
    if not owner:
        return {}                          # why: OPS Hub shows a snapshot only to its owner, so one is needed
    rid = new_id()
    doc: dict[str, Any] = {"id": rid, "uc": uc, "owner": owner,
                           "project": (skill or {}).get("project_name") or "",
                           "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           "analytics": {k: analytics.get(k) for k in _KEEP if k in analytics},
                           "period": _period(analytics), "rules": _rules()}
    try:
        folder = drill_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{rid}.json"
        tmp = folder / f".{rid}.tmp"
        # why: plain write + rename, no copy2 / chmod (Azure Files refuses them, 6 Nov lesson); the id is new,
        # so nothing is ever overwritten
        tmp.write_text(json.dumps(doc, default=str, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except Exception as exc:
        print(f"[ask_why] snapshot not saved, email sent without links: {exc}")
        return {}
    base = os.getenv("OPSHUB_URL", OPSHUB_BASE).rstrip("/")
    links = {m: f"{base}/why?r={rid}&m={m}" for m in METRICS}
    analytics["why_links"] = links
    return links


def _period(analytics: dict) -> str:
    """The data period exactly as the email header words it (email_html.period_label), fixed at send time."""
    from email_html import alert_week_note, period_label
    wk = analytics.get("week_label") or ""
    try:
        return period_label(wk, fallback_note=alert_week_note(analytics)) if wk else ""
    except Exception:                      # why: a wording problem must never cost the email its links
        return str(wk)


def _rules() -> dict:
    """The email's own judging rules, so the page marks and filters exactly as the email does."""
    from agents.analytics_agent import MIN_QC_TO_FLAG
    from email_briefing_pt import OP_MIN_PROD_HOURS
    return {"min_qc_to_judge": MIN_QC_TO_FLAG, "op_min_prod_hours": OP_MIN_PROD_HOURS}


def _a(url: str, text: str) -> str:
    """One Outlook-safe link."""
    return f'<a href="{escape(url, quote=True)}" style="color:#1F5FAD;text-decoration:underline">{text}</a>'


def links_row(analytics: dict | None) -> str:
    """'Ask why: FTA · Efficiency · CoQ · Yield' under the KPI boxes; "" without links (email as before)."""
    links = (analytics or {}).get("why_links") or {}
    if not links:
        return ""
    parts = " &nbsp;·&nbsp; ".join(_a(links[m], label) for m, label in METRICS.items() if m in links)
    return ('<div style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#5A6B7D;margin:-8px 0 14px">'
            f'<b>Ask why</b> — see where each number comes from: {parts}</div>')


def alert_link(analytics: dict | None, metric_key: str) -> str:
    """'See why →' for one alert metric (copq shows the CoQ page); "" without links."""
    links = (analytics or {}).get("why_links") or {}
    url = links.get("coq" if metric_key == "copq" else metric_key)
    return f' &nbsp;·&nbsp; {_a(url, "See why &rarr;")}' if url else ""
