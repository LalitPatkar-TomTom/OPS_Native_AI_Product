"""Profile check email for new and updated OPS Native AI profiles.

Run by the Azure job after fire_all_now, before the analytics DB is saved:
    python profile_check.py                 # check new/changed profiles, email their owners (09, 13, 17 IST runs)
    python profile_check.py --to ADDRESS    # test: email every result to ADDRESS only, no CC, nothing recorded
    python profile_check.py --seed          # record all current profiles as checked, send nothing
    python profile_check.py --reminders --to ADDRESS   # test: the daily Jira-key reminders, to ADDRESS only

Daily reminder (2 Nov 2026): at the 09:00 run, every profile whose Jira project key Jira cannot find gets one
reminder a day until it is fixed (same CC). Why: the check above only emails new or changed profiles, and the
profiles seeded on 21 Oct were never checked, so wrong keys (Geocoding, GDN, QA, LMDF) went unnoticed while the
briefings said "Jira SLA: All clear".

A profile is new or changed when its sha256 differs from table profile_checks in trigger_audit.db.
Each profile version gets one email: a thank-you, what works, suggested updates and what the owner
should check personally. It is for information only: it never stops or changes the owner's triggers. The very first run seeds the existing profiles silently.
"""
import argparse
import hashlib
import html
import logging
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import audit_log
import skill_registry
from config import SKILLS_DIR

log = logging.getLogger("profile_check")

CC = ["Ketki.Avachat@tomtom.com", "Vrushali.Kashikar@tomtom.com",
      "pratish.deshpande@tomtom.com", "lalit.patkar@tomtom.com"]
SEND_HOURS = {9, 13, 17}                 # not the 21:00 run — outside working hours
REMINDER_HOUR = 9                        # Jira-key reminders: once a day, at the first run (user, 2 Nov 2026)
JIRA_UCS = {"UC1", "UC2", "UC3"}         # use cases that read Jira (briefing, SLA follow-up, weekly report)
ONBOARDING_URL = "https://tomtom-ops-hub.bravewave-803863cf.westeurope.azurecontainerapps.io/onboarding"
METRIC_NAME = {"fta": "FTA", "efficiency": "Efficiency", "coq": "CoQ", "copq": "CoPQ", "yield": "Yield"}
UC_NAME = {"UC1": "Daily Briefing", "UC2": "Jira SLA follow-up", "UC3": "Weekly Report",
           "UC4": "Metric alerts", "UC5": "Plan vs Actual"}
TABLE = """CREATE TABLE IF NOT EXISTS profile_checks (
    email       TEXT PRIMARY KEY,
    sha256      TEXT NOT NULL,
    checked_at  TEXT NOT NULL,
    issues      INTEGER NOT NULL,
    emailed     INTEGER NOT NULL        -- 1 sent, 0 seeded / not sent
)"""


# ── checks against the real systems ──────────────────────────────────────────
def jira_project_ok(key: str) -> tuple[bool, str]:
    """(exists, note). Looks the value up in Jira's project directory: a JQL query on an unknown
    project returns no tickets instead of an error, so it cannot tell a wrong key from a quiet one.
    Only projects visible to the OPS Native AI Jira account count — UC2 reads Jira with that account."""
    from agents import jira_agent
    import httpx
    try:
        r = httpx.get(f"{jira_agent.JIRA_BASE_URL}/rest/api/3/project/search",
                      params={"query": key, "maxResults": 20}, headers=jira_agent._auth_header(), timeout=20)
        if r.status_code != 200:
            return True, f"could not be checked (HTTP {r.status_code})"
        projects = r.json().get("values") or []
    except Exception as exc:
        return True, f"could not be checked ({str(exc)[:80]})"
    if any(p.get("key", "").upper() == key.upper() for p in projects):
        return True, ""
    by_name = [p for p in projects if p.get("name", "").lower() == key.lower()]
    if by_name:
        return False, f"is a project name; its Jira key is <b>{html.escape(by_name[0]['key'])}</b>"
    return False, "was not found in Jira (or is not visible to OPS Native AI)"


