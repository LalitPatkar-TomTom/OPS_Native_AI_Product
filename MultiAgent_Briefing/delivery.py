"""
Delivery — sends briefing output to the user.

Priority order:
  1. Email — EMAIL_TRANSPORT picks the route:
       outlook (default)  win32com, your logged-in Outlook on Windows
       graph              Microsoft Graph sendMail from the dedicated mailbox (MAIL_SENDER);
                          falls back to Outlook if Graph fails and Outlook is available
  2. Teams webhook  (set TEAMS_WEBHOOK_URL in .env when ready)
  3. File only      (always saved regardless)

EMAIL_CC=off sends to the profile owner only (no global or profile CCs).
Parallel run: EMAIL_PARALLEL_TO=<address> sends every email only to that address, without
CCs, with the intended recipients in the subject — for comparing a new setup with the live one.

The recipient email is read directly from the skill file —
it is the filename itself (lalit.patkar@tomtom.com_skill.md → lalit.patkar@tomtom.com).
No hardcoding, no separate config.
"""
import logging
import os
import re
from datetime import datetime
from pathlib import Path

# config.py already loaded the root .env at import time — no separate load needed here
log = logging.getLogger("delivery")

# Always CC'd on every email regardless of skill file settings
GLOBAL_CC = ["Ketki.Avachat@tomtom.com"]

# Every recipient must be exactly one TomTom address. The owner comes from the profile filename and
# Graph splits on ";", so without this check a crafted filename could add a second recipient.
_TOMTOM_ADDRESS = re.compile(r"^[A-Za-z0-9._%+-]+@tomtom\.com$", re.I)


def is_valid_recipient(address: str) -> bool:
    """True for a single @tomtom.com address (no separators, no display name)."""
    return bool(_TOMTOM_ADDRESS.match((address or "").strip()))


# ── 1. Outlook email (primary — Windows, no config needed) ────────────────────

def _send_outlook(
    to_email: str,
    subject: str,
    html_body: str,
    cc_emails: list[str] | None = None,
    attachment_path: str | None = None,
) -> bool:
    """
    Send via the locally running Outlook application using HTML formatting.
    Uses win32com — works as long as Outlook is installed and your account is signed in.
    Optional attachment_path: absolute path to a file to attach (e.g. a .docx report).
    """
    try:
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail         = outlook.CreateItem(0)   # 0 = olMailItem
        mail.To         = to_email
        if cc_emails:
            mail.CC = "; ".join(cc_emails)
        mail.Subject    = subject
        mail.BodyFormat = 2         # olFormatHTML — forces HTML rendering in Outlook
        mail.HTMLBody   = html_body
        if attachment_path:
            mail.Attachments.Add(attachment_path)
            log.info(f"Attachment added: {attachment_path}")
        mail.Send()
        cc_note = f" (CC: {', '.join(cc_emails)})" if cc_emails else ""
        log.info(f"Email sent via Outlook -> {to_email}{cc_note}")
        return True
    except ImportError:
        log.warning("pywin32 not available — Outlook delivery skipped")
        return False
    except Exception as exc:
        log.error(f"Outlook email failed: {exc}")
        return False


# ── 1b. Microsoft Graph (dedicated mailbox — works anywhere, e.g. the Azure job) ──

_graph_token: dict = {"value": "", "expires": 0.0}


def _graph_access_token() -> str:
    """Client-credentials token for Graph, cached until shortly before it expires."""
    import time
    import httpx
    if _graph_token["value"] and time.time() < _graph_token["expires"] - 300:
        return _graph_token["value"]
    tenant = os.getenv("MAIL_TENANT_ID", "").strip()
    r = httpx.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data={"grant_type": "client_credentials",
              "client_id": os.getenv("MAIL_CLIENT_ID", "").strip(),
              "client_secret": os.getenv("MAIL_CLIENT_SECRET", "").strip(),
              "scope": "https://graph.microsoft.com/.default"},
        timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"token request failed: HTTP {r.status_code} {r.json().get('error', '')}")
    body = r.json()
    _graph_token.update(value=body["access_token"], expires=time.time() + int(body.get("expires_in", 3600)))
    return _graph_token["value"]


