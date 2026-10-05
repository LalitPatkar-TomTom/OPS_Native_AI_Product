"""
OPS Native AI — Onboarding Server

Handles:
  - Per-user OAuth consent for Microsoft (Mail + Teams + Calendar) and Slack
  - Token storage (one JSON file per user per provider in tokens/)
  - Auth status endpoint polled by UserOnboarding.HTML
  - Skill profile upload + LLM-powered merge (personal + domain → combined)
  - File watcher on skills/uploads/ for drop-in skill.md delivery

Run:
    cd Onboarding_Server
    pip install -r requirements.txt
    uvicorn server:app --port 8000 --reload

The UserOnboarding.HTML form (../AI Architecture/HighLevelDocs/UserOnboarding.HTML)
opens OAuth popups and uploads skill.md files pointing to this server.
"""
import logging
import secrets
import urllib.parse
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from azure.identity import ClientSecretCredential, DefaultAzureCredential

import merge_skills
import token_store
from config import Settings
from watcher import SkillWatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

settings = Settings()
token_store.init(settings.tokens_dir)

_uploads_dir  = Path(settings.skills_uploads_dir)
_combined_dir = Path(settings.skills_combined_dir)
_domains_dir  = Path(settings.skills_domains_dir)


def _build_credential(s: Settings):
    if s.databricks_client_id and s.databricks_client_secret:
        logger.info("Databricks auth: Service Principal (%s)", s.databricks_client_id)
        return ClientSecretCredential(
            tenant_id=s.databricks_azure_tenant_id,
            client_id=s.databricks_client_id,
            client_secret=s.databricks_client_secret,
        )
    logger.info("Databricks auth: DefaultAzureCredential (az login / Managed Identity)")
    return DefaultAzureCredential()


_credential = _build_credential(settings)
if settings.databricks_pat_token:
    logger.info("Databricks LLM auth: PAT token configured — will use for skill merges")
elif settings.databricks_host:
    logger.info("Databricks LLM auth: Azure credential — will use for skill merges")
else:
    logger.warning("DATABRICKS_HOST not set — skill merges will use concatenation fallback")

# ── Lifespan — start/stop file watcher ───────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    watcher = SkillWatcher(
        uploads_dir=_uploads_dir,
        domains_dir=_domains_dir,
        combined_dir=_combined_dir,
        settings=settings,
        credential=_credential,
    )
    watcher.start()
    yield
    watcher.stop()


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OPS Native AI — Onboarding Server",
    description="Handles per-user OAuth consent and skill profile merging.",
    lifespan=lifespan,
)

# Allow requests from the onboarding HTML opened as file:// or from localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # file:// has null origin — wildcard required
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# In-memory state store for CSRF tokens (email → state string)
_oauth_states: dict[str, str] = {}

# ── Microsoft Graph scopes (covers Mail + Teams chats + Calendar) ─────────────
_MS_SCOPES = " ".join([
    "Mail.Read",
    "Chat.Read",
    "Calendars.Read",
    "offline_access",   # gives refresh_token → one-time auth only
    "openid",
    "profile",
    "User.Read",
])

# ── Slack user-level scopes ───────────────────────────────────────────────────
_SLACK_USER_SCOPES = "channels:history,groups:history,im:history,channels:read,users:read"


# ── Shared result page shown in the OAuth popup ───────────────────────────────

def _result_page(success: bool, provider: str, message: str) -> HTMLResponse:
    icon    = "✅" if success else "❌"
    color   = "#059669" if success else "#dc2626"
    heading = "Connected!" if success else "Connection Failed"
    js_ok   = "true" if success else "false"
    html = f"""<!DOCTYPE html><html><head>
<meta charset="UTF-8">
<title>OPS Hub — Connect Account</title>
<style>
  body  {{ font-family:'Segoe UI',sans-serif; display:flex; align-items:center;
           justify-content:center; min-height:100vh; margin:0; background:#f8fafc; }}
  .box  {{ background:#fff; border-radius:12px; padding:40px 48px; text-align:center;
           box-shadow:0 4px 24px rgba(0,0,0,.10); max-width:420px; }}
  .icon {{ font-size:48px; margin-bottom:16px; }}
  h2   {{ color:{color}; margin:0 0 10px; font-size:20px; }}
  p    {{ color:#64748b; font-size:14px; line-height:1.6; }}
  .sub {{ margin-top:24px; font-size:12px; color:#94a3b8; }}
</style>
<script>
  // Notify the parent window (UserOnboarding.HTML) and close the popup
  setTimeout(function() {{
    if (window.opener) {{
      window.opener.postMessage(
        {{ type: 'auth_complete', provider: '{provider}', success: {js_ok} }}, '*'
      );
      window.close();
    }}
  }}, 1800);
</script>
</head><body>
<div class="box">
  <div class="icon">{icon}</div>
  <h2>{heading}</h2>
  <p>{message}</p>
  <p class="sub">This window will close automatically…</p>
</div>
</body></html>"""
    return HTMLResponse(content=html)


