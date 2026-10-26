"""Previous full week as a reference, and the "Recommended actions" box with root causes (26 Oct)."""
from datetime import date

import email_html as E

AN = {"live": True, "week_label": "2026-10-26", "fta_current": 96.1, "fta_rag": "AMBER",
      "efficiency_vs_bl": 71.0, "efficiency_rag": "RED", "coq_current": 6.4, "coq_rag": "GREEN",
      "metrics_4w": [{"week": "2026-10-26", "fta": 96.1, "coq": 6.4, "efficiency_vs_bl": 71.0, "qc_tasks": 31},
                     {"week": "2026-10-19", "fta": 97.64, "coq": 21.77, "efficiency_vs_bl": 94.2, "qc_tasks": 381}],
      "process_breakdown": [
          {"process_type": "pt-a", "fta_pct": 94.0, "total_qc": 20, "eff_vs_bl": 62.0, "coq_pct": 9.0, "total_hrs": 120,
           "work_units": [{"work_unit": "WU-1", "fta_pct": 90.0, "total_qc": 10}, {"work_unit": "WU-2", "fta_pct": 98.0, "total_qc": 10}]},
          {"process_type": "pt-b", "fta_pct": 100.0, "total_qc": 11, "eff_vs_bl": 88.0, "coq_pct": 4.0, "total_hrs": 80}]}


def test_period_label():
    assert E.period_label("2026-10-19", today=date(2026, 10, 26), relative=False) == "Mon 19 Oct – Sun 25 Oct 2026"
    assert E.period_label("2026-10-12", today=date(2026, 10, 26)) == "Mon 12 Oct – Sun 18 Oct 2026 (latest week with data)"


def test_monday_shows_last_week_with_its_full_range():
    for today, wk in ((date(2026, 10, 26), "2026-10-19"), (date(2026, 11, 2), "2026-10-26"), (date(2027, 1, 4), "2026-12-28")):
        assert E.week_word(wk, today) == "last week"
    assert E.period_label("2026-10-19", today=date(2026, 10, 26)) == "Mon 19 Oct – Sun 25 Oct 2026 (last week)"
    assert E.period_label("2026-12-28", today=date(2027, 1, 4)) == "Mon 28 Dec – Sun 03 Jan 2027 (last week)"


def test_other_days_show_this_week_from_monday_to_today():
    assert E.period_label("2026-10-26", today=date(2026, 10, 27)) == "Mon 26 Oct – Tue 27 Oct 2026 (this week so far)"
    assert E.period_label("2026-10-26", today=date(2026, 10, 28)) == "Mon 26 Oct – Wed 28 Oct 2026 (this week so far)"
    assert E.period_label("2026-10-26", today=date(2026, 11, 1)) == "Mon 26 Oct – Sun 01 Nov 2026 (this week so far)"


def test_reference_row_names_the_shown_week():
    row = E._reference_row({**AN, "week_label": "2026-10-26"}, ["fta"])
    assert row[0] == "Previous full week (reference)" and "Mon 19 Oct – Sun 25 Oct 2026:" in row[1]


def test_previous_full_week_only_when_current_week_is_row_0():
    assert E.previous_full_week(AN)["week"] == "2026-10-19"
    assert E.previous_full_week({**AN, "week_label": "2026-10-19"}) is None


def test_actions_name_the_root_cause_and_the_reference_week():
    items = E.action_items({}, AN, {"fta", "efficiency"})
    assert [r for r, _, _ in items] == ["AMBER", "RED"]
    fta_why = items[0][2]
    assert "pt-a" in fta_why and "mostly WU-1" in fta_why and "pt-b" not in fta_why     # 100% has no rejections
    assert "Only 31 QC" in fta_why and "97.64%" in fta_why
    assert "pt-a</b> (62.0% of baseline" in items[1][2]


def test_sla_breach_is_an_action_and_uc4_shows_only_its_metric():
    jira = {"sla_breaches": [{"key": "OM-1", "assignee": "A", "hours_stale": 400}], "sla_escalation_hours": 72}
    assert E.action_items(jira, AN, {"fta"})[0][1].startswith("Follow up on 1 Jira")
    only = E.action_items(jira, AN, set(), only="efficiency")
    assert len(only) == 1 and "efficiency" in only[0][1]


def test_no_box_when_all_green():
    green = {**AN, "fta_rag": "GREEN", "efficiency_rag": "GREEN"}
    assert E._build_action_box({}, green, {"fta", "efficiency"}) == ""
