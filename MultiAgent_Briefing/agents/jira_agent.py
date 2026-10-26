"""
Jira Agent — fetches relevant MCPET ticket status and SLA health.

Ticket visibility rules (applied via JQL, not post-filter):
  Show a ticket if ANY of the following is true:
    1. Ticket text (summary/description) contains the user's feature/process keywords
    2. The user is the reporter
    3. The user is the assignee

Keywords are derived from the skill profile:
  - databricks_feature  e.g. "RMLanes" → searches "RMLanes" and "RM Lanes"
  - databricks_process_types  e.g. ["orbis-dir-turnrestriction"] → searched as-is
"""
import base64
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (
    JIRA_BASE_URL, JIRA_PROJECT, JIRA_EMAIL, JIRA_API_TOKEN,
    SLA_WARNING_HOURS, SLA_ESCALATION_HOURS,
)
from agents import atlassian_mcp

log = logging.getLogger("jira_agent")


def _auth_header() -> dict:
    creds = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    token = base64.b64encode(creds.encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def _hours_since(updated_str: str) -> float:
    dt  = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - dt).total_seconds() / 3600


# OSI-003: without a window the query returned every open ticket ever created (some from 2021).
DEFAULT_JIRA_WINDOW_DAYS = 365


def sla_levels(skill: dict | None) -> tuple[float, float]:
    """(warning, escalation) hours from the profile (OSI-006); the config defaults when not set."""
    t = (skill or {}).get("sla_thresholds") or {}
    return (t.get("warning_hours") or SLA_WARNING_HOURS, t.get("escalation_hours") or SLA_ESCALATION_HOURS)


def _sla_status(hours: float, warn: float = SLA_WARNING_HOURS, esc: float = SLA_ESCALATION_HOURS) -> str:
    # The status names stay BREACH_72H / WARNING_48H (used across the emails and analytics);
    # the hours behind them now come from each profile.
    if hours >= esc:  return "BREACH_72H"
    if hours >= warn: return "WARNING_48H"
    return "OK"


def created_window(skill: dict | None) -> tuple[str, str]:
    """(JQL clause, plain-English label) for the created-date window of UC2."""
    w = (skill or {}).get("jira_window") or {}
    if w.get("since"):
        return f'AND created >= "{w["since"]}" ', f'created since {w["since"]}'
    days = int(w.get("days") or DEFAULT_JIRA_WINDOW_DAYS)
    label = (f"created in the last {round(days / 365)} year(s)" if days % 365 == 0 and days > 365 else
             f"created in the last {round(days * 12 / 365)} months" if days >= 60 else
             f"created in the last {days} days")
    return f"AND created >= -{days}d ", label


def _keyword_variants(raw: str) -> list[str]:
    """
    Generate search-friendly variants of a keyword for Jira text search.

    Examples:
      "RMLanes"      → ["RMLanes", "RM Lanes"]
      "FMOLanes"     → ["FMOLanes", "FMO Lanes"]
      "RM-Lanes"     → ["RM-Lanes", "RM Lanes"]
      "orbis-update" → ["orbis-update", "orbis update"]
    """
    variants = {raw.strip()}
    # Split PascalCase with consecutive capitals: "RMLanes" → "RM Lanes"
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", raw)  # e.g. RM + Lanes
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", spaced)      # e.g. camel → camel Case
    variants.add(spaced.strip())
    # Replace hyphens/underscores with spaces
    variants.add(re.sub(r"[-_]", " ", raw).strip())
    return [v for v in variants if v]