# ════════════════════════════════ HEALTH ═════════════════════════════════════

@app.get("/")
def health():
    return {"service": "OPS Native AI — Onboarding Server", "status": "running"}


# ════════════════════════════════ MICROSOFT ══════════════════════════════════

@app.get("/auth/microsoft")
def microsoft_initiate(email: str, request: Request):
    """Redirect user to Microsoft login page."""
    if not settings.graph_client_id:
        raise HTTPException(400, "GRAPH_CLIENT_ID not set in .env — see .env.example")

    state = f"{email}|{secrets.token_urlsafe(16)}"
    _oauth_states[state] = email

    params = {
        "client_id":     settings.graph_client_id,
        "response_type": "code",
        "redirect_uri":  settings.graph_redirect_uri,
        "scope":         _MS_SCOPES,
        "state":         state,
        "prompt":        "select_account",
    }
    url = (
        f"https://login.microsoftonline.com/{settings.graph_tenant_id}"
        f"/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"
    )
    return RedirectResponse(url)


@app.get("/auth/microsoft/callback")
async def microsoft_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None,
):
    """Exchange authorisation code for tokens and store them."""
    if error or not code or not state:
        msg = error_description or error or "No authorisation code received."
        return _result_page(False, "microsoft", msg)

    email = _oauth_states.pop(state, None) or (state.split("|")[0] if "|" in state else None)
    if not email:
        return _result_page(False, "microsoft", "Invalid state — please try connecting again.")

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"https://login.microsoftonline.com/{settings.graph_tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  settings.graph_redirect_uri,
                "client_id":     settings.graph_client_id,
                "client_secret": settings.graph_client_secret,
                "scope":         _MS_SCOPES,
            },
        )

    if resp.status_code != 200:
        logger.error("Microsoft token exchange failed: %s", resp.text)
        return _result_page(False, "microsoft", "Token exchange failed — check app credentials.")

    data = resp.json()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
    ).isoformat()

    token_store.save(email, "microsoft", {
        "access_token":  data.get("access_token"),
        "refresh_token": data.get("refresh_token"),   # used for silent daily refresh
        "expires_at":    expires_at,
        "scopes":        data.get("scope", ""),
        "email":         email,
    })

    return _result_page(
        True, "microsoft",
        f"Microsoft connected for <strong>{email}</strong>.<br>"
        "The agent can now read your <strong>Mail</strong>, "
        "<strong>Teams messages</strong>, and <strong>Calendar</strong>.",
    )


# ════════════════════════════════ SLACK ══════════════════════════════════════

@app.get("/auth/slack")
def slack_initiate(email: str):
    """Redirect user to Slack OAuth page."""
    if not settings.slack_oauth_client_id:
        raise HTTPException(400, "SLACK_OAUTH_CLIENT_ID not set in .env — see .env.example")

    state = f"{email}|{secrets.token_urlsafe(16)}"
    _oauth_states[state] = email

    params = {
        "client_id":    settings.slack_oauth_client_id,
        "user_scope":   _SLACK_USER_SCOPES,
        "redirect_uri": settings.slack_redirect_uri,
        "state":        state,
    }
    url = f"https://slack.com/oauth/v2/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@app.get("/auth/slack/callback")
async def slack_callback(
    code: str = None,
    state: str = None,
    error: str = None,
):
    """Exchange Slack code for user token and store it."""
    if error or not code or not state:
        return _result_page(False, "slack", f"Slack error: {error or 'No code received'}")

    email = _oauth_states.pop(state, None) or (state.split("|")[0] if "|" in state else None)
    if not email:
        return _result_page(False, "slack", "Invalid state — please try connecting again.")

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "code":          code,
                "redirect_uri":  settings.slack_redirect_uri,
                "client_id":     settings.slack_oauth_client_id,
                "client_secret": settings.slack_oauth_client_secret,
            },
        )

    data = resp.json()
    if not data.get("ok"):
        logger.error("Slack token exchange failed: %s", data)
        return _result_page(False, "slack", f"Slack error: {data.get('error', 'unknown')}")

    authed_user = data.get("authed_user") or {}
    team_name   = (data.get("team") or {}).get("name", "Slack")

    token_store.save(email, "slack", {
        "access_token":  authed_user.get("access_token"),
        "slack_user_id": authed_user.get("id"),
        "team_id":       (data.get("team") or {}).get("id"),
        "team_name":     team_name,
        "scopes":        authed_user.get("scope", ""),
        "email":         email,
    })

    return _result_page(
        True, "slack",
        f"Slack connected for <strong>{email}</strong> ({team_name}).<br>"
        "The agent can now read your channels and direct messages.",
    )


# ════════════════════════════════ STATUS / DISCONNECT ════════════════════════

@app.get("/auth/status")
def auth_status(email: str):
    """Return connection status for all providers for a given user."""
    return token_store.status(email)