def _send_graph(
    to_email: str,
    subject: str,
    html_body: str,
    cc_emails: list[str] | None = None,
    attachment_path: str | None = None,
) -> bool:
    """Send from MAIL_SENDER via Graph /users/{sender}/sendMail (copy kept in its Sent Items)."""
    sender = os.getenv("MAIL_SENDER", "").strip()
    if not (sender and os.getenv("MAIL_CLIENT_SECRET", "").strip()):
        log.warning("Graph mail not configured (MAIL_SENDER / MAIL_CLIENT_SECRET) — skipped")
        return False
    try:
        import base64
        import httpx
        message = {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            # one address, or several separated by ";" (e.g. the weekly analytics report)
            "toRecipients": [{"emailAddress": {"address": a.strip()}} for a in to_email.split(";") if a.strip()],
            "ccRecipients": [{"emailAddress": {"address": c}} for c in (cc_emails or [])],
        }
        reply_to = os.getenv("MAIL_REPLY_TO", "").strip()
        if reply_to:
            message["replyTo"] = [{"emailAddress": {"address": reply_to}}]
        if attachment_path:
            data = Path(attachment_path).read_bytes()
            message["attachments"] = [{
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": Path(attachment_path).name,
                "contentBytes": base64.b64encode(data).decode("ascii"),
            }]
            log.info(f"Attachment added: {attachment_path}")
        for attempt in (1, 2):
            r = httpx.post(f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail",
                           headers={"Authorization": f"Bearer {_graph_access_token()}"},
                           json={"message": message, "saveToSentItems": True}, timeout=60)
            if r.status_code == 202:
                cc_note = f" (CC: {', '.join(cc_emails)})" if cc_emails else ""
                log.info(f"Email sent via Graph -> {to_email}{cc_note}")
                return True
            if r.status_code in (429, 500, 502, 503, 504) and attempt == 1:
                import time
                time.sleep(int(r.headers.get("Retry-After", "10")))
                continue
            err = r.json().get("error", {}) if r.content else {}
            log.error(f"Graph email failed: HTTP {r.status_code} {err.get('code', '')}: {err.get('message', '')[:200]}")
            return False
    except Exception as exc:
        log.error(f"Graph email failed: {exc}")
    return False


def _send_email(to_email, subject, html_body, cc_emails=None, attachment_path=None) -> tuple[bool, str]:
    """Send by EMAIL_TRANSPORT; returns (sent_ok, transport used)."""
    if os.getenv("EMAIL_TRANSPORT", "outlook").strip().lower() == "graph":
        if _send_graph(to_email, subject, html_body, cc_emails, attachment_path):
            return True, "graph"
        if os.name != "nt":
            return False, "graph"
        log.warning("Falling back to Outlook for this email")
    return _send_outlook(to_email, subject, html_body, cc_emails, attachment_path), "outlook"


# ── 2. Teams webhook (secondary — set TEAMS_WEBHOOK_URL in .env) ──────────────

def _send_teams(subject: str, body: str) -> bool:
    """
    POST briefing to a Teams channel via Incoming Webhook or Workflows URL.
    Set TEAMS_WEBHOOK_URL in .env to activate. No-op if not set.
    """
    url = os.getenv("TEAMS_WEBHOOK_URL", "").strip()
    if not url:
        return False
    try:
        import httpx
        payload = {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {"type": "TextBlock", "text": subject,
                         "weight": "Bolder", "size": "Medium", "wrap": True},
                        {"type": "TextBlock",
                         "text": datetime.now().strftime("%d %b %Y - %H:%M IST"),
                         "isSubtle": True, "spacing": "None"},
                        {"type": "TextBlock",
                         "text": body[:3000] + ("..." if len(body) > 3000 else ""),
                         "wrap": True, "spacing": "Medium"},
                    ],
                },
            }],
        }
        r = httpx.post(url, json=payload, timeout=15)
        if r.status_code in (200, 202):
            log.info(f"Teams delivery OK ({r.status_code})")
            return True
        log.warning(f"Teams returned {r.status_code}: {r.text[:120]}")
        return False
    except Exception as exc:
        log.error(f"Teams delivery failed: {exc}")
        return False


# ── Public API ─────────────────────────────────────────────────────────────────