def _jql_str(value: str) -> str:
    """Escape a value for a double-quoted JQL string (a stray \ or " would break the query)."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _build_jql(skill: dict | None) -> tuple[str, str]:
    """
    Build a JQL string scoped to tickets relevant to the user.

    Returns (jql_string, human_label).
    """
    _skill        = skill or {}
    user_email    = _skill.get("user", JIRA_EMAIL)
    feature       = _skill.get("databricks_feature", "")
    process_types = _skill.get("databricks_process_types") or []
    # jira_project from skill takes priority; config JIRA_PROJECT is a last-resort fallback
    project_key   = _skill.get("jira_project") or JIRA_PROJECT

    if not project_key:
        raise ValueError(
            "No Jira project key found. "
            "Add 'Jira project key: YOURKEY' to the skill file or set JIRA_PROJECT env var."
        )

    # ── Keyword conditions (feature name + process types) ──────────────────────
    kw_clauses: list[str] = []

    if feature:
        for variant in _keyword_variants(feature):
            kw_clauses.append(f'text ~ "{_jql_str(variant)}"')

    if isinstance(process_types, str):
        process_types = [process_types]
    for pt in process_types:
        kw_clauses.append(f'text ~ "{_jql_str(pt)}"')

    # ── Identity conditions (reporter or assignee) ─────────────────────────────
    id_clauses = [
        f'reporter = "{user_email}"',
        f'assignee = "{user_email}"',
    ]

    all_clauses = kw_clauses + id_clauses
    scope_expr  = " OR ".join(all_clauses)
    label       = f"project:{project_key} | feature:{feature or 'none'} | reporter/assignee:{user_email}"

    window_clause, _ = created_window(_skill)
    jql = (
        f"project = {project_key} "
        f"AND statusCategory != Done "
        f"{window_clause}"
        f"AND ({scope_expr}) "
        f"ORDER BY updated ASC"
    )
    return jql, label


def run(skill: dict | None = None) -> dict[str, Any]:
    """
    Fetch relevant MCPET tickets for the given user skill profile.

    Args:
        skill: parsed skill dict from skill_registry.load_skill().
               Drives keyword and identity filtering in JQL.
               Pass None to return all open MCPET tickets (no scope).
    """
    jql, jql_label = _build_jql(skill)

    jira_project = (skill or {}).get("jira_project") or JIRA_PROJECT
    warn_h, esc_h = sla_levels(skill)
    result: dict[str, Any] = {
        "sla_warning_hours":    warn_h,
        "sla_escalation_hours": esc_h,
        "created_window":       created_window(skill)[1],
        "open_tickets": [],
        "sla_breaches": [],
        "sla_warnings": [],
        "total_open":   0,
        "jql":          jql,
        "source":       f"Jira {jira_project}",
        "as_of":        datetime.now(timezone.utc).isoformat(),
        "error":        None,
    }

    if not JIRA_API_TOKEN:
        result["error"] = "JIRA_API_TOKEN not set — add to OPS_Native_AI/.env"
        return result

    body = {
        "jql":        jql,
        "maxResults": 100,
        "fields":     ["summary", "status", "priority", "assignee", "reporter",
                       "updated", "created", "issuetype", "labels", "components"],
    }

    # Atlassian MCP first (org policy); the direct REST call stays as the fallback
    data = None
    result["via"] = "REST"
    if atlassian_mcp.enabled():
        try:
            data = atlassian_mcp.search_jira(jql, body["fields"], body["maxResults"])
            result["via"] = "MCP"
        except Exception as exc:
            log.warning("Jira via MCP failed (%s) — falling back to REST", exc)

    if data is None:
        try:
            headers = {**_auth_header(), "Content-Type": "application/json"}
            resp = httpx.post(
                f"{JIRA_BASE_URL}/rest/api/3/search/jql",
                json=body,
                headers=headers,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            result["error"] = str(exc)
            return result

    issues = data.get("issues", [])
    result["total_open"] = len(issues)

    for issue in issues:
        f           = issue["fields"]
        updated_str = f.get("updated", "")
        hours_stale = _hours_since(updated_str) if updated_str else 9999
        sla         = _sla_status(hours_stale, warn_h, esc_h)

        ticket = {
            "key":         issue["key"],
            "summary":     f.get("summary", ""),
            "status":      (f.get("status")    or {}).get("name", ""),   # null in some projects
            "priority":    (f.get("priority")  or {}).get("name", ""),
            "assignee":    (f.get("assignee")  or {}).get("displayName", "Unassigned"),
            "reporter":    (f.get("reporter")  or {}).get("displayName", "Unknown"),
            "updated":     updated_str,
            "hours_stale": round(hours_stale, 1),
            "sla_status":  sla,
            "labels":      f.get("labels", []),
            "url":         f"{JIRA_BASE_URL}/browse/{issue['key']}",
        }
        result["open_tickets"].append(ticket)

        if sla == "BREACH_72H":
            result["sla_breaches"].append(ticket)
        elif sla == "WARNING_48H":
            result["sla_warnings"].append(ticket)

    return result


if __name__ == "__main__":
    import pprint
    # Simulate lalit's skill profile
    mock_skill = {
        "user":                     "lalit.patkar@tomtom.com",
        "databricks_feature":       "RMLanes",
        "databricks_process_types": None,
    }
    result = run(mock_skill)
    print(f"JQL: {result['jql']}\n")
    print(f"Tickets found: {result['total_open']}")
    pprint.pprint(result)
