"""No process types / planning IDs in a profile: no quality or efficiency figures, a note instead; Jira keeps working."""
import re

import email_html as E
import email_html_weekly as W
import skill_registry as sr
from agents import analytics_agent as A, jira_agent as J

PROFILE = """# Jane Doe
Jira project key: DSM
| Metric | Level | Scope | Target | Alert At | Direction | Source |
| --- | --- | --- | --- | --- | --- | --- |
| FTA — First Time Accuracy | Planning ID | (all) | 98% | below 98% | ↓ Alert on drop | Databricks |
"""
JIRA = {"sla_breaches": [{"key": "DSM-1", "summary": "s", "status": "Open", "assignee": "A", "url": "https://x/DSM-1",
                          "hours_stale": 400.0, "sla_status": "BREACH_72H", "priority": "High", "labels": []}],
        "sla_warnings": [], "open_tickets": [], "total_open": 1, "source": "Jira DSM", "as_of": "2026-10-26", "error": None}


def _skill(tmp_path, text=PROFILE):
    p = tmp_path / "jane.doe@tomtom.com_skill.md"
    p.write_text(text, encoding="utf-8")
    return sr.load_skill(p)


def test_profile_without_scope_is_flagged(tmp_path):
    s = _skill(tmp_path)
    assert s["no_databricks_scope"] and s["primary_metrics"] == ["none"]


def test_explicit_all_or_process_types_is_kept(tmp_path):
    assert sr.has_databricks_scope({"scope_mode": "all"})
    assert sr.has_databricks_scope({"databricks_process_types": ["orbis-dir-oneway"]})
    assert not sr.has_databricks_scope({"scope_mode": "defined"})


def test_no_databricks_query_and_no_numbers(tmp_path):
    a = A.run(_skill(tmp_path), "daily")          # returns before any Databricks client is built
    assert a["no_scope"] and not a["live"] and a["process_breakdown"] == [] and a["week_label"] == ""


def test_jira_still_scoped_by_project_and_person(tmp_path):
    jql, _ = J._build_jql(_skill(tmp_path))
    assert "project = DSM" in jql and 'reporter = "jane.doe@tomtom.com"' in jql and "created >= -365d" in jql


def test_emails_show_the_note_and_jira_but_no_figures(tmp_path):
    s = _skill(tmp_path)
    a = A.run(s, "daily")
    for html in (E.build(JIRA, a, {}, s), W.build(JIRA, a, {}, skill=s)):
        t = re.sub(r"<[^>]+>", " ", html)
        assert "Add your scope" in t and "DSM-1" in t
        note_end = t.find("the next email will include them")
        rest = t[:t.find("Add your scope")] + t[note_end:]
        assert not re.search(r"\bFTA\b|\bCoQ\b|Efficiency vs|Breakdown|4-Week Trend|96\.68", rest)


def test_uc4_is_skipped(tmp_path, monkeypatch):
    import trigger_engine as T
    seen = []
    monkeypatch.setattr(T.audit_log, "log_skipped", lambda uc, user, skill, reason: seen.append((uc, reason)))
    monkeypatch.setattr(A, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no analytics for UC4")))
    T._run_uc4(_skill(tmp_path), "jane.doe@tomtom.com")
    assert seen == [("UC4", "no process types or planning IDs in the profile")]
