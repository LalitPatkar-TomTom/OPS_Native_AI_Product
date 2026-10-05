"""
Delivery — sends briefing output to the user.

Priority order:
  1. Outlook email  (win32com — uses your logged-in Outlook, zero config)
  2. Teams webhook  (set TEAMS_WEBHOOK_URL in .env when ready)
  3. File only      (always saved regardless)

The recipient email is read directly from the skill file —
it is the filename itself (lalit.patkar@tomtom.com_skill.md → lalit.patkar@tomtom.com).
No hardcoding, no separate config.
"""
import logging
import os
from datetime import datetime
from pathlib import Path

# config.py already loaded the root .env at import time — no separate load needed here
log = logging.getLogger("delivery")

# Always CC'd on every email regardless of skill file settings
GLOBAL_CC = ["Ketki.Avachat@tomtom.com"]


# ── 1. Outlook email (primary — Windows, no config needed) ────────────────────

def _send_outlook(to_email: str, subject: str, html_body: str,
                  cc_emails: list[str] | None = None) -> bool:
    """
    Send via the locally running Outlook application using HTML formatting.
    Uses win32com — works as long as Outlook is installed and your account is signed in.
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

    # Test mode: redirect all emails to a single address (set TEST_RECIPIENT_OVERRIDE in .env)
    _override = os.getenv("TEST_RECIPIENT_OVERRIDE", "").strip()
    if _override and recipient and recipient != _override:
        subject = f"[TEST → {recipient}] {subject}"
        recipient = _override
        log.info(f"TEST MODE: redirecting email to {_override}")

    # Use pre-built HTML if provided (UC3 weekly, UC4 alert); else auto-build from data
    if not html_body and jira is not None and analytics is not None:
        try:
            from email_html import build as build_html
            _preview_note = None
            if os.getenv("PREVIEW_MODE"):
                _preview_note = (
                    "This is a preview of your daily operational briefing. Once implemented, "
                    "you will receive this automatically every morning. If you have any initial "
                    "feedback or comments, please reply to Lalit Patkar."
                )
            html_body = build_html(jira, analytics, confluence, skill=skill,
                                   preview_note=_preview_note)
        except Exception as exc:
            log.warning(f"HTML email build failed, falling back to plain text: {exc}")
            html_body = ""

    # 1. Outlook email (HTML preferred, plain text fallback)
    if recipient and "@" in recipient:
        merged_cc = list(dict.fromkeys((cc_recipients or []) + GLOBAL_CC))
        body_to_send = html_body if html_body else content
        results["email"] = _send_outlook(recipient, subject, body_to_send, cc_emails=merged_cc)
    else:
        log.warning(f"No valid email in skill['user']: {recipient!r}")
        results["email"] = False

    # 2. Teams (only if webhook URL is configured)
    teams_url = os.getenv("TEAMS_WEBHOOK_URL", "").strip()
    if teams_url:
        results["teams"] = _send_teams(subject, content)

    return results
