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

# Why the project is checked (2 Nov 2026): Jira REST search answers 200 with 0 tickets for a project key that
# does not exist or that the engine's Jira account cannot see, so profiles with a wrong key (Geocoding, GDN, QA,
# LMDF) got "Jira SLA: All clear" every day. The check follows the run's own route: the MCP search already fails
# with "does not exist for the field 'project'" (no REST fallback then); before a REST search the project is
# looked up with the same account. The MCP identity sees projects the REST account does not (e.g. DPOT), so a
# REST-only check would wrongly flag profiles that the MCP reads fine.
PROJECT_GONE = "does not exist for the field 'project'"

# REST lookups this run: key -> True when Jira answered 404 (one lookup per key per run)
_missing_projects: dict[str, bool] = {}


def _not_found(key: str) -> str:
    """The error text used everywhere for a project key that Jira cannot find."""
    return (f"Jira project '{key}' not found or not visible to the OPS AI Jira account — "
            f"check the Jira project key in your profile (OPS Hub → My profile)")


def project_missing(key: str) -> bool:
    """True only when Jira answers 404 for GET /rest/api/3/project/{key} with the REST account (read-only).
    Any other answer (200, 401, network error) returns False, so an outage is reported by the search itself."""
    if key not in _missing_projects:
        try:
            r = httpx.get(f"{JIRA_BASE_URL}/rest/api/3/project/{key}", headers=_auth_header(), timeout=15)
            _missing_projects[key] = r.status_code == 404
        except Exception as exc:
            log.debug("project lookup %s failed: %s", key, exc)
            _missing_projects[key] = False
    return _missing_projects[key]


def _auth_header() -> dict:
    creds = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    token = base64.b64encode(creds.encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def _hours_since(updated_str: str) -> float:
    dt  = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - dt).total_seconds() / 3600


# OSI-003: without a window the query returned every open ticket ever created (some from 2021).
JIRA_MAX_TICKETS = 1000   # open tickets read per profile (MCP and REST both page, 100 per call)
DEFAULT_JIRA_WINDOW_DAYS = 365


def sla_levels(skill: dict | None) -> tuple[float, float]:
    """(warning, escalation) hours from the profile (OSI-006); the config defaults when not set."""
    t = (skill or {}).get("sla_thresholds") or {}
    return (t.get("warning_hours") or SLA_WARNING_HOURS, t.get("escalation_hours") or SLA_ESCALATION_HOURS)


def _sla_status(hours: float, warn: float = SLA_WARNING_HOURS, esc: float = SLA_ESCALATION_HOURS) -> str:
    # The status names stay BREACH_72H / WARNING_48H (used across the emails and analytics);
    # the hours behind them now come from each profile.
    """BREACH_72H / WARNING_48H / OK for a ticket's hours without an update, by the profile's levels."""
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
    r"""Escape a value for a double-quoted JQL string (a stray \ or " would break the query)."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _profile_keys(skill: dict | None) -> list[str]:
    """The profile's Jira keys in order (OSI-061: every key of the Active projects); config JIRA_PROJECT is a
    last-resort fallback when the profile names none."""
    from skill_registry import jira_keys
    return jira_keys(skill) or ([JIRA_PROJECT] if JIRA_PROJECT else [])


def _project_clause(keys: list[str]) -> str:
    """`project = OM` for one key (the JQL every single-key profile has always run, unchanged), `project in
    (OM, MCPET)` for several: one search, so the SLA lists and counts cover all of the user's projects."""
    return f"project = {keys[0]}" if len(keys) == 1 else f"project in ({', '.join(keys)})"


def _build_jql(skill: dict | None, keys: list[str] | None = None) -> tuple[str, str]:
    """
    Build a JQL string scoped to tickets relevant to the user.

    keys: the Jira projects to search (default: every key in the profile); run() passes only the keys Jira
    can find, so one wrong key does not stop the others from being checked.
    Returns (jql_string, human_label).
    """
    _skill        = skill or {}
    user_email    = _skill.get("user", JIRA_EMAIL)
    feature       = _skill.get("databricks_feature", "")
    process_types = _skill.get("databricks_process_types") or []
    keys          = keys or _profile_keys(_skill)
    project_key   = ", ".join(keys)

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
        f"{_project_clause(keys)} "
        f"AND statusCategory != Done "
        f"{window_clause}"
        f"AND ({scope_expr}) "
        f"ORDER BY updated ASC"
    )
    return jql, label


def project_status(key: str) -> str:
    """"ok", "missing" or "unknown" for a Jira project key, by the same route as run(): MCP first, then REST.
    Used by the profile check's daily reminder, so a reminder goes out only when the run itself cannot read
    the project. "unknown" (Jira down) never triggers a reminder."""
    if atlassian_mcp.enabled():
        try:
            atlassian_mcp.search_jira(f"project = {key}", ["key"], 1)
            return "ok"
        except Exception as exc:
            if PROJECT_GONE in str(exc):
                return "missing"
            log.debug("MCP project check %s failed, trying REST: %s", key, exc)
    try:
        r = httpx.get(f"{JIRA_BASE_URL}/rest/api/3/project/{key}", headers=_auth_header(), timeout=15)
    except Exception:
        return "unknown"
    return {200: "ok", 404: "missing"}.get(r.status_code, "unknown")


