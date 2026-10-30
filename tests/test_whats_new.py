"""Weekly "What's new" email (comms/whats_new): the week's notes, recipients, and the Friday send rules."""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "comms" / "whats_new"))
import send_weekly as S  # noqa: E402
import whats_new as W  # noqa: E402

DATA = {"coming_next": ["Power BI parity"], "notes": [
    {"date": "2026-10-28", "area": "Jira follow-ups", "title": "Old", "text": "last week", "osi": ""},
    {"date": "2026-11-02", "area": "OPS Hub", "title": "Self <Service>", "text": "a & b", "osi": "OSI-1"},
    {"date": "2026-11-06", "area": "Daily Briefing, Weekly Report and Alerts", "title": "Top", "text": "big one",
     "osi": "", "highlight": True},
]}
FRI = date(2026, 11, 6)


def test_week_takes_the_notes_since_last_friday():
    assert [n["title"] for n in W.week_notes(DATA, FRI)] == ["Self <Service>", "Top"]
    assert [n["title"] for n in W.week_notes(DATA, FRI, since=date(2026, 10, 23))] == ["Old", "Self <Service>", "Top"]
    assert W.period(FRI) == "Fri 30 Oct – Fri 06 Nov 2026"


def test_email_is_functional_escaped_and_has_the_highlight_box():
    html = W.build(W.week_notes(DATA, FRI), DATA["coming_next"], W.period(FRI))
    assert "Self &lt;Service&gt;" in html and "a &amp; b" in html and "(OSI-1)" in html
    assert html.index("big one") < html.index(">OPS Hub</td>") and html.count("big one") == 1   # box first, not repeated
    assert "Power BI parity" in html and "no AI model writes them" in html


def test_recipients_are_all_beta_users_plus_stakeholders():
    to, cc = W.recipients(["Devika.Shetty@tomtom.com", "pratish.deshpande@tomtom.com", "x"])
    assert "devika.shetty@tomtom.com" in to and "ketki.avachat@tomtom.com" in to
    assert to.count("pratish.deshpande@tomtom.com") == 1 and "x" not in to
    assert cc == ["peter.clarys@tomtom.com", "saurav.nanda@tomtom.com", "seema.nayyar2@tomtom.com"]


def test_profiles_give_the_beta_users(tmp_path):
    for n in ("a.b@tomtom.com_skill.md", "C.D@tomtom.com_skill.md", "notes.md"):
        (tmp_path / n).write_text("x")
    assert S.profile_emails(tmp_path) == ["a.b@tomtom.com", "c.d@tomtom.com"]


def test_friday_rules():
    assert S.plan(date(2026, 11, 5), DATA, [], None) == {"send": False, "why": "not a Friday"}
    assert S.plan(FRI, DATA, [], FRI)["why"] == "already sent for 2026-11-06"
    assert S.plan(date(2026, 11, 13), DATA, [], FRI)["why"] == "no notes this week"
    p = S.plan(FRI, DATA, ["devika.shetty@tomtom.com"], date(2026, 10, 30))
    assert p["send"] and p["notes"] == 2 and "devika.shetty@tomtom.com" in p["to"]
    assert p["subject"] == "What's new in OPS Native AI & OPS Hub · Fri 30 Oct – Fri 06 Nov 2026"


def test_marker_stops_a_second_send(tmp_path):
    m = tmp_path / "whats_new_sent.json"
    assert S.last_sent(m) is None
    m.write_text('{"friday": "2026-10-30"}')
    assert S.last_sent(m) == date(2026, 10, 30)


def test_notes_file_is_valid_and_functional():
    data = W.load_notes()
    for n in data["notes"]:
        date.fromisoformat(n["date"])
        assert n["area"] and n["title"] and n["text"]
    assert not any(w in " ".join(n["text"] for n in data["notes"]).lower()
                   for w in ("sql", "refactor", "endpoint", "function", "commit"))   # no technical wording
