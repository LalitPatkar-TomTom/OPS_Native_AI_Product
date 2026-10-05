"""
Confluence Agent — reads configured Confluence pages for daily briefing context.

Scope (Phase 1, read-only):
  - Fetches page content via Confluence REST API
  - Extracts update status, text excerpt, and any metric tables
  - Flags if the weekly progress page hasn't been updated recently

Data sources driven by skill.md:
  - confluence_pages: list of {space, page_id} dicts parsed from skill.md

No personal space (email/Teams/Slack) access — strictly Confluence only.
"""
import base64
import re
import sys
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN

log = logging.getLogger("confluence_agent")

CONFLUENCE_BASE = JIRA_BASE_URL   # same Atlassian domain
CONFLUENCE_API  = f"{CONFLUENCE_BASE}/wiki/rest/api"


def _auth_header() -> dict:
    creds = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    token = base64.b64encode(creds.encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def _days_since(iso_str: str) -> float:
    """Return how many days ago an ISO timestamp was."""
    try:
        dt  = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - dt).total_seconds() / 86400
    except Exception:
        return 999.0


def _storage_to_plain(storage_html: str) -> str:
    """
    Lightweight conversion of Confluence storage XHTML to plain text.
    Uses confluence_fetch.storage_to_text if available, falls back to regex strip.
    """
    try:
        from agents.confluence_fetch import storage_to_text
        return storage_to_text(storage_html)
    except Exception:
        pass
    # Fallback: strip all HTML tags
    text = re.sub(r"<[^>]+>", " ", storage_html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_excerpt(plain_text: str, max_chars: int = 600) -> str:
    """Return the first meaningful lines of a page as an excerpt."""
    lines = [ln.strip() for ln in plain_text.splitlines() if ln.strip()]
    excerpt = ""
    for ln in lines:
        if len(excerpt) + len(ln) > max_chars:
            break
        excerpt += ln + " "
    return excerpt.strip()


def _extract_metric_table(plain_text: str) -> dict[str, Any]:
    """
    Best-effort extraction of numeric metrics from page text.
    Looks for FTA %, CoQ %, efficiency patterns.
    """
    metrics: dict[str, Any] = {}

    fta_m = re.search(r"FTA[^0-9]*(\d{1,3}(?:\.\d+)?)\s*%", plain_text, re.I)
    if fta_m:
        metrics["fta_mentioned"] = float(fta_m.group(1))

    coq_m = re.search(r"CoQ[^0-9]*(\d{1,3}(?:\.\d+)?)\s*%", plain_text, re.I)
    if coq_m:
        metrics["coq_mentioned"] = float(coq_m.group(1))

    eff_m = re.search(r"[Ee]fficiency[^0-9]*(\d{1,3}(?:\.\d+)?)\s*%", plain_text, re.I)
    if eff_m:
        metrics["efficiency_mentioned"] = float(eff_m.group(1))

    return metrics


def _fetch_page(page_id: str) -> dict[str, Any]:
    """Fetch one Confluence page and return a structured summary."""
    result: dict[str, Any] = {
        "page_id":         page_id,
        "page_title":      "",
        "page_url":        f"{CONFLUENCE_BASE}/wiki/spaces/pages/{page_id}",
        "last_updated":    "",
        "last_updated_by": "",
        "days_since_update": 999.0,
        "update_overdue":  False,
        "excerpt":         "",
        "metrics":         {},
        "error":           None,
    }

    if not JIRA_API_TOKEN:
        result["error"] = "JIRA_API_TOKEN not set — Confluence fetch skipped"
        return result

    try:
        url    = f"{CONFLUENCE_API}/content/{page_id}"
        params = {"expand": "body.storage,version,space,history.lastUpdated"}
        resp   = httpx.get(url, headers=_auth_header(), params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        result["error"] = str(exc)
        return result

    # Metadata
    result["page_title"] = data.get("title", "")
    space_key = (data.get("space") or {}).get("key", "")
    result["page_url"] = (
        f"{CONFLUENCE_BASE}/wiki/spaces/{space_key}/pages/{page_id}"
    )

    # Version / last update
    version = data.get("version") or {}
    last_updated = version.get("when", "")
    result["last_updated"] = last_updated
    result["last_updated_by"] = (
        (version.get("by") or {}).get("displayName", "")
        or (version.get("by") or {}).get("email", "")
    )

    if last_updated:
        days = _days_since(last_updated)
        result["days_since_update"] = round(days, 1)
        # Flag if not updated in the last 8 days (allows Friday → next Friday)
        result["update_overdue"] = days > 8

    # Content
    storage = (data.get("body") or {}).get("storage", {}).get("value", "")
    if storage:
        plain = _storage_to_plain(storage)
        result["excerpt"] = _extract_excerpt(plain)
        result["metrics"] = _extract_metric_table(plain)

    return result


def run(skill: dict | None = None) -> dict[str, Any]:
    """
    Fetch all Confluence pages configured in the skill profile.

    Args:
        skill: parsed skill dict from skill_registry.load_skill().
               Uses skill["confluence_pages"] list of {page_id, space} dicts.

    Returns:
        {
          "pages":      [list of page result dicts],
          "page_count": int,
          "overdue_pages": [titles of pages not updated this week],
          "source":     "Confluence",
          "as_of":      ISO timestamp,
          "error":      None | str,
        }
    """
    result: dict[str, Any] = {
        "pages":         [],
        "page_count":    0,
        "overdue_pages": [],
        "source":        "Confluence",
        "as_of":         datetime.now(timezone.utc).isoformat(),
        "error":         None,
    }

    confluence_pages = (skill or {}).get("confluence_pages") or []
    if not confluence_pages:
        result["error"] = "No Confluence pages configured in skill.md"
        return result

    for page_cfg in confluence_pages:
        page_id = str(page_cfg.get("page_id", ""))
        if not page_id:
            continue
        log.info(f"Fetching Confluence page {page_id} …")
        page_result = _fetch_page(page_id)
        result["pages"].append(page_result)
        if page_result.get("update_overdue"):
            result["overdue_pages"].append(page_result.get("page_title", page_id))
        if page_result.get("error"):
            log.warning(f"  Page {page_id}: {page_result['error']}")

    result["page_count"] = len(result["pages"])
    return result


if __name__ == "__main__":
    import pprint, json

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    mock_skill = {
        "user": "lalit.patkar@tomtom.com",
        "confluence_pages": [
            {"space": "MSO", "page_id": "2063630424"},
        ],
    }
    out = run(mock_skill)
    print(f"\nPages fetched: {out['page_count']}")
    print(f"Overdue:       {out['overdue_pages']}")
    pprint.pprint(out)
