"""Weekly "What's new in OPS Native AI & OPS Hub" email — sent every Friday (user rule, 30 Oct 2026).

Functional, not technical: what users now see and can do, plus what is coming next and how to give
feedback. The content is notes.json: one note per user-visible change, written in plain words at release
time (by a person; no AI model is used). This module turns the notes of one week into the email.
send_weekly.py sends it from opsai@ every Friday 17:00 IST (Azure job), to every beta user and the
stakeholders, without a review step (user, 30 Oct: no need to review it every week).

Local use:
  python whats_new.py 2026-10-30                 # the email for the week ending that Friday -> archive folder
  python whats_new.py 2026-10-30 --send-to-me    # also a copy to Lalit only, from his own Outlook
"""
from __future__ import annotations

import html
import json
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE / "notes.json"
# archive of the emails next to the other Native AI docs (all Native AI material lives in Deployed)
_DOCS = HERE.parents[2] / "OPS_NativeAI_Docs" / "WhatsNew"
ARCHIVE = _DOCS if _DOCS.parent.exists() else HERE / "out"
ME = "lalit.patkar@tomtom.com"
OSI_LOG = ("https://tomtom.atlassian.net/wiki/spaces/MCP/pages/2594472161/"
           "OPS+Native+AI+OPS+Hub+User+Onboarding+Use+Cases+and+Limitations")
OPS_HUB = "https://tomtom-ops-hub.bravewave-803863cf.westeurope.azurecontainerapps.io"

# Who gets it: every beta user (the owner of each profile on the skills share, read at send time, so new
# users are included) plus the stakeholders: the weekly analytics readers, as agreed on 30 Oct.
STAKEHOLDERS_TO = ["ketki.avachat@tomtom.com", "pratish.deshpande@tomtom.com", "vrushali.kashikar@tomtom.com"]
STAKEHOLDERS_CC = ["peter.clarys@tomtom.com", "seema.nayyar2@tomtom.com", "saurav.nanda@tomtom.com"]
AREAS = ["Daily Briefing, Weekly Report and Alerts", "Jira follow-ups", "OPS Hub"]   # order in the email

INK, MUTED, RED, BLUE, LINE, SOFT = "#14213D", "#5A6577", "#C2410C", "#2563EB", "#E3E7EE", "#F4F6FA"
F = "font-family:Segoe UI,Arial,sans-serif"


def recipients(profile_emails) -> tuple[list[str], list[str]]:
    """(To, CC): every beta user plus the To stakeholders, lower-case, no duplicates; anyone already in To
    is left out of CC."""
    to = sorted({e.strip().lower() for e in list(profile_emails) + STAKEHOLDERS_TO if e and "@" in e})
    cc = sorted({c.lower() for c in STAKEHOLDERS_CC} - set(to))
    return to, cc


def load_notes(path: Path = NOTES) -> dict:
    """notes.json as a dict {"coming_next": [...], "notes": [...]}."""
    return json.loads(path.read_text(encoding="utf-8"))


def week_notes(data: dict, friday: date, since: date | None = None) -> list[dict]:
    """The notes dated after `since` (default: the Friday before) up to and including `friday`."""
    start = since or friday - timedelta(days=7)
    return [n for n in data.get("notes", []) if start < date.fromisoformat(n["date"]) <= friday]


def _fmt(d: date) -> str:
    """'Fri 30 Oct 2026'."""
    return d.strftime("%a %d %b %Y")


def period(friday: date, since: date | None = None) -> str:
    """'Fri 23 Oct – Fri 30 Oct 2026' (the window the notes cover)."""
    start = since or friday - timedelta(days=7)
    left = start.strftime("%a %d %b") if start.year == friday.year else _fmt(start)
    return f"{left} – {_fmt(friday)}"


def subject(friday: date, since: date | None = None) -> str:
    """The email subject."""
    return f"What's new in OPS Native AI & OPS Hub · {period(friday, since)}"


def _e(s: str) -> str:
    """HTML-escaped text."""
    return html.escape(s or "")


