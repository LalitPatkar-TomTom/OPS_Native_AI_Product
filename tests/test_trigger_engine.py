"""Alert and report decisions in the trigger engine (MultiAgent_Briefing/trigger_engine.py).

UC4 never alerts on placeholder data, a failed send does not silence the alert for the day, UC3 is
sent once per day by the scheduled runs, and a failing use case is reported as an error.
"""
import pytest

import audit_log
import delivery
import fire_all_now
import trigger_engine as te
from agents import analytics_agent, jira_agent, uc4_state

USER = "jane.doe@tomtom.com"
SKILL = {"user": USER, "project_name": "P", "primary_metrics": ["fta"],
         "metric_thresholds": {"fta": {"alert": 92.0, "target": 95.0, "direction": "drop"}}}
LIVE = {"live": True, "fta_current": 90.0, "week_label": "2026-10-12", "process_breakdown": []}


@pytest.fixture
def mail(monkeypatch):
    """Record deliveries instead of sending; .ok decides what the send reports."""
    class Rec(list):
        ok = True
    rec = Rec()
    monkeypatch.setattr(delivery, "deliver",
                        lambda content, skill, **kw: (rec.append(kw.get("subject")) or {"email": rec.ok}))
    uc4_state.clear_for_testing(USER)
    yield rec
    uc4_state.clear_for_testing(USER)


def _analytics(monkeypatch, data):
    monkeypatch.setattr(analytics_agent, "run", lambda skill, report_type="daily": dict(data))


def test_uc4_alerts_on_breach_and_suppresses_repeat(mail, monkeypatch):
    _analytics(monkeypatch, LIVE)
    te._run_uc4(SKILL, USER)
    te._run_uc4(SKILL, USER)
    assert len(mail) == 1 and mail[0].startswith("UC4 Alert RED — FTA 90.00%")


def test_uc4_never_alerts_on_placeholder_data(mail, monkeypatch):
    _analytics(monkeypatch, analytics_agent._fallback("offline"))
    te._run_uc4({**SKILL, "metric_thresholds": {"fta": {"alert": 99.0, "direction": "drop"}}}, USER)
    assert mail == []


def test_uc4_failed_send_is_retried_next_slot(mail, monkeypatch):
    _analytics(monkeypatch, LIVE)
    mail.ok = False
    te._run_uc4(SKILL, USER)
    assert uc4_state.already_alerted_today(USER, "fta") is False
    mail.ok = True
    te._run_uc4(SKILL, USER)
    assert len(mail) == 2 and uc4_state.already_alerted_today(USER, "fta") is True


def test_uc4_healthy_metric_sends_nothing(mail, monkeypatch):
    _analytics(monkeypatch, {**LIVE, "fta_current": 97.0})
    te._run_uc4(SKILL, USER)
    assert mail == []


def test_uc3_sent_once_per_day_by_scheduled_runs(monkeypatch):
    def must_not_run(skill):
        raise AssertionError("UC3 ran although it was already sent today")
    monkeypatch.setattr(jira_agent, "run", must_not_run)
    audit_log.start_run("2026-10-23", "17:00", 0, ["UC3"], 1, "scheduled")
    audit_log.log_uc3("uc3.user@tomtom.com", {}, {}, {}, status="sent")
    te._run_uc3({}, None, "uc3.user@tomtom.com")          # returns before any agent runs
    assert audit_log.sent_today("UC3", "uc3.user@tomtom.com") is True
    assert audit_log.sent_today("UC3", "someone.else@tomtom.com") is False


def test_manual_runs_are_never_held_back():
    audit_log.start_run("2026-10-23", "17:00", 0, ["UC3"], 1, "manual")
    audit_log.log_uc3("manual.user@tomtom.com", {}, {}, {}, status="sent")
    assert audit_log.sent_today("UC3", "manual.user@tomtom.com") is False


def test_failing_use_case_counts_as_error(monkeypatch, tmp_path):
    def boom(skill, user):
        raise RuntimeError("Jira down")
    monkeypatch.setattr(te, "_run_uc2", boom)
    assert te._make_job("UC2", {"user": USER}, tmp_path / "x")() is False
    with pytest.raises(RuntimeError):
        fire_all_now._dispatch("UC2", {"user": USER}, tmp_path / "x", USER)


def test_quiet_hours_skip_is_not_an_error(monkeypatch, tmp_path):
    monkeypatch.setattr(te, "_in_quiet_hours", lambda q, tz: True)
    assert te._make_job("UC2", {"user": USER, "quiet_hours": (19, 8)}, tmp_path / "x")() is True


@pytest.mark.parametrize("quiet,tz,expected", [
    (None, "Asia/Kolkata", False), ((0, 24), "Asia/Kolkata", True),
    ((5, 5), "Asia/Kolkata", False), ((0, 24), "Bad/Zone", False)])
def test_in_quiet_hours(quiet, tz, expected):
    assert te._in_quiet_hours(quiet, tz) is expected
