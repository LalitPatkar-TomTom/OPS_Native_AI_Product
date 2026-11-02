"""Daily Jira-key reminder (profile_check.py, user 2 Nov 2026): once a day at the 09:00 run, every profile whose
Jira project key Jira cannot find gets a reminder with the same CC as the profile check, until it is fixed.

No Jira call and no email: jira_project_ok and the Graph sender are replaced; the DB is a temp SQLite file.
"""
import sqlite3
from datetime import datetime

import pytest

import delivery
import profile_check as pc

UC = "| UC1 | Daily Operational Briefing | Calendar · 09:00 daily | {s} |\n"


def _profile(tmp_path, email, key, status="✅ Active"):
    """A profile file with one use case (UC1) and the given Jira key."""
    p = tmp_path / f"{email}_skill.md"
    p.write_text(f"# {email.split('.')[0].title()} X\nJira project key: {key}\n" + UC.format(s=status), encoding="utf-8")
    return p


@pytest.fixture
def sent(monkeypatch):
    """Record every Graph send instead of sending; Jira knows only OM and QADEV."""
    out = []
    monkeypatch.setattr(delivery, "_send_graph", lambda to, subject, body, cc_emails=None: out.append(
        (to, subject, body, cc_emails)) or True)
    monkeypatch.setattr(pc, "_project_status", lambda k: "ok" if k in ("OM", "QADEV") else
                        "unknown" if k == "DOWN" else "missing")
    monkeypatch.setattr(pc, "jira_project_ok", lambda k: (False, "was not found in Jira (or is not visible to OPS Native AI)"))
    return out


def test_only_wrong_keys_with_a_jira_use_case_are_problems(tmp_path, sent):
    from skill_registry import load_skill
    assert pc.jira_key_problems(load_skill(_profile(tmp_path, "a.b@tomtom.com", "OM"))) == []
    assert [k for k, _ in pc.jira_key_problems(load_skill(_profile(tmp_path, "c.d@tomtom.com", "QA")))] == ["QA"]
    assert pc.jira_key_problems(load_skill(_profile(tmp_path, "e.f@tomtom.com", "QA", "❌ Inactive"))) == []
    assert pc.jira_key_problems(load_skill(_profile(tmp_path, "i.j@tomtom.com", "DOWN"))) == []   # outage: no mail


def test_one_reminder_per_profile_per_day_with_cc_and_recorded(tmp_path, sent):
    files = [_profile(tmp_path, "a.b@tomtom.com", "OM"), _profile(tmp_path, "c.d@tomtom.com", "QA"),
             _profile(tmp_path, "g.h@tomtom.com", "LMDF")]
    con = sqlite3.connect(tmp_path / "audit.db")
    assert pc.send_reminders(con, files, skip={"g.h@tomtom.com"}, today="2026-11-03") == 1   # g.h got the full check
    to, subject, body, cc = sent[0]
    assert to == "c.d@tomtom.com" and cc == pc.CC
    assert "QA" in subject and "not checked" in subject and "Jira SLA is not being checked" in body
    assert pc.ONBOARDING_URL in body
    assert pc.send_reminders(con, files, skip=set(), today="2026-11-03") == 1                 # only g.h, c.d done
    assert [s[0] for s in sent] == ["c.d@tomtom.com", "g.h@tomtom.com"]
    assert pc.send_reminders(con, files, skip=set(), today="2026-11-04") == 2                 # next day: again
    rows = con.execute("SELECT email, sent_on, keys, emailed FROM profile_reminders ORDER BY sent_on, email").fetchall()
    assert rows[0] == ("c.d@tomtom.com", "2026-11-03", "QA", 1) and len(rows) == 4


def test_test_mode_sends_to_one_address_without_cc_and_records_nothing(tmp_path, sent):
    con = sqlite3.connect(tmp_path / "audit.db")
    pc.send_reminders(con, [_profile(tmp_path, "c.d@tomtom.com", "QA")], set(), "", to="me@tomtom.com")
    assert sent[0][0] == "me@tomtom.com" and sent[0][3] is None and sent[0][1].startswith("[TEST → c.d@tomtom.com]")
    assert con.execute("SELECT count(*) FROM profile_reminders").fetchone()[0] == 0


@pytest.mark.parametrize("hour, expected", [(9, 1), (13, 0), (17, 0)])
def test_main_sends_reminders_only_at_the_first_run(tmp_path, sent, monkeypatch, hour, expected):
    import audit_log
    _profile(tmp_path, "c.d@tomtom.com", "QA")
    db = tmp_path / "audit.db"
    con = sqlite3.connect(db)
    con.execute(pc.TABLE)                                             # not the first run: no silent seeding
    sha = __import__("hashlib").sha256((tmp_path / "c.d@tomtom.com_skill.md").read_bytes()).hexdigest()
    con.execute("INSERT INTO profile_checks VALUES (?,?,?,?,?)", ("c.d@tomtom.com", sha, "2026-10-21", 0, 0))
    con.commit()
    con.close()
    monkeypatch.setattr(audit_log, "_DB_PATH", db)
    monkeypatch.setattr(pc, "SKILLS_DIR", str(tmp_path))

    class _Now(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 3, hour, 5)
    monkeypatch.setattr(pc, "datetime", _Now)
    assert pc.main([]) == 0
    assert len(sent) == expected                                       # unchanged profile: only the reminder