def databricks_presence(process_types: list[str], planning_ids: list[str]) -> tuple[dict, dict, str]:
    """{name: tasks in the last 120 days} for process types and planning IDs found in Databricks."""
    if not process_types and not planning_ids:
        return {}, {}, ""
    try:
        from agents.analytics_agent import _build_client
        client, table = _build_client()
    except Exception as exc:
        return {}, {}, f"Databricks not reachable ({str(exc)[:80]})"
    q = lambda v: "'" + v.lower().replace("'", "''") + "'"

    def present(col: str, values: list[str]) -> dict:
        """Map each value found in the KPI table (last 120 days) to its done-task count (scoped SELECT)."""
        if not values:
            return {}
        sql = (f"SELECT LOWER({col}) AS v, SUM(COALESCE(Prod_Done_task_count, 0)) AS n FROM {table} "
               f"WHERE week_start >= date_sub(current_date(), 120) AND LOWER({col}) IN ({', '.join(map(q, values))}) "
               f"GROUP BY 1")
        res = client.execute_sql(sql, 500, allowed_table=table)
        rows = res.get("rows") or res.get("data") or []
        return {(r.get("v") if isinstance(r, dict) else r[0]): (r.get("n") if isinstance(r, dict) else r[1])
                for r in rows}
    try:
        return present("processType", process_types), present("planningid", planning_ids), ""
    except Exception as exc:
        return {}, {}, f"Databricks query failed ({str(exc)[:80]})"


def check(skill: dict) -> dict:
    """Findings for one profile: ok (works), fix (please update), manual (please check yourself)."""
    ok, fix, manual = [], [], []
    active = [u["uc_id"] for u in skill.get("use_cases", []) if u.get("active")]
    if active:
        ok.append("Use cases active: " + ", ".join(f"{u} {UC_NAME.get(u, '')}".strip() for u in active))
    else:
        fix.append("<b>No use case is marked Active</b>, so you receive no emails. Mark the ones you want as Active.")

    # Jira (UC2)
    keys = [k.strip() for k in re.split(r"[,;/]", skill.get("jira_project") or "") if k.strip()]
    if "UC2" in active:
        if not keys:
            fix.append("<b>Jira project key missing</b>: your Jira SLA follow-up (UC2) cannot run. Add the key(s) "
                       "of the projects you track — the letters before the number in a ticket ID (e.g. <i>OM</i> in OM-123456).")
        for k in keys:
            good, note = jira_project_ok(k)
            if not good:
                fix.append(f"<b>Jira project \"{html.escape(k)}\"</b> {note}, so your Jira SLA follow-up (UC2) "
                           "cannot run. Use the project key — the letters before the number in a ticket ID "
                           "(e.g. <i>OM</i> in OM-123456).")
            elif note:
                manual.append(f"Jira project {html.escape(k)}: {note}.")
            else:
                ok.append(f"Jira project <b>{html.escape(k)}</b> found in Jira.")

    # Databricks scope
    pts = skill.get("databricks_process_types") or []
    pids = skill.get("databricks_planning_ids") or []
    found_pt, found_pid, err = databricks_presence(pts, pids)
    if err:
        manual.append(f"Process types / planning IDs could not be checked: {html.escape(err)}.")
    else:
        if pts:
            missing = [p for p in pts if p.lower() not in found_pt]
            idle = [p for p in pts if p.lower() in found_pt and not found_pt[p.lower()]]
            if len(pts) > len(missing):
                ok.append(f"{len(pts) - len(missing)} of {len(pts)} process types found in Databricks.")
            if missing:
                fix.append("<b>Process types not found in Databricks</b> (check the spelling): "
                           + ", ".join(f"<i>{html.escape(p)}</i>" for p in missing) + ".")
            if idle:
                manual.append("No completed tasks in the last 120 days for: "
                              + ", ".join(f"<i>{html.escape(p)}</i>" for p in idle) + " — still relevant?")
        if pids:
            missing = [p for p in pids if p.lower() not in found_pid]
            if len(pids) > len(missing):
                ok.append(f"{len(pids) - len(missing)} of {len(pids)} planning IDs found in Databricks.")
            if missing:
                fix.append("<b>Planning IDs not found in Databricks</b>: "
                           + ", ".join(f"<i>{html.escape(p)}</i>" for p in missing) + ".")
        if not pts and not pids and (skill.get("scope_mode") or "defined") == "defined" and not skill.get("databricks_feature"):
            fix.append("<b>No process types or planning IDs</b>: your emails will show no FTA, efficiency, CoQ or "
                       "yield, and no metric alerts are sent, until you add the planning IDs and/or process types "
                       "you are responsible for. Jira follow-ups are not affected.")
        elif not pts and not pids:
            ok.append("Scope: " + ("all process types, as chosen in your profile" if skill.get("scope_mode") == "all"
                                   else f"process types matching <i>{html.escape(str(skill.get('scope_mode')))}</i>")
                      + ".")

    # Metric alerts (UC4)
    th = skill.get("metric_thresholds") or {}
    if "UC4" in active:
        set_ = {m: t for m, t in th.items() if t.get("alert") is not None}
        if set_:
            ok.append("Alert levels: " + ", ".join(
                f"{METRIC_NAME.get(m, m)} {t['alert']:g}%" + (f" (target {t['target']:g}%)" if t.get("target") is not None else "")
                for m, t in set_.items()))
        else:
            fix.append("<b>No metric alert levels</b>: metric alerts (UC4) cannot fire. Add an alert level per metric.")

    # Things only the owner can confirm
    qh = skill.get("quiet_hours")
    if qh:
        manual.append(f"Quiet hours read as <b>{qh[0]:02d}:00–{qh[1]:02d}:00</b>: briefings, SLA follow-ups and "
                      "weekly reports are held back then (metric alerts are not).")
    manual.append("Emails are sent after the runs at 09:00, 13:00, 17:00 and 21:00 IST; the daily briefing comes "
                  "with the 09:00 run" + (f" (your profile says {html.escape(skill['briefing_time'])})"
                                          if skill.get("briefing_time") else "") + ".")
    if (skill.get("alert_channel") or "").lower() not in ("", "email", "outlook"):
        manual.append(f"Your profile names <b>{html.escape(skill['alert_channel'])}</b> as alert channel; for now all "
                      "alerts come by email from opsai@tomtom.com.")
    if skill.get("cc_recipients"):
        manual.append("CC recipients in your profile are not used: emails go to you only.")
    manual.append("Alert levels and targets above match what you want to be alerted on.")
    return {"ok": ok, "fix": fix, "manual": manual}


