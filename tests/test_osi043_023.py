"""OSI-043: every UC4 metric past its level in one run goes out in ONE email, worst first, still once per metric
per day; one alert alone is the email of before. OSI-023: time saved counts UC4 per breach, not per email."""
from datetime import date

import pytest

import delivery
import email_html
import trigger_engine as te
import weekly_analytics as wa
from agents import analytics_agent, uc4_state

USER = "osi043.user@tomtom.com"
SKILL = {"user": USER, "project_name": "P", "primary_metrics": ["fta", "coq"],
         "metric_thresholds": {"fta": {"alert": 92.0, "target": 95.0, "direction": "drop"},
                               "coq": {"alert": 7.0, "target": 6.0, "direction": "rise"}}}
LIVE = {"live": True, "fta_current": 90.0, "coq_current": 9.0, "week_label": "2026-10-12", "process_breakdown": []}


@pytest.fixture
def mail(monkeypatch):
    """Record every delivery (subject + html) instead of sending; .ok decides what the send reports."""
    class Rec(list):
        ok = True
    rec = Rec()
    monkeypatch.setattr(delivery, "deliver",
                        lambda content, skill, **kw: (rec.append(kw) or {"email": rec.ok}))
    monkeypatch.setattr(analytics_agent, "run", lambda skill, report_type="daily": dict(LIVE))
    monkeypatch.delenv("UC4_COMBINED_ALERT", raising=False)
    monkeypatch.delenv("FORCE_UC4_ALERT", raising=False)
    uc4_state.clear_for_testing(USER)
    yield rec
    uc4_state.clear_for_testing(USER)


def test_two_breaches_go_out_in_one_email_worst_first(mail):
    te._run_uc4(SKILL, USER)
    assert len(mail) == 1
    subj, html = mail[0]["subject"], mail[0]["html_body"]
    # CoQ 9 vs 7 is 29% past its level, FTA 90 vs 92 only 2%: CoQ comes first
    assert subj.startswith("UC4 Alert RED — 2 metrics past their level: COQ 9.00%, FTA 90.00%")
    assert "2 metrics past their alert level" in html
    assert html.index("CoQ — Cost of Quality") < html.index("FTA — First Time Accuracy")
    assert html.count("<html>") == 1 and html.count("<!-- Footer -->") == 1
    assert uc4_state.already_alerted_today(USER, "fta") and uc4_state.already_alerted_today(USER, "coq")


def test_combined_alert_is_still_once_per_metric_per_day(mail):
    te._run_uc4(SKILL, USER)
    te._run_uc4(SKILL, USER)
    assert len(mail) == 1


def test_a_metric_that_already_alerted_today_is_left_out(mail):
    uc4_state.mark_alerted(USER, "coq")
    te._run_uc4(SKILL, USER)
    assert len(mail) == 1 and mail[0]["subject"].startswith("UC4 Alert RED — FTA 90.00% vs threshold 92.0%")


def test_failed_combined_send_marks_nothing(mail):
    mail.ok = False
    te._run_uc4(SKILL, USER)
    assert not uc4_state.already_alerted_today(USER, "fta") and not uc4_state.already_alerted_today(USER, "coq")


def test_switch_off_sends_one_email_per_metric(mail, monkeypatch):
    monkeypatch.setenv("UC4_COMBINED_ALERT", "0")
    te._run_uc4(SKILL, USER)
    assert [m["subject"][:22] for m in mail] == ["UC4 Alert RED — COQ 9.", "UC4 Alert RED — FTA 90"]


def test_single_alert_email_is_unchanged_by_the_split():
    """build_alert() = the shell around its body_only part, so one alert alone is byte-for-byte the old email."""
    kw = dict(metric="fta", rag="RED", current_value=90.0, threshold=92.0, direction="stable",
              week_label="2026-10-12", process_breakdown=[], skill={"project_name": "P"}, analytics=LIVE)
    full, body = email_html.build_alert(**kw), email_html.build_alert(**kw, body_only=True)
    assert body in full and full.startswith("<html>") and "<html>" not in body
    assert "\n  </table>\n\n  <!-- Alert banner -->" in full and "  </table>\n\n  <!-- Footer -->" in full


def test_combined_alert_html_lists_every_metric():
    parts = [{"label": "CoQ — Cost of Quality", "value": 9.0, "level": 7.0, "direction": "rise"},
             {"label": "FTA — First Time Accuracy", "value": 90.0, "level": 92.0, "direction": "drop"}]
    html = email_html.build_combined_alert(parts, ["<p>coq body</p>", "<p>fta body</p>"], {"project_name": "P"})
    assert "Above 7%" in html and "Below 92%" in html and "2.00 pts" in html
    assert html.index("coq body") < html.index("fta body")


# ── OSI-023 ──────────────────────────────────────────────────────────────────────

def _email(day: str, uc: str = "UC4") -> dict:
    """A delivered email at 10:00 IST on day."""
    return {"ts": f"{day}T04:30:00", "uc_id": uc, "sent_ok": 1}


def test_uc4_counts_breaches_not_emails():
    # one combined email on 20 Oct carrying three breaches counts 3
    alerts = [{"user_email": "a@tomtom.com", "metric_key": m, "alert_date": "2026-10-20"} for m in ("fta", "coq", "yield")]
    d = {"alerts": alerts}
    assert wa.uc4_items(d, [_email("2026-10-20")], [], alerts) == 3


def test_uc4_days_before_the_state_table_still_count_emails():
    alerts = [{"user_email": "a@tomtom.com", "metric_key": "fta", "alert_date": "2026-10-09"}]
    d = {"alerts": alerts}
    sent = [_email("2026-10-05"), _email("2026-10-05"), _email("2026-10-09"), _email("2026-10-05", "UC1")]
    hist = [{"day_ist": "2026-10-03", "uc_id": "UC4", "count": 4}, {"day_ist": "2026-10-03", "uc_id": "UC1", "count": 9}]
    assert wa.uc4_items(d, sent, hist, alerts) == 1 + 2 + 4


def test_period_hours_use_breaches_for_uc4():
    day = "2026-10-20"
    alerts = [{"user_email": "a@tomtom.com", "metric_key": m, "alert_date": day} for m in ("fta", "coq")]
    d = {"emails": [{**_email(day), "profile_owner": "a@tomtom.com", "to_email": "a@tomtom.com",
                     "has_attachment": 0}],
         "events": [], "runs": [], "alerts": alerts, "history": [], "chats": [], "feedback": [], "reports": []}
    s = wa.period_stats(d, date(2026, 10, 19), date(2026, 10, 25))
    assert s["by_uc"]["UC4"] == 1 and s["items"]["UC4"] == 2
    assert s["hours"]["UC4"] == pytest.approx(2 * wa.MINUTES["UC4"] / 60)
