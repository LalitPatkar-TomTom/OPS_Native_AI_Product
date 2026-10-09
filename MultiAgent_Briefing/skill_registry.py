"""
Skill Registry — parses lalit's personal skill file into a structured trigger spec.

Reads the markdown SKILL profile and extracts:
  - Active use cases and their trigger definitions
  - Quiet hours (no-alert window)
  - Timezone
  - Delivery preferences
  - Alert thresholds (FTA, SLA)

The parsed output drives the Trigger Engine — no manual config needed.
"""
import re
from pathlib import Path
from typing import Any

from config import SKILLS_DIR


# ── Trigger string parser ──────────────────────────────────────────────────────

def _parse_time(time_str: str) -> tuple[int, int]:
    """'07:30' → (7, 30)"""
    h, m = time_str.strip().split(":")
    return int(h), int(m)


def _parse_weekday(day_str: str) -> str:
    """'Friday' → 'fri'  (APScheduler day_of_week format)"""
    mapping = {
        "monday": "mon", "tuesday": "tue", "wednesday": "wed",
        "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun",
    }
    return mapping.get(day_str.lower(), "fri")


def _parse_trigger(raw: str) -> dict[str, Any]:
    """
    Convert a plain-English trigger string from the skill file into a spec dict.

    Patterns handled:
      "Calendar · 07:30 daily"            → cron, every day at 07:30
      "Calendar · Friday 16:00"           → cron, every Friday at 16:00
      "Calendar · 17:00 daily"            → cron, every day at 17:00
      "Metric · 30-min PBI poll"          → poll, every 30 minutes, source=metrics
      "Jira event + 2-hour poll"          → poll, every 120 minutes, source=jira
    """
    s = raw.strip()

    # Calendar · HH:MM daily
    m = re.search(r"Calendar\s*[·•]\s*(\d{1,2}:\d{2})\s+daily", s, re.I)
    if m:
        h, mn = _parse_time(m.group(1))
        return {"type": "cron", "hour": h, "minute": mn, "day_of_week": "*",
                "description": f"Every day at {m.group(1)}"}

    # Calendar · DayName HH:MM
    m = re.search(r"Calendar\s*[·•]\s*(\w+day)\s+(\d{1,2}:\d{2})", s, re.I)
    if m:
        day = _parse_weekday(m.group(1))
        h, mn = _parse_time(m.group(2))
        return {"type": "cron", "hour": h, "minute": mn, "day_of_week": day,
                "description": f"Every {m.group(1)} at {m.group(2)}"}

    # Calendar · HH:MM DayName  (reversed order)
    m = re.search(r"Calendar\s*[·•]\s*(\d{1,2}:\d{2})\s+(\w+day)", s, re.I)
    if m:
        h, mn = _parse_time(m.group(1))
        day = _parse_weekday(m.group(2))
        return {"type": "cron", "hour": h, "minute": mn, "day_of_week": day,
                "description": f"Every {m.group(2)} at {m.group(1)}"}

    # Metric · 30-min PBI poll  /  Quality · 30-min poll
    m = re.search(r"(\d+)-min\b", s, re.I)
    if m:
        return {"type": "poll", "interval_minutes": int(m.group(1)),
                "source": "metrics", "description": f"Every {m.group(1)} minutes (metrics)"}

    # Jira event + 2-hour poll  /  2-hour poll
    m = re.search(r"(\d+)-hour poll", s, re.I)
    if m:
        mins = int(m.group(1)) * 60
        return {"type": "poll", "interval_minutes": mins,
                "source": "jira", "description": f"Every {m.group(1)} hours (Jira)"}

    return {"type": "unknown", "raw": raw,
            "description": f"Unrecognised trigger: {raw!r}"}


# ── Preference extractors ──────────────────────────────────────────────────────

def _extract_quiet_hours(text: str) -> tuple[int, int] | None:
    """
    Parse quiet hours from either format:
      Table row: | Quiet Hours (no alerts) | 19:00 – 08:00 |
      Inline:    Quiet Hours (no alerts): 19:00–08:00
    Returns (start_hour, end_hour) or None.
    """
    m = re.search(
        r"Quiet Hours[^|\n]*[|:]\s*(\d{1,2}):\d{2}\s*[–\-–]+\s*(\d{1,2}):\d{2}",
        text,
    )
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _extract_timezone(text: str) -> str:
    """
    Infer timezone from location mentions (Pune → Asia/Kolkata).
    Falls back to Asia/Kolkata for TomTom Pune context.
    """
    # Explicit timezone line
    m = re.search(r"Timezone[:\s]+([A-Za-z/_]+)", text)
    if m and "/" in m.group(1):
        return m.group(1).strip()
    # Location inference
    if re.search(r"\bPune\b", text, re.I):
        return "Asia/Kolkata"
    if re.search(r"\bAmsterdam\b", text, re.I):
        return "Europe/Amsterdam"
    return "Asia/Kolkata"