# ── email ────────────────────────────────────────────────────────────────────
def compose(skill: dict, res: dict, updated: bool) -> tuple[str, str]:
    """Build the (subject, HTML body) of the profile-check email from check() results."""
    first = html.escape(skill.get("user_first_name") or "there")
    n = len(res["fix"])
    subject = ("Your OPS Native AI profile is live" + (" – thank you for the update" if updated else "")
               + (f" – {n} suggested update{'s' if n != 1 else ''}" if n else " – all checks passed"))
    li = lambda items: "".join(f"<li>{x}</li>" for x in items)
    body = [f"<p>Hi {first},</p>",
            "<p>Thank you for " + ("updating your" if updated else "onboarding to") + " <b>OPS Native AI</b>! "
            "Your profile is active from the next run, and we checked it against Jira and Databricks.</p>"]
    if res["ok"]:
        body.append(f"<p style='margin-bottom:4px'><b>✅ Working</b></p><ul style='margin-top:0'>{li(res['ok'])}</ul>")
    if res["fix"]:
        body.append(f"<p style='margin-bottom:4px'><b>⚠️ Suggested updates to your profile</b></p>"
                    "<p style='margin:0 0 4px'>For your information: your briefings and alerts keep running as "
                    "they are; these updates make them more accurate.</p>"
                    f"<ol style='margin-top:0'>{li(res['fix'])}</ol>")
    if res["manual"]:
        body.append(f"<p style='margin-bottom:4px'><b>🔍 Please check yourself</b></p>"
                    f"<ul style='margin-top:0'>{li(res['manual'])}</ul>")
    body.append("<p><b>How to update (when you want to):</b> open the onboarding page on OPS Hub, change what is needed and press "
                f"<i>Finish &amp; Submit</i>. The new profile is used from the next run:<br>"
                f"<a href='{ONBOARDING_URL}'>{ONBOARDING_URL}</a></p>"
                "<p><i>This is an automated mail. If anything is unclear, please reach out to the OPS Native AI team.</i></p>"
                "<p>Thanks,<br>OPS Native AI team</p>")
    return subject, ("<div style='font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#1a1a1a;"
                     "line-height:1.5'>" + "".join(body) + "</div>")