@app.delete("/auth/disconnect")
def disconnect(email: str, provider: str):
    """Revoke a user's stored token for a provider."""
    if provider not in ("microsoft", "slack"):
        raise HTTPException(400, "provider must be 'microsoft' or 'slack'")
    token_store.delete(email, provider)
    return {"email": email, "provider": provider, "disconnected": True}


# ════════════════════════════════ SKILL UPLOAD & MERGE ══════════════════════

@app.post("/skills/upload")
async def upload_skill(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Upload a personal skill.md produced by the onboarding form.

    The file is saved to skills/uploads/ and an LLM merge is triggered in the
    background. The combined output appears in skills/combined/ when done
    (typically 15–60 s depending on model latency).

    Expected filename format: {firstname.lastname}_skill.md
    """
    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(400, "Only .md files accepted")

    dest = _uploads_dir / file.filename
    _uploads_dir.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    dest.write_bytes(content)
    logger.info("Skill upload saved: %s (%d bytes)", file.filename, len(content))

    background_tasks.add_task(
        _run_merge,
        dest,
    )
    return {
        "status": "accepted",
        "filename": file.filename,
        "message": "Skill profile received. LLM merge started — combined file ready in ~30 s.",
    }


def _run_merge(upload_path: Path) -> None:
    try:
        merge_skills.merge(
            user_skill_path=upload_path,
            domains_dir=_domains_dir,
            combined_dir=_combined_dir,
            databricks_host=settings.databricks_host,
            databricks_pat_token=settings.databricks_pat_token,
            databricks_llm_model=settings.databricks_llm_model,
            credential=_credential,
        )
    except Exception:
        logger.exception("Background merge failed for: %s", upload_path.name)


@app.get("/skills/status")
def skills_status():
    """
    List all skill profiles: upload timestamp, merge status, combined file availability.
    """
    uploads  = {p.stem: p for p in _uploads_dir.glob("*.md")} if _uploads_dir.exists() else {}
    combined = {p.stem: p for p in _combined_dir.glob("*.md")} if _combined_dir.exists() else {}

    result = []
    for stem, up in sorted(uploads.items()):
        co = combined.get(stem)
        result.append({
            "filename":       up.name,
            "uploaded_at":    datetime.fromtimestamp(up.stat().st_mtime).isoformat(),
            "merged":         co is not None,
            "merged_at":      datetime.fromtimestamp(co.stat().st_mtime).isoformat() if co else None,
            "stale":          co is not None and up.stat().st_mtime > co.stat().st_mtime,
        })
    return {"profiles": result, "total": len(result)}


@app.get("/skills/combined/{filename}")
def download_combined(filename: str):
    """Download a merged skill.md file by name."""
    if not filename.endswith(".md"):
        raise HTTPException(400, "filename must end with .md")
    path = _combined_dir / filename
    if not path.exists():
        raise HTTPException(404, f"Combined profile not found: {filename}. Upload and wait ~30 s for merge.")
    return FileResponse(
        path=str(path),
        media_type="text/markdown",
        filename=filename,
    )


# ════════════════════════════════ ANALYTICS SCOPE ════════════════════════════

_DATABRICKS_RESOURCE = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"


def _get_databricks_token() -> str:
    if settings.databricks_pat_token:
        return settings.databricks_pat_token
    try:
        tok = _credential.get_token(f"{_DATABRICKS_RESOURCE}/.default")
        return tok.token
    except Exception:
        return ""


@app.get("/analytics/scope-options")
async def scope_options():
    """
    Return distinct processType and planningid values from Databricks.
    Used by the onboarding form to populate the scope multi-select dropdowns.
    """
    if not settings.databricks_host or not settings.databricks_sql_warehouse_id:
        return JSONResponse({"process_types": [], "planning_ids": [], "note": "Databricks SQL not configured"})

    token = _get_databricks_token()
    if not token:
        return JSONResponse({"process_types": [], "planning_ids": [], "note": "No Databricks auth available"})

    table = settings.databricks_combined_table
    results: dict = {"process_types": [], "planning_ids": []}

    for col, key in [("processType", "process_types"), ("planningid", "planning_ids")]:
        sql = (
            f"SELECT DISTINCT {col} FROM {table} "
            f"WHERE {col} IS NOT NULL AND {col} != '' "
            f"ORDER BY {col} LIMIT 300"
        )
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.databricks_host.rstrip('/')}/api/2.0/sql/statements",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "warehouse_id": settings.databricks_sql_warehouse_id,
                        "statement": sql,
                        "wait_timeout": "25s",
                        "disposition": "INLINE",
                        "format": "JSON_ARRAY",
                    },
                )
            data = resp.json()
            if data.get("status", {}).get("state") == "SUCCEEDED":
                rows = data.get("result", {}).get("data_array") or []
                results[key] = [r[0] for r in rows if r and r[0]]
            else:
                logger.warning("scope-options query for %s returned state: %s", col, data.get("status"))
        except Exception as exc:
            logger.warning("scope-options fetch failed for %s: %s", col, exc)

    return JSONResponse(results)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=settings.port, reload=True)