def _extract_briefing_time(text: str) -> str:
    """Extract 'Morning Briefing Time: 08:30'"""
    m = re.search(r"Morning Briefing Time[|\s:]+(\d{1,2}:\d{2})", text)
    return m.group(1) if m else "08:30"


def _extract_alert_channel(text: str) -> str:
    """Extract 'Alert Channel: Teams'"""
    m = re.search(r"Alert Channel[|\s:]+([^\n|]+)", text)
    return m.group(1).strip() if m else "file"


def _normalize_metric_key(name: str) -> str | None:
    """Map a metric label from the onboarding table to a canonical key."""
    n = name.lower()
    if "fta" in n or "first time" in n:          return "fta"
    if "efficiency" in n:                          return "efficiency"
    if "copq" in n or "cost of poor" in n:        return "copq"
    if "coq" in n or "cost of quality" in n:      return "coq"
    if "yield" in n:                               return "yield"
    return None


def _parse_pct(s: str) -> float | None:
    """Extract first numeric value from a string like '95%', 'below 92%', '<90%'."""
    m = re.search(r"(\d[\d.]*)", s.replace(",", "."))
    return float(m.group(1)) if m else None


def _parse_direction(alert_str: str, dir_str: str) -> str:
    """
    Return 'drop' (alert when value falls below threshold)
        or 'rise' (alert when value rises above threshold).

    Reads both the Alert At cell ('below 92%', 'above 10%')
    and the Direction cell ('↓ Alert on drop', '↑ Alert on rise').
    """
    combined = (alert_str + " " + dir_str).lower()
    if "above" in combined or "rise" in combined or "increase" in combined:
        return "rise"
    return "drop"   # default: alert on drop (FTA, Efficiency)


def _iter_metric_rows(text: str):
    """
    Yield each data row of every Metrics table as {header_lower: cell}.

    A Metrics table is any markdown table whose header row has both a
    "Metric" and an "Alert" column. Columns are mapped by header name, so the
    5-col legacy, 6-col (Level, no Scope) and 7-col (Level + Scope) onboarding
    formats all parse correctly.
    """
    headers: list[str] | None = None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            headers = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if headers is None:
            low = [c.lower() for c in cells]
            if any(c.startswith("metric") for c in low) and any("alert" in c for c in low):
                headers = low
            continue
        if all(set(c) <= set("-: ") for c in cells):   # |---|---| separator
            continue
        yield {h: (cells[i] if i < len(cells) else "") for i, h in enumerate(headers)}


def _col(row: dict[str, str], *names: str) -> str:
    """Return the first cell whose header starts with any of names."""
    for h, v in row.items():
        if any(h.startswith(n) for n in names):
            return v
    return ""


def _extract_metric_thresholds(text: str) -> dict[str, dict]:
    """
    Parse all rows from the Metrics Profile table.

    Table format (new onboarding):
      | Metric | Level | Target | Alert At | Direction | Source |
      | FTA — First Time Accuracy | Process Type | 95% | below 92% | ↓ Alert on drop | Databricks |

    Returns dict keyed by canonical metric key:
      {
        "fta":        {"target": 95.0, "alert": 92.0, "direction": "drop"},
        "efficiency": {"target": 100.0, "alert": 90.0, "direction": "drop"},
        "coq":        {"target": 7.0,  "alert": 10.0, "direction": "rise"},
      }
    Falls back to sensible defaults for any metric not found.
    """
    defaults = {
        "fta":        {"target": 95.0,  "alert": 92.0,  "direction": "drop"},
        "efficiency": {"target": 100.0, "alert": 90.0,  "direction": "drop"},
        "coq":        {"target": 7.0,   "alert": 10.0,  "direction": "rise"},
        "copq":       {"target": 5.0,   "alert": 8.0,   "direction": "rise"},
        "yield":      {"target": 95.0,  "alert": 94.0,  "direction": "drop"},
    }
    result: dict[str, dict] = {}

    for row in _iter_metric_rows(text):
        key = _normalize_metric_key(_col(row, "metric"))
        if key is None or key in result:   # first declaration wins
            continue
        alert_str  = _col(row, "alert")
        target_val = _parse_pct(_col(row, "target"))
        alert_val  = _parse_pct(alert_str)
        direction  = _parse_direction(alert_str, _col(row, "direction"))

        if target_val is not None or alert_val is not None:
            d = dict(defaults.get(key, {}))
            if target_val is not None: d["target"]    = target_val
            if alert_val  is not None: d["alert"]     = alert_val
            d["direction"] = direction
            result[key] = d

    # Fill in any missing metrics with defaults
    for k, v in defaults.items():
        if k not in result:
            result[k] = dict(v)

    return result