# ── Daily Jira-key reminder ──────────────────────────────────────────────────

REMINDER_TABLE = """CREATE TABLE IF NOT EXISTS profile_reminders (
    email    TEXT NOT NULL,
    sent_on  TEXT NOT NULL,             -- IST date; one reminder per profile per day
    keys     TEXT NOT NULL,             -- the Jira keys that were not found
    emailed  INTEGER NOT NULL,
    PRIMARY KEY (email, sent_on)
)"""


def _project_status(key: str) -> str:
    """"ok" / "missing" / "unknown" by the run's own route (MCP first, then REST): jira_agent.project_status."""
    from agents import jira_agent
    return jira_agent.project_status(key)


def jira_key_problems(skill: dict) -> list[tuple[str, str]]:
    """(key, note) for every Jira project key in the profile that the run cannot read, when a use case that reads
    Jira is active. A key that could not be checked (Jira down) is not a problem: no reminder on an outage."""
    active = {u["uc_id"] for u in skill.get("use_cases", []) if u.get("active")}
    if not active & JIRA_UCS:
        return []
    keys = [k.strip() for k in re.split(r"[,;/]", skill.get("jira_project") or "") if k.strip()]
    out = []
    for k in keys:
        if _project_status(k) == "missing":
            good, note = jira_project_ok(k)          # for the note, e.g. "is a project name; its key is X"
            out.append((k, note if not good and note else "was not found in Jira (or is not visible to OPS Native AI)"))
    return out


def compose_reminder(skill: dict, problems: list[tuple[str, str]]) -> tuple[str, str]:
    """(subject, HTML body) of the daily reminder: which key, what it stops, how to fix it."""
    first = html.escape(skill.get("user_first_name") or "there")
    keys = ", ".join(html.escape(k) for k, _ in problems)
    items = "".join(f"<li><b>{html.escape(k)}</b> {note}.</li>" for k, note in problems)
    body = (f"<p>Hi {first},</p>"
            "<p>The Jira project key in your OPS Native AI profile could not be found in Jira, so your "
            "<b>Jira SLA is not being checked</b>: your briefing and weekly report show "
            "<i>Jira SLA: Not checked</i> and no Jira SLA follow-up is sent.</p>"
            f"<ul>{items}</ul>"
            "<p><b>How to fix:</b> use the project key, the letters before the number in a ticket ID (e.g. "
            "<i>OM</i> in OM-123456). Open the onboarding page on OPS Hub, correct the Jira project key and press "
            "<i>Finish &amp; Submit</i>; it is used from the next run:<br>"
            f"<a href='{ONBOARDING_URL}'>{ONBOARDING_URL}</a></p>"
            "<p>If the key is right, the OPS Native AI Jira account may not have access to that project: please "
            "reply so we can request it.</p>"
            "<p><i>This is an automated reminder, sent once a day until the key is found in Jira.</i></p>"
            "<p>Thanks,<br>OPS Native AI team</p>")
    return (f"Action needed: Jira project key {keys} not found – your Jira SLA is not checked",
            "<div style='font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#1a1a1a;line-height:1.5'>"
            + body + "</div>")


def send_reminders(con, files: list, skip: set, today: str, to: str = "") -> int:
    """Send today's Jira-key reminders (CC: CC) to profiles with a key Jira cannot find; returns the number sent.
    skip: profiles that already got the full check email this run. to: test address (nothing recorded)."""
    import delivery
    con.execute(REMINDER_TABLE)
    done = {e for (e,) in con.execute("SELECT email FROM profile_reminders WHERE sent_on = ?", (today,))}
    sent = 0
    for p in files:
        email = p.name[: -len("_skill.md")].lower()
        if email in skip or (not to and email in done):
            continue
        try:
            skill = skill_registry.load_skill(p)
            problems = jira_key_problems(skill)
        except Exception as exc:
            log.warning(f"reminder check failed for {email}: {exc}")
            continue
        if not problems:
            continue
        subject, body = compose_reminder(skill, problems)
        if to:
            ok = delivery._send_graph(to, "[TEST → " + email + "] " + subject, body)
        else:
            ok = delivery._send_graph(email, subject, body, cc_emails=CC)
            con.execute("INSERT OR REPLACE INTO profile_reminders VALUES (?,?,?,?)",
                        (email, today, ",".join(k for k, _ in problems), int(ok)))
        sent += ok
        print(f"jira key reminder: {email} — {', '.join(k for k, _ in problems)} not found — "
              f"email {'sent' if ok else 'NOT sent'}")
    return sent