def deliver(
    content: str,
    skill: dict,
    subject: str = "AI Briefing",
    jira: dict | None = None,
    analytics: dict | None = None,
    confluence: dict | None = None,
    cc_recipients: list[str] | None = None,
    html_body: str | None = None,
    attachment_path: str | None = None,
) -> dict:
    """
    Deliver the briefing. File is always saved; email/Teams fire on top.

    Args:
        content   : markdown text of the briefing (saved to file, Teams fallback)
        skill     : parsed skill dict — skill["user"] is the recipient email
        subject   : email/Teams message subject line
        jira      : raw Jira agent output — used to build HTML email
        analytics : raw Analytics agent output — used to build HTML email

    Returns dict of {channel: bool} for logging.
    """
    results   = {"file": True}
    recipient = skill.get("user", "")
    if recipient and not is_valid_recipient(recipient):
        log.error(f"Refusing to send: profile owner {recipient!r} is not a single @tomtom.com address")
        recipient = ""                       # falls through to the "no valid email" branch below
    bad_cc = [c for c in (cc_recipients or []) if not is_valid_recipient(c)]
    if bad_cc:
        log.warning(f"Dropping CC addresses that are not single @tomtom.com addresses: {bad_cc}")
        cc_recipients = [c for c in cc_recipients if is_valid_recipient(c)]

    # Test mode: redirect all emails to a single address (set TEST_RECIPIENT_OVERRIDE in .env)
    _override = os.getenv("TEST_RECIPIENT_OVERRIDE", "").strip()
    if _override and recipient and recipient != _override:
        subject = f"[TEST → {recipient}] {subject}"
        recipient = _override
        log.info(f"TEST MODE: redirecting email to {_override}")

    # Parallel run: everything goes to one address only, no CCs (the real list goes in the subject)
    _parallel_to = os.getenv("EMAIL_PARALLEL_TO", "").strip()
    intended_to = None

    # Use pre-built HTML if provided (UC3 weekly, UC4 alert); else auto-build from data
    if not html_body and jira is not None and analytics is not None:
        try:
            from email_html import build as build_html
            _preview_note = None
            if os.getenv("PREVIEW_MODE"):
                _preview_note = (
                    "This is a preview of your daily operational briefing. Once implemented, "
                    "you will receive this automatically every morning. If you have any initial "
                    "feedback or comments, please reach out to the OPS Native AI team."
                )
            html_body = build_html(jira, analytics, confluence, skill=skill,
                                   preview_note=_preview_note)
        except Exception as exc:
            log.warning(f"HTML email build failed, falling back to plain text: {exc}")
            html_body = ""

    # 1. Outlook email (HTML preferred, plain text fallback)
    if recipient and "@" in recipient:
        merged_cc = list(dict.fromkeys((cc_recipients or []) + GLOBAL_CC))
        # EMAIL_CC=off: owner only, no global or profile CCs (the Azure job)
        if os.getenv("EMAIL_CC", "on").strip().lower() == "off":
            merged_cc = []
        body_to_send = html_body if html_body else content
        if _parallel_to:
            intended_to = recipient
            cc_note = f"; cc {', '.join(merged_cc)}" if merged_cc else "; no cc"
            subject = f"[AZURE PARALLEL → {recipient}{cc_note}] {subject}"
            recipient, merged_cc = _parallel_to, []
            log.info(f"PARALLEL RUN: email for {intended_to} sent to {_parallel_to} only")
        results["email"], transport = _send_email(
            recipient, subject, body_to_send,
            cc_emails=merged_cc,
            attachment_path=attachment_path,
        )
        # Who received what — the basis of trigger analytics / business value
        import audit_log
        audit_log.log_delivery(
            profile_owner=skill.get("user", ""), to_email=recipient, cc_emails=merged_cc,
            subject=subject, has_attachment=bool(attachment_path), sent_ok=results["email"],
            transport=transport, intended_to=intended_to,
        )
    else:
        log.warning(f"No valid email in skill['user']: {recipient!r}")
        results["email"] = False

    # 2. Teams (only if webhook URL is configured)
    teams_url = os.getenv("TEAMS_WEBHOOK_URL", "").strip()
    if teams_url:
        results["teams"] = _send_teams(subject, content)

    return results