def _extract_primary_metrics(text: str) -> tuple[list[str], bool]:
    """
    Detect which metrics the user cares about from their Metrics Profile table.
    Returns (metric_keys, include_operator_breakdown).
    Defaults to (['fta', 'efficiency', 'coq'], False) if no metrics table found.
    """
    section_m = re.search(r"##\s*\d*\.?\s*Metrics Profile(.*?)(?=^##|\Z)", text, re.S | re.M)
    section = section_m.group(1) if section_m else text

    metrics: list[str] = []
    if re.search(r"\|\s*FTA\b|\bFirst Time Accuracy\b", section, re.I):
        metrics.append("fta")
    if re.search(r"\|\s*(User\s+)?Efficiency|\bManual Efficiency\b|\bEfficiency vs\b", section, re.I):
        metrics.append("efficiency")
    if re.search(r"\|\s*CopQ\b|\bCost of Poor Quality\b|\bOperational Waste\b", section, re.I):
        metrics.append("copq")
    elif re.search(r"\|\s*CoQ\b|\bCost of Quality\b", section, re.I):
        metrics.append("coq")
    if re.search(r"\|\s*Yield\b", section, re.I):
        metrics.append("yield")

    # Any metric row with Level="Operator" (or metric named "Operator View") enables operator breakdown
    include_ops = bool(
        re.search(r"\|\s*Operator View\b|\boperator[_\s]view\b", section, re.I)
        or re.search(r"\|\s*[A-Za-z][^|]+\|\s*Operator\s*\|", section, re.I)
    )

    return (metrics if metrics else ["fta", "efficiency", "coq"]), include_ops


def _extract_explicit_scope(text: str, skip_words: re.Pattern) -> dict[str, list[str]]:
    """
    Explicit named types / planningids (bold markdown format, as written by
    the onboarding form):
      **Databricks Process Types:** orbis-dir-turnrestriction, ...
      **Databricks Planning IDs:** ADAS-RMLanes, ...
    Bold markdown is required to avoid matching prose.
    """
    result: dict[str, list[str]] = {}
    for key, pattern, none_vals in (
        ("databricks_process_types", r"\*\*Databricks [Pp]rocess [Tt]ypes?:?\*\*:?\s+([^\n|]+)",
         ("(none — filter by feature)", "(none)", "-", "—")),
        ("databricks_planning_ids", r"\*\*Databricks [Pp]lanning [Ii][Dd]s?:?\*\*:?\s+([^\n|]+)",
         ("(none)", "-", "—")),
    ):
        m = re.search(pattern, text, re.I)
        if not m:
            continue
        raw = m.group(1).strip()
        if raw and raw not in none_vals and not skip_words.search(raw):
            vals = [p.strip() for p in re.split(r"[,;]", raw)
                    if p.strip() and not skip_words.search(p)]
            if vals:
                result[key] = vals
    return result