# ── main ─────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    """Email owners of new or changed profiles (CC: CC) their check results; record sha256 in profile_checks.

    Runs only in SEND_HOURS unless --to/--seed; the first run or --seed records without emailing.
    --to sends every result to one address only and records nothing. Returns 0.
    """
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--to", help="test: send every result to this address only, no CC, record nothing")
    ap.add_argument("--seed", action="store_true", help="record current profiles as checked, send nothing")
    ap.add_argument("--only", help="check only this profile email (with --to)")
    ap.add_argument("--reminders", action="store_true", help="with --to: send the daily Jira-key reminders now")
    a = ap.parse_args(argv)

    if not a.to and not a.seed and datetime.now().hour not in SEND_HOURS:
        print("profile check: not a sending slot (09, 13, 17 IST) — skipped")
        return 0
    con = sqlite3.connect(str(audit_log._DB_PATH), timeout=10)
    first_run = not con.execute("SELECT 1 FROM sqlite_master WHERE name = 'profile_checks'").fetchone()
    con.execute(TABLE)
    known = dict(con.execute("SELECT email, sha256 FROM profile_checks"))
    seed = a.seed or (first_run and not a.to)

    files = sorted(p for p in Path(SKILLS_DIR).glob("*_skill.md") if "@" in p.name)
    if a.reminders:
        if not a.to:
            print("profile check: --reminders needs --to (a test address)")
            con.close()
            return 0
        only = [p for p in files if not a.only or p.name[: -len("_skill.md")].lower() == a.only.lower()]
        print(f"profile check: {send_reminders(con, only, set(), '', to=a.to)} test reminder(s) sent to {a.to}")
        con.close()
        return 0
    sent = checked = 0
    emailed_now: set[str] = set()
    for p in files:
        email = p.name[: -len("_skill.md")].lower()
        if a.only and email != a.only.lower():
            continue
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if not a.to and known.get(email) == sha:
            continue
        now = datetime.now().isoformat(timespec="seconds")
        if seed:
            con.execute("INSERT OR REPLACE INTO profile_checks VALUES (?,?,?,?,0)", (email, sha, now, 0))
            continue
        try:
            skill = skill_registry.load_skill(p)
            res = check(skill)
        except Exception as exc:
            log.warning(f"profile check failed for {email}: {exc}")
            print(f"profile check: {email} could not be checked ({exc})")
            continue
        checked += 1
        subject, body = compose(skill, res, updated=email in known)
        import delivery
        if a.to:
            ok = delivery._send_graph(a.to, "[TEST → " + email + "] " + subject, body)
        else:
            ok = delivery._send_graph(email, subject, body, cc_emails=CC)
            con.execute("INSERT OR REPLACE INTO profile_checks VALUES (?,?,?,?,?)",
                        (email, sha, now, len(res["fix"]), int(ok)))
        sent += ok
        emailed_now.add(email)
        print(f"profile check: {email} — {len(res['fix'])} to update, {len(res['manual'])} to check — "
              f"email {'sent' if ok else 'NOT sent'}")
    # daily Jira-key reminder: first run of the day, live only (not when seeding, not a test send)
    if not seed and not a.to and datetime.now().hour == REMINDER_HOUR:
        today = datetime.now().date().isoformat()
        print(f"profile check: {send_reminders(con, files, emailed_now, today)} Jira key reminder(s) sent")
    con.commit()
    con.close()
    if seed:
        print(f"profile check: {len(files)} existing profile(s) recorded as checked (no emails)")
    else:
        print(f"profile check: {checked} new/updated profile(s) checked, {sent} email(s) sent")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  [%(levelname)-8s]  %(message)s")
    sys.exit(main())
