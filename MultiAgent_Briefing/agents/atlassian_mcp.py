"""
Atlassian reads through the TomTom MCP registry (org policy: use the registered MCP servers for
Jira / Confluence), via registry_mcp.py.

One MCP session is opened on first use and shared by the whole run (all profiles, all threads).
Only read tools are allowed. Results come back in the shape of the Jira / Confluence REST
responses the agents already parse, so callers keep their REST code as the fallback:

    if atlassian_mcp.enabled():
        try:
            data = atlassian_mcp.search_jira(jql, fields, 100)
        except Exception:
            data = None          # → existing REST call

MCP is skipped for the rest of the run after a failed start (e.g. no VPN — the registry is on
the TomTom network) and can be switched off with ATLASSIAN_VIA_MCP=0. Needs ATL_EMAIL and a
scoped ATL_TOKEN in .env.
"""
import asyncio
import atexit
import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import JIRA_BASE_URL  # noqa: E402  (also loads .env)

log = logging.getLogger("atlassian_mcp")

CLOUD_ID = JIRA_BASE_URL
_START_TIMEOUT = 60
_CALL_TIMEOUT = 60

_lock = threading.Lock()
_state: dict[str, Any] = {"loop": None, "rt": None, "failed": None}
_user_names: dict[str, str] = {}


class MCPError(RuntimeError):
    pass


def enabled() -> bool:
    """MCP is on unless switched off, the scoped token is missing, or it already failed this run."""
    if os.getenv("ATLASSIAN_VIA_MCP", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    if not (os.getenv("ATL_EMAIL", "").strip() and os.getenv("ATL_TOKEN", "").strip()) and not os.getenv("MCP_AUTH"):
        return False
    return _state["failed"] is None


def _session():
    """The shared RegistryTools session, started on first use (thread-safe)."""
    with _lock:
        if _state["failed"] is not None:
            raise MCPError(_state["failed"])
        if _state["rt"] is not None:
            return _state["rt"], _state["loop"]
        try:
            import registry_mcp

            loop = asyncio.new_event_loop()
            threading.Thread(target=loop.run_forever, name="atlassian-mcp", daemon=True).start()

            async def _enter():
                rt = registry_mcp.RegistryTools()
                await rt.__aenter__()
                return rt

            rt = asyncio.run_coroutine_threadsafe(_enter(), loop).result(timeout=_START_TIMEOUT)
            if not rt.tools:
                raise MCPError("registry returned no Atlassian tools (is the VPN connected?)")
            _state["rt"], _state["loop"] = rt, loop
            atexit.register(_close)
            log.info("Atlassian MCP ready: %d tools", len(rt.tools))
            return rt, loop
        except Exception as exc:
            _state["failed"] = f"{type(exc).__name__}: {exc}"
            log.warning("Atlassian MCP unavailable — using direct REST for this run (%s)", _state["failed"])
            raise MCPError(_state["failed"]) from exc


def _close():
    rt, loop = _state.get("rt"), _state.get("loop")
    # the session's polite DELETE at interpreter exit can race the shutdown; it is harmless
    logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)
    if rt is not None and loop is not None:
        try:
            asyncio.run_coroutine_threadsafe(rt.__aexit__(None, None, None), loop).result(timeout=10)
        except Exception:
            pass


def call(tool: str, args: dict) -> dict:
    """Run one read tool and return its parsed JSON payload (the 'data' part when present)."""
    rt, loop = _session()
    if rt.is_write(tool):
        raise MCPError(f"'{tool}' is a write tool — not allowed here")
    text = asyncio.run_coroutine_threadsafe(rt.call(tool, args), loop).result(timeout=_CALL_TIMEOUT)
    if text.startswith("ERROR"):
        raise MCPError(text[:300])
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MCPError(f"{tool}: response is not JSON ({text[:120]!r})") from exc
    if isinstance(payload, dict) and payload.get("error"):
        raise MCPError(f"{tool}: {payload.get('statusCode', '')} {payload.get('message', '')}"[:300])
    return payload.get("data", payload) if isinstance(payload, dict) else payload


# ── Jira ──────────────────────────────────────────────────────────────────────

def search_jira(jql: str, fields: list[str], max_results: int = 100) -> dict:
    """Same result as POST /rest/api/3/search/jql: {"issues": [{"key", "fields": {...}}, ...]}."""
    issues: list[dict] = []
    token = None
    while len(issues) < max_results:
        args = {"cloudId": CLOUD_ID, "jql": jql, "fields": fields, "view": "full",
                "maxResults": min(100, max_results - len(issues))}
        if token:
            args["nextPageToken"] = token
        data = call("searchJiraIssuesUsingJql", args)
        issues += data.get("issues") or []
        token = data.get("nextPageToken")
        if data.get("isLast", True) or not token:
            break
    return {"issues": issues[:max_results]}


def _user_name(account_id: str) -> str:
    if not account_id:
        return ""
    if account_id not in _user_names:
        try:
            u = call("executeRead", {"name": "getJiraUser", "cloudId": CLOUD_ID, "inputs": {"accountId": account_id}})
            _user_names[account_id] = (u or {}).get("displayName", "") if isinstance(u, dict) else ""
        except Exception as exc:
            log.debug("user lookup %s failed: %s", account_id, exc)
            _user_names[account_id] = ""
    return _user_names[account_id]


# ── Confluence ────────────────────────────────────────────────────────────────

_space_keys: dict[str, str] = {}


def _space_key(space_id: str) -> str:
    """Space key (e.g. MSO) for page links; '' when unknown (then a key-less link is used)."""
    if not space_id:
        return ""
    if space_id not in _space_keys:
        try:
            _space_keys[space_id] = call("executeRead", {"name": "getConfluenceSpace", "cloudId": CLOUD_ID,
                                                         "inputs": {"spaceIdOrKey": str(space_id)}}).get("key", "")
        except Exception as exc:
            log.debug("space lookup %s failed: %s", space_id, exc)
            _space_keys[space_id] = ""
    return _space_keys[space_id]


def get_confluence_page(page_id: str) -> dict:
    """
    Same fields as GET /wiki/rest/api/content/{id}?expand=body.storage,version,space that
    confluence_agent reads: title, space.key, version.when, version.by.displayName and the body
    (HTML here, not storage XHTML — the same text comes out of storage_to_text).
    '_page_url' is a key-less link used only if the space lookup fails.
    """
    d = call("getConfluenceContent", {"cloudId": CLOUD_ID, "content_id": str(page_id),
                                      "detail": "full", "content_format": "html"})
    meta = d.get("metadata") or {}
    version = meta.get("version") or {}
    # metadata.authorId is the page's creator; the latest version's author is who last edited it
    editor = ""
    try:
        latest = (call("executeRead", {"name": "listConfluenceContentVersions", "cloudId": CLOUD_ID,
                                       "inputs": {"contentId": str(page_id), "limit": 1}}).get("results") or [{}])[0]
        editor = latest.get("authorId", "")
    except Exception as exc:
        log.debug("version history %s failed: %s", page_id, exc)
    return {
        "title":   d.get("title", ""),
        "space":   {"key": _space_key(d.get("spaceId", ""))},
        "version": {"when": version.get("createdAt", ""), "number": version.get("number"),
                    "by": {"displayName": _user_name(editor)}},
        "body":    {"storage": {"value": (d.get("body") or {}).get("value", "")}},
        "_page_url": f"{JIRA_BASE_URL}/wiki/pages/viewpage.action?pageId={page_id}",
    }
