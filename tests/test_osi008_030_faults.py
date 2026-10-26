"""26 Oct: email faults (small samples, subject status, project name), OSI-008 headline KPIs, OSI-030 scoped alert
levels, and the minimum volume before alerts use this week."""
import email_html as E
import skill_registry as sr
import trigger_engine as T
from agents import analytics_agent as A

PROFILE = """## 5. Metrics Profile

| Metric | Level | Scope | Target | Alert At | Direction | Source |
|---|---|---|---|---|---|---|
| FTA — First Time Accuracy | Process Type | All | 98% | below 98% | ↕ Alert on deviation | Databricks |
| CoQ — Cost of Quality | Process Type | pt-a, pt-b | 3% | above 3% | ↑ Alert on rise | Databricks |
| Yield | Planning ID | PID-1 | 85% | below 85% | ↓ Alert on drop | Databricks |
| Plan vs Actual | Planning ID | PID-1 | 100% | below 85% | ↓ Alert on drop | Databricks |
"""


def test_alert_week_needs_50_qc_and_a_fifth_of_last_week():
    assert A.alert_week_too_early(35, 2222) == 445          # Sheetal on Monday morning: falls back
    assert A.alert_week_too_early(500, 2222) is None
    assert A.alert_week_too_early(20, 60) == 50             # small scope: the 50 floor applies
    assert A.alert_week_too_early(60, 60) is None


def test_alert_label_says_why_last_week_is_used():
    note = E.alert_week_note({"early_week": {"week": "2026-10-26", "qc": 35, "needed": 445}})
    assert "this week too early: 35 QC&apos;d so far, alerts use it from 445" in note
    assert E.alert_week_note({}) == " · no QC data yet this week"


def test_small_samples_are_shown_but_never_flagged():
    rows = [{"process_type": "one-task", "fta_pct": 0.0, "fta_rag": "RED", "total_qc": 1},
            {"process_type": "real", "fta_pct": 91.0, "fta_rag": "RED", "total_qc": 400,
             "work_units": [{"work_unit": "wu", "fta_pct": 50.0, "fta_rag": "RED", "total_qc": 2}]}]
    A._mark_small_samples(rows)
    assert rows[0]["fta_rag"] == "SMALL" and rows[1]["fta_rag"] == "RED"
    assert rows[1]["work_units"][0]["fta_rag"] == "SMALL"
    assert [p["process_type"] for p in E.flagged(rows)] == ["real"]
    assert sorted(rows, key=E._fta_order)[-1]["process_type"] == "one-task"     # listed last


def test_subject_and_body_share_the_overall_status():
    assert E.overall_rag({"sla_breaches": [1]}, {}) == "RED"
    assert E.overall_rag({}, {"fta_rag": "AMBER"}) == "AMBER"
    assert E.overall_rag({}, {"fta_rag": "GREEN"}) == "GREEN"


def test_project_name_falls_back_to_the_jira_key():
    assert E.project_name_of({"jira_project": "OM"}) == "OM"
    assert E.project_name_of({"project_name": "RM Lane", "jira_project": "OM"}) == "RM Lane"


def test_six_headline_kpis_with_rag_only_for_profile_metrics():
    an = {"fta_current": 96.5, "fta_rag": "GREEN", "efficiency_vs_bl": 103.4, "efficiency_rag": "GREEN",
          "coq_current": 18.4, "coq_rag": "RED", "yield_current": None, "prod_hrs": 1500, "qc_hrs": 553,
          "sampling_pct": 25.0, "total_qc": 2222, "prod_tasks": 8873}
    h = E._build_kpi_row(an, {"sla_breaches": [], "sla_warnings": []}, {"fta", "coq"})
    for label in ("FTA", "Efficiency vs BL", "Cost of Quality", "Yield", "Hours", "Sampling", "Jira SLA Alerts"):
        assert label in h
    assert h.count("no alert set") == 2                      # efficiency and yield are not in this profile
    assert "2,053h" in h and "2,222 QC&apos;d of 8,873 tasks" in h
    no_scope = E._build_kpi_row({"no_scope": True}, {"sla_breaches": [], "sla_warnings": []}, {"none"})
    assert "Jira SLA Alerts" in no_scope and "Cost of Quality" not in no_scope


def test_metric_rules_keep_level_and_scope():
    rules = sr._extract_metric_rules(PROFILE)
    assert [(r["metric"], r["level"], r["scope"]) for r in rules] == [
        ("fta", "process", []), ("coq", "process", ["pt-a", "pt-b"]), ("yield", "planning", ["PID-1"])]


def test_scoped_rows_are_checked_per_item_and_whole_scope_rows_overall():
    skill = {"metric_rules": sr._extract_metric_rules(PROFILE),
             "databricks_process_types": ["pt-a", "pt-b", "pt-c"], "databricks_planning_ids": ["PID-1"]}
    overall, scoped = T.split_rules(skill, "coq")
    assert not overall and scoped[0]["scope"] == ["pt-a", "pt-b"]
    overall, scoped = T.split_rules(skill, "yield")          # names the whole planning scope -> overall
    assert overall and not scoped
    an = {"process_breakdown": [
        {"process_type": "pt-a", "coq_pct": 4.5, "total_hrs": 100, "fta_rag": "GREEN"},
        {"process_type": "pt-b", "coq_pct": 2.0, "total_hrs": 80, "fta_rag": "GREEN"},
        {"process_type": "pt-c", "coq_pct": 9.0, "total_hrs": 50, "fta_rag": "GREEN"},          # not in the row
        {"process_type": "pt-a-extra", "coq_pct": 9.0, "total_hrs": 50, "fta_rag": "GREEN"}]}   # exact names only
    hits = T.scoped_breaches(an, scoped_rules := T.split_rules(skill, "coq")[1], "coq")
    assert [(h[1]["process_type"], h[2]) for h in hits] == [("pt-a", 4.5)]
    assert scoped_rules


def test_piped_process_type_still_matches_its_profile_name():
    rule = [{"metric": "fta", "level": "process", "scope": ["area-conflictsolving-aa"], "alert": 92.0, "direction": "drop"}]
    an = {"process_breakdown": [{"process_type": "area-conflictsolving-aa|ia|ap|bua|neighb", "fta_pct": 80.0,
                                 "fta_rag": "RED", "total_qc": 300}]}
    assert len(T.scoped_breaches(an, rule, "fta")) == 1
    an["process_breakdown"][0].update(total_qc=3, fta_rag="SMALL")                   # too small: never alerts
    assert T.scoped_breaches(an, rule, "fta") == []
