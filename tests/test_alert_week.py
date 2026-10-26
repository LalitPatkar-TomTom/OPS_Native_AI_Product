"""Which week each email asks Databricks for (26 Oct): alerts target this week, the daily briefing the previous working day's."""
from datetime import date

from agents import analytics_agent as A


class _Day(date):
    """date.today() pinned to a chosen day."""
    pinned = date(2026, 10, 26)

    @classmethod
    def today(cls):
        return cls.pinned


def _target(monkeypatch, today, report_type):
    _Day.pinned = today
    monkeypatch.setattr(A, "date", _Day)
    return A._compute_target(report_type)[0]


def test_alerts_ask_for_this_week_every_day(monkeypatch):
    # the metrics query falls back to the latest earlier week with QC data, i.e. last week while this week has none
    assert _target(monkeypatch, date(2026, 10, 26), "alert") == "2026-10-26"     # Monday
    assert _target(monkeypatch, date(2026, 10, 28), "alert") == "2026-10-26"     # Wednesday


def test_daily_briefing_shows_last_week_on_monday_only(monkeypatch):
    assert _target(monkeypatch, date(2026, 10, 26), "daily") == "2026-10-19"
    assert _target(monkeypatch, date(2026, 10, 27), "daily") == "2026-10-26"


def test_alert_label_says_why_last_week_is_shown():
    import email_html as E
    assert (E.period_label("2026-10-19", today=date(2026, 10, 26), fallback_note=True)
            == "Mon 19 Oct – Sun 25 Oct 2026 (last week · no QC data yet this week)")
    assert (E.period_label("2026-10-26", today=date(2026, 10, 27), fallback_note=True)
            == "Mon 26 Oct – Tue 27 Oct 2026 (this week so far)")