def _extract_databricks_scope(text: str) -> dict[str, Any]:
    """
    Extract Databricks scope filter from the skill file.

    Scope modes (checked in priority order):
      keyword:gen,lane  — WHERE LOWER(processType) LIKE '%gen%' OR LIKE '%lane%'
      keyword:gen       — WHERE LOWER(processType) LIKE '%gen%'
      keyword:lane      — WHERE LOWER(processType) LIKE '%lane%'
      all               — no filter, full table sorted by volume
      defined           — explicit process types or planningids listed

    For 'defined' mode, looks for:
      "Databricks Process Types: orbis-dir-turnrestriction, ..."
      "Databricks Planning IDs: ADAS-RMLanes, ..."
    """
    result: dict[str, Any] = {}
    _SKIP_WORDS = re.compile(r'\ball\b|\bvolume\b|\bsorted\b|\bhighest\b|\bfamily\b|\bkeyword\b', re.I)

    # Step 1 — an explicit list from the onboarding form always wins; LLM-merged
    # prose ("the two RM Lanes process types") must not widen it to keyword scope.
    explicit = _extract_explicit_scope(text, _SKIP_WORDS)
    if explicit:
        return {"scope_mode": "defined", **explicit}

    # Step 2 — detect keyword / all scope modes from plain-English descriptions
    has_gen  = bool(re.search(r'\bGEN\b.{0,25}process types|\bGEN-family\b', text))
    has_lane = bool(re.search(r'\bLanes?\b.{0,25}process types|\bLane.{0,8}family\b', text))
    has_all  = bool(re.search(
        r'[Aa]ll available process types'
        r'|[Aa]ll.*Databricks process types.*volume'
        r'|process types.*prioriti[sz]ed by volume',
        text,
    ))

    if has_gen and has_lane:
        result["scope_mode"] = "keyword:gen,lane"
        return result
    if has_gen:
        result["scope_mode"] = "keyword:gen"
        return result
    if has_lane:
        result["scope_mode"] = "keyword:lane"
        return result
    if has_all:
        result["scope_mode"] = "all"
        return result

    result["scope_mode"] = "defined"

    # Legacy single feature (planningid fallback)
    if "databricks_planning_ids" not in result:
        m = re.search(r"Databricks feature[^:\n]*[:\s*|]+([^\n|]+)", text, re.I)
        if m:
            feature = m.group(1).strip()
            if feature and feature not in ("(none)", "-", "—") \
                    and not _SKIP_WORDS.search(feature):
                result["databricks_planning_ids"] = [feature]

    # Step 3 — parse from Metrics Profile table (Metric | Level | Scope | ...)
    # Rows where Level = "Process Type" → scope values are process type names
    # Rows where Level = "Planning ID"  → scope values are planning IDs
    # Only tables with a real "Scope" column qualify (the 6-col form has none).
    if "databricks_process_types" not in result and "databricks_planning_ids" not in result:
        pts_from_table: list[str] = []
        pids_from_table: list[str] = []
        _SKIP_SCOPE = {"—", "-", "(all)", ""}
        for row in _iter_metric_rows(text):
            if "scope" not in row:
                continue
            level = _col(row, "level").lower()
            scope = row["scope"]
            if scope in _SKIP_SCOPE or not level:
                continue
            items = [p.strip() for p in scope.split(",") if p.strip() and p.strip() not in _SKIP_SCOPE]
            if "process type" in level or "operator" in level:
                pts_from_table.extend(items)
            elif "planning id" in level or "deliverable" in level:
                pids_from_table.extend(items)
        seen: set[str] = set()
        pts_unique = [p for p in pts_from_table if p not in seen and not seen.add(p)]  # type: ignore[func-returns-value]
        if pts_unique:
            result["databricks_process_types"] = pts_unique
        seen = set()
        pids_unique = [p for p in pids_from_table if p not in seen and not seen.add(p)]  # type: ignore[func-returns-value]
        if pids_unique:
            result["databricks_planning_ids"] = pids_unique

    return result


def _extract_project_config(text: str) -> dict[str, str]:
    """
    Extract project name and Jira project key from the skill file.

    Primary:  Active Projects table row
                | RM Lanes | MCPET | Manager | Active |
    Fallback: "Project Keys monitored: MCPET"
    Fallback: "Jira project key: MCPET" (Quick Agent Summary inline mention)
    """
    project_name = ""
    jira_project = ""

    # Active Projects table: | Project Name | JIRA_KEY | Role | Active |
    m = re.search(
        r"\|\s*([^|\-][^|]+?)\s*\|\s*([A-Z][A-Z0-9]{1,15})\s*\|[^|]+\|\s*Active\s*\|",
        text,
    )
    if m:
        project_name = m.group(1).strip()
        jira_project = m.group(2).strip()

    # Fallback: "Project Keys monitored: MCPET"
    if not jira_project:
        m2 = re.search(r"Project Keys?\s+monitored[:\s*|]+([A-Z][A-Z0-9]+)", text, re.I)
        if m2:
            jira_project = m2.group(1).strip()

    # Fallback: "Jira project key: MCPET" (inline in Quick Agent Summary)
    if not jira_project:
        m3 = re.search(r"Jira project key[:\s]+([A-Z][A-Z0-9]+)", text, re.I)
        if m3:
            jira_project = m3.group(1).strip()

    return {"project_name": project_name, "jira_project": jira_project}