def run(skill: dict | None = None) -> dict[str, Any]:
    """
    Fetch relevant MCPET tickets for the given user skill profile.

    Args:
        skill: parsed skill dict from skill_registry.load_skill().
               Drives keyword and identity filtering in JQL.
               Pass None to return all open MCPET tickets (no scope).
    """
    keys = _profile_keys(skill)
    missing: list[str] = []
    if len(keys) > 1 and JIRA_API_TOKEN:
        # OSI-061: with several keys, a wrong one must not stop the others (one search over all of them would
        # fail on the wrong key, MCP, or quietly return 0 tickets for it, REST). Each key is looked up first by
        # the run's own route; "unknown" (Jira down) is kept, so an outage is reported by the search itself.
        missing = [k for k in keys if project_status(k) == "missing"]
        if missing:
            log.warning("Jira project(s) %s not found — checked without them: %s",
                        ", ".join(missing), ", ".join(k for k in keys if k not in missing) or "none")
    found = [k for k in keys if k not in missing] or keys
    jql, jql_label = _build_jql(skill, found)

    jira_project = ", ".join(found)
    warn_h, esc_h = sla_levels(skill)
    result: dict[str, Any] = {
        "sla_warning_hours":    warn_h,
        "sla_escalation_hours": esc_h,
        "created_window":       created_window(skill)[1],
        "open_tickets": [],
        "sla_breaches": [],
        "sla_warnings": [],
        "unassigned":   [],          # OSI-056: open tickets with no assignee, listed apart from the SLA
        "total_open":   0,
        "jql":          jql,
        "source":       f"Jira {jira_project}",
        "as_of":        datetime.now(timezone.utc).isoformat(),
        "error":        None,
    }
    if missing:
        result["missing_keys"] = missing
        if len(missing) == len(keys):
            # every key is wrong: the same "not found — SLA not checked" as a single wrong key
            result["source"] = f"Jira {', '.join(keys)}"
            result.update(error=_not_found(", ".join(keys)), project_not_found=True)
            log.warning("Jira projects %s not found — SLA not checked", ", ".join(keys))
            return result
        result["key_warning"] = (f"Jira project {', '.join(missing)} not found or not visible to the OPS AI Jira "
                                 f"account, so it is not checked; {jira_project} "
                                 f"{'is' if len(found) == 1 else 'are'} checked. Check the Jira key in your "
                                 f"profile (OPS Hub → My profile).")

    if not JIRA_API_TOKEN:
        result["error"] = "JIRA_API_TOKEN not set — add to OPS_Native_AI/.env"
        return result


    body = {
        "jql":        jql,
        "maxResults": 100,          # page size; up to JIRA_MAX_TICKETS in total (27 Oct: one scope had exactly 100)
        "fields":     ["summary", "status", "priority", "assignee", "reporter",
                       "updated", "created", "issuetype", "labels", "components"],
    }

    # Atlassian MCP first (org policy); the direct REST call stays as the fallback
    data = None
    result["via"] = "REST"
    if atlassian_mcp.enabled():
        try:
            data = atlassian_mcp.search_jira(jql, body["fields"], JIRA_MAX_TICKETS)
            result["via"] = "MCP"
        except Exception as exc:
            if PROJECT_GONE in str(exc):
                # the project does not exist for Jira: REST would answer 0 tickets, so do not fall back
                result.update(error=_not_found(jira_project), project_not_found=True)
                log.warning("Jira project %s not found (MCP) — SLA not checked", jira_project)
                return result
            log.warning("Jira via MCP failed (%s) — falling back to REST", exc)

    # several keys were each looked up above; the REST lookup takes one key
    if data is None and len(found) == 1 and project_missing(jira_project):
        # 404 also means "no permission": QADEV exists but the REST account cannot see it
        result.update(error=_not_found(jira_project), project_not_found=True)
        log.warning("Jira project %s not found (REST) — SLA not checked", jira_project)
        return result

    if data is None:
        try:
            headers = {**_auth_header(), "Content-Type": "application/json"}
            issues, token = [], None
            while len(issues) < JIRA_MAX_TICKETS:
                page = {**body, **({"nextPageToken": token} if token else {})}
                resp = httpx.post(f"{JIRA_BASE_URL}/rest/api/3/search/jql", json=page, headers=headers, timeout=20)
                resp.raise_for_status()
                chunk = resp.json()
                issues += chunk.get("issues") or []
                token = chunk.get("nextPageToken")
                if chunk.get("isLast", True) or not token:
                    break
            data = {"issues": issues[:JIRA_MAX_TICKETS]}
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
        if not f.get("assignee"):
            created = f.get("created") or ""
            result["unassigned"].append({**ticket, "created": created,
                                         "age_days": round(_hours_since(created) / 24) if created else None})

    # OSI-056 (part, 6 Nov 2026): tickets nobody owns, oldest first. Listed apart, never counted as SLA
    # breaches. "Not linked" (the other half of OSI-056) waits for the reporter to say what "linked" means.
    result["unassigned"].sort(key=lambda t: t["created"] or "9999")
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