def build(notes: list[dict], coming_next: list[str], label: str) -> str:
    """The Outlook-safe HTML email (tables and inline styles only) for one week's notes."""
    hl = next((n for n in notes if n.get("highlight")), None)
    rows = []
    for area in AREAS + sorted({n["area"] for n in notes} - set(AREAS)):
        items = [n for n in notes if n["area"] == area and n is not hl]
        if not items:
            continue
        rows.append(f'<tr><td style="{F};font-size:16px;font-weight:bold;color:{INK};padding:18px 0 6px">'
                    f'{_e(area)}</td></tr>')
        for n in items:
            tag = f' <span style="{F};font-size:11px;color:{MUTED}">({_e(n["osi"])})</span>' if n.get("osi") else ""
            rows.append(f'<tr><td style="{F};font-size:14px;color:{INK};line-height:1.5;padding:4px 0 4px 12px;'
                        f'border-left:3px solid {LINE}"><b>{_e(n["title"])}</b>: {_e(n["text"])}{tag}</td></tr>')
    box = ""
    if hl:
        box = (f'<tr><td style="padding:14px 0 4px"><table width="100%" cellpadding="0" cellspacing="0" '
               f'style="background:#FFF1E8;border-left:5px solid {RED}"><tr><td style="{F};padding:12px 16px">'
               f'<div style="font-size:15px;font-weight:bold;color:{INK}">{_e(hl["title"])}</div>'
               f'<div style="font-size:14px;color:{INK};line-height:1.5;margin-top:4px">{_e(hl["text"])}</div>'
               f'</td></tr></table></td></tr>')
    nxt = "".join(f'<li style="margin:3px 0">{_e(x)}</li>' for x in coming_next)
    nxt_block = (f'<tr><td style="{F};font-size:16px;font-weight:bold;color:{INK};padding:18px 0 6px">Coming next'
                 f'</td></tr><tr><td style="{F};font-size:14px;color:{INK};line-height:1.5"><ul style="margin:0;'
                 f'padding-left:20px">{nxt}</ul></td></tr>') if nxt else ""
    return f"""<html><body style="margin:0;background:#FFFFFF">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:16px">
<table width="640" cellpadding="0" cellspacing="0">
<tr><td style="{F};font-size:12px;font-weight:bold;letter-spacing:1px;color:{RED};text-transform:uppercase">
OPS Native AI &amp; OPS Hub · What's new · {_e(label)}</td></tr>
<tr><td style="{F};font-size:24px;font-weight:bold;color:{INK};padding:6px 0 4px">What changed for you this week</td></tr>
<tr><td style="{F};font-size:14px;color:{MUTED};line-height:1.5">Thank you for your feedback in the OSI log.
This is what changed for you this week.</td></tr>
{box}
{''.join(rows)}
{nxt_block}
<tr><td style="padding:16px 0 0"><table width="100%" cellpadding="0" cellspacing="0" style="background:{SOFT}">
<tr><td style="{F};font-size:13px;color:{INK};line-height:1.5;padding:12px 16px">
<b>Your feedback shapes this.</b> Add a row to the <a href="{OSI_LOG}" style="color:{BLUE}">OSI log</a>
or change your scope and alert levels in <a href="{OPS_HUB}/onboarding" style="color:{BLUE}">OPS Hub</a>.
</td></tr></table></td></tr>
<tr><td style="{F};font-size:11px;color:{MUTED};padding:12px 0 0">Sent every Friday by the OPS Native AI team.
The emails you receive are built from the data with fixed rules; no AI model writes them.</td></tr>
</table></td></tr></table></body></html>"""


def send_to_me(subj: str, body: str) -> None:
    """A copy from the user's own Outlook to the user only (optional preview; Windows + Outlook)."""
    import win32com.client
    mail = win32com.client.Dispatch("Outlook.Application").CreateItem(0)
    mail.To = ME
    mail.Subject = f"[PREVIEW] {subj}"
    mail.HTMLBody = body
    mail.Send()


if __name__ == "__main__":
    friday = date.fromisoformat(sys.argv[1])
    data = load_notes()
    notes = week_notes(data, friday)
    if not notes:
        sys.exit(f"no notes for the week ending {friday}")
    body = build(notes, data.get("coming_next", []), period(friday))
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    out = ARCHIVE / f"whats_new_{friday}.html"
    out.write_text(body, encoding="utf-8")
    print("written", out, "|", len(notes), "notes")
    if "--send-to-me" in sys.argv:
        send_to_me(subject(friday), body)
        print("preview sent to", ME)