def _extract_confluence_config(text: str) -> dict[str, Any]:
    """
    Extract Confluence page IDs from URLs mentioned in the skill file.

    Parses patterns like:
      https://tomtom.atlassian.net/wiki/spaces/MSO/pages/2063630424/Page+Title
    Returns {"confluence_pages": [{"space": "MSO", "page_id": "2063630424"}, ...]}
    """
    page_pattern = re.compile(
        r"https?://[^/]+/wiki/spaces/([A-Z0-9]+)/pages/(\d+)"
    )
    seen: set[str] = set()
    pages: list[dict[str, str]] = []
    for m in page_pattern.finditer(text):
        pid = m.group(2)
        if pid not in seen:
            seen.add(pid)
            pages.append({"space": m.group(1), "page_id": pid})
    return {"confluence_pages": pages}


def _extract_cc_recipients(text: str) -> list[str]:
    """
    Parse 'Briefing CC: a@b.com; c@d.com' from skill file header.
    Returns a list of email strings (empty list if not set).
    """
    m = re.search(r"\*\*Briefing CC[:\s]*\*\*[:\s]*([^\n]+)", text)
    if not m:
        return []
    raw = m.group(1).strip()
    return [e.strip() for e in re.split(r"[;,]", raw) if "@" in e.strip()]


def _extract_sla_thresholds(text: str) -> dict[str, int]:
    """Extract Jira SLA warning and escalation hours."""
    warn = 48
    esc  = 72
    m_w = re.search(r"SLA.*?Warning.*?(\d+)\s*hours?", text, re.I)
    m_e = re.search(r"SLA.*?Escalation.*?(\d+)\s*hours?", text, re.I)
    if m_w:
        warn = int(m_w.group(1))
    if m_e:
        esc = int(m_e.group(1))
    return {"warning_hours": warn, "escalation_hours": esc}


# ── UC table parser ────────────────────────────────────────────────────────────

def _extract_use_cases(text: str) -> list[dict[str, Any]]:
    """
    Parse the Active Use Cases table from the skill file.

    Expected row format:
    | UC1 | Daily Operational Briefing | Calendar · 07:30 daily | ✅ Active |
    """
    uc_row = re.compile(
        r"\|\s*(UC\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(✅\s*Active|Active|❌\s*Inactive|Inactive)\s*\|"
    )
    use_cases = []
    for m in uc_row.finditer(text):
        uc_id, name, trigger_str, status = m.groups()
        trigger_spec = _parse_trigger(trigger_str)
        use_cases.append({
            "uc_id":        uc_id.strip(),
            "name":         name.strip(),
            "trigger_str":  trigger_str.strip(),
            "trigger_spec": trigger_spec,
            "active":       "Active" in status,
        })
    # Deduplicate (table may appear twice in the skill file)
    seen = set()
    unique = []
    for uc in use_cases:
        if uc["uc_id"] not in seen:
            seen.add(uc["uc_id"])
            unique.append(uc)
    return unique


# ── Public API ─────────────────────────────────────────────────────────────────

def load_all_skills(skills_dir: Path | None = None) -> list[dict[str, Any]]:
    """
    Load every personal *_skill.md in the Personal Skills directory.
    Only files whose name contains '@' are treated as personal profiles
    (email-based filenames like lalit.patkar@tomtom.com_skill.md).
    Domain template files without '@' are skipped.
    Returns a list of parsed skill dicts — one per user.
    """
    d = skills_dir or SKILLS_DIR
    personal_files = [f for f in sorted(d.glob("*_skill.md")) if "@" in f.name]
    return [load_skill(f) for f in personal_files]


