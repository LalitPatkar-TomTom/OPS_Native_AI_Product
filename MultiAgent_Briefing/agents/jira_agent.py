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


def _auth_header() -> dict:
    creds = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    token = base64.b64encode(creds.encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def _hours_since(updated_str: str) -> float:
    dt  = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - dt).total_seconds() / 3600


def _sla_status(hours: float) -> str:
    if hours >= SLA_ESCALATION_HOURS: return "BREACH_72H"
    if hours >= SLA_WARNING_HOURS:    return "WARNING_48H"
    return "OK"


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
            kw_clauses.append(f'text ~ "{variant}"')

    if isinstance(process_types, str):
        process_types = [process_types]
    for pt in process_types:
        kw_clauses.append(f'text ~ "{pt}"')

    # ── Identity conditions (reporter or assignee) ─────────────────────────────
    id_clauses = [
        f'reporter = "{user_email}"',
        f'assignee = "{user_email}"',
    ]

    all_clauses = kw_clauses + id_clauses
    scope_expr  = " OR ".join(all_clauses)
    label       = f"project:{project_key} | feature:{feature or 'none'} | reporter/assignee:{user_email}"

    jql = (
        f"project = {project_key} "
        f"AND statusCategory != Done "
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
    result: dict[str, Any] = {
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
        sla         = _sla_status(hours_stale)

        ticket = {
            "key":         issue["key"],
            "summary":     f.get("summary", ""),
            "status":      f.get("status", {}).get("name", ""),
            "priority":    f.get("priority", {}).get("name", ""),
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