def load_skill(skill_file: Path) -> dict[str, Any]:
    """
    Parse the personal skill file and return a structured skill dict.

    Returns:
        {
          "user":           "lalit.patkar@tomtom.com",
          "timezone":       "Asia/Kolkata",
          "quiet_hours":    (19, 8),          # (start_hour, end_hour)
          "briefing_time":  "08:30",
          "alert_channel":  "Teams",
          "fta_thresholds": {"target": 95.0, "alert": 92.0},
          "sla_thresholds": {"warning_hours": 48, "escalation_hours": 72},
          "use_cases":      [...],
          "skill_file":     "/path/to/file.md",
        }
    """
    if not skill_file.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_file}")

    text = skill_file.read_text(encoding="utf-8")

    # Filename: lalit.patkar@tomtom.com_skill.md → strip _skill suffix
    user_email = skill_file.stem
    if user_email.endswith("_skill"):
        user_email = user_email[:-6]

    db_scope    = _extract_databricks_scope(text)
    conf_scope  = _extract_confluence_config(text)
    proj        = _extract_project_config(text)
    pri_metrics, include_ops = _extract_primary_metrics(text)
    met_thr     = _extract_metric_thresholds(text)

    # Derive first name from email: lalit.patkar@tomtom.com → "Lalit"
    first_part      = user_email.split("@")[0]           # lalit.patkar
    user_first_name = first_part.split(".")[0].capitalize()  # Lalit

    return {
        "user":                      user_email,
        "user_first_name":           user_first_name,
        "project_name":              proj.get("project_name", ""),
        "jira_project":              proj.get("jira_project", ""),
        "timezone":                  _extract_timezone(text),
        "quiet_hours":               _extract_quiet_hours(text),
        "briefing_time":             _extract_briefing_time(text),
        "alert_channel":             _extract_alert_channel(text),
        "metric_thresholds":         met_thr,
        # backward-compat keys (UC4 reads these directly)
        "fta_thresholds":            met_thr.get("fta",        {"target": 95.0, "alert": 92.0}),
        "coq_thresholds":            met_thr.get("coq",        {"target": 7.0,  "alert": 10.0}),
        "sla_thresholds":            _extract_sla_thresholds(text),
        "use_cases":                 _extract_use_cases(text),
        "primary_metrics":             pri_metrics,
        "include_operator_breakdown":  include_ops,
        "scope_mode":                  db_scope.get("scope_mode", "defined"),
        "databricks_process_types":  db_scope.get("databricks_process_types"),
        "databricks_planning_ids":   db_scope.get("databricks_planning_ids"),
        "databricks_feature":        db_scope.get("databricks_feature"),
        "confluence_pages":          conf_scope.get("confluence_pages", []),
        "cc_recipients":             _extract_cc_recipients(text),
        "skill_file":                str(skill_file),
    }


# ── CLI test ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    # Windows terminals default to cp1252; force UTF-8 for emoji output
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    skills = load_all_skills()
    if not skills:
        print(f"No *_skill.md files found in {SKILLS_DIR}")
        sys.exit(1)

    for skill in skills:
        print(f"\n{'='*60}")
        print(f"=== {skill['user']} ({skill['user_first_name']}) ===")
        print(f"{'='*60}")
        print(f"Project   : {skill['project_name']}  (Jira: {skill['jira_project']})")
        print(f"Timezone  : {skill['timezone']}")
        print(f"Quiet hrs : {skill['quiet_hours']}")
        print(f"Briefing  : {skill['briefing_time']}")
        print(f"Channel   : {skill['alert_channel']}")
        print(f"FTA       : target={skill['fta_thresholds']['target']}%  "
              f"alert={skill['fta_thresholds']['alert']}%")
        print(f"SLA       : warn={skill['sla_thresholds']['warning_hours']}h  "
              f"escalate={skill['sla_thresholds']['escalation_hours']}h")
        print(f"CC        : {', '.join(skill.get('cc_recipients', [])) or '(none)'}")
        active = [u for u in skill['use_cases'] if u['active']]
        print(f"\nActive Use Cases ({len(active)} active):")
        for uc in skill["use_cases"]:
            status = "[ON] " if uc["active"] else "[OFF]"
            spec   = uc["trigger_spec"]
            print(f"  {status} {uc['uc_id']}  {uc['name']}")
            print(f"         Trigger : {uc['trigger_str']}")
            print(f"         Parsed  : type={spec['type']}  "
                  + (f"cron={spec.get('hour','')}:{spec.get('minute',''):02d}  dow={spec.get('day_of_week','*')}"
                     if spec['type'] == 'cron'
                     else f"interval={spec.get('interval_minutes','?')}min  source={spec.get('source','?')}")
            )
