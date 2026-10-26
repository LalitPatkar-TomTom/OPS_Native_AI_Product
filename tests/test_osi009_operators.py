"""OSI-009 (26 Oct): operators past the profile's alert levels, with all six KPIs, for Operational Leads and
profiles that select Level = Operator."""
import email_html as E
import skill_registry as sr
from agents import analytics_agent as A

TABLE = """## 5. Metrics Profile

| Metric | Level | Scope | Target | Alert At | Direction | Source |
|---|---|---|---|---|---|---|
| FTA — First Time Accuracy | Process Type | All | 95% | below 92% | ↓ Alert on drop | Databricks |
| CoQ — Cost of Quality | {level} | All | 7% | above 10% | ↑ Alert on rise | Databricks |
"""


def _skill(domain, level="Process Type"):
    text = f"**Domain:** {domain}\n\n" + TABLE.format(level=level)
    return {**{"primary_metrics": sr._extract_primary_metrics(text)[0], "metric_rules": sr._extract_metric_rules(text),
               "metric_thresholds": sr._extract_metric_thresholds(text)},
            "domain": sr._extract_domain(text),
            "operator_view": sr._extract_primary_metrics(text)[1] or sr._extract_domain(text).lower().startswith("operational lead")}


def test_operational_leads_and_opt_in_get_the_operator_view():
    assert _skill("Operational Lead")["operator_view"]
    assert _skill("Project Manager", level="Operator")["operator_view"]        # opted in
    assert not _skill("Project Manager")["operator_view"]
    assert not _skill("Quality Lead")["operator_view"]


def test_levels_come_from_the_profile():
    assert sr.operator_levels(_skill("Operational Lead")) == {
        "fta": {"alert": 92.0, "direction": "drop"}, "coq": {"alert": 10.0, "direction": "rise"}}


def test_only_operators_past_a_level_are_flagged_and_small_samples_are_not_judged():
    levels = {"fta": {"alert": 92.0, "direction": "drop"}, "coq": {"alert": 10.0, "direction": "rise"}}
    ops = [{"operator": "a", "fta_pct": 85.0, "coq_pct": 5.0, "total_qc": 40, "prod_tasks": 200},
           {"operator": "b", "fta_pct": 99.0, "coq_pct": 15.0, "total_qc": 40, "prod_tasks": 200},
           {"operator": "c", "fta_pct": 99.0, "coq_pct": 5.0, "total_qc": 40, "prod_tasks": 200},
           {"operator": "d", "fta_pct": 0.0, "coq_pct": 100.0, "total_qc": 1, "prod_tasks": 0}]     # one task
    A.mark_operator_breaches(ops, levels)
    assert [o["breaches"] for o in ops] == [["fta"], ["coq"], [], []]


def test_table_lists_only_breaching_operators_with_six_kpis():
    ops = [{"operator": "a", "process_type": "pt", "fta_pct": 85.0, "eff_vs_bl": 95.0, "coq_pct": 5.0,
            "yield_pct": 90.0, "total_hrs": 40.0, "sampling_pct": 20.0, "breaches": ["fta"]},
           {"operator": "c", "process_type": "pt", "fta_pct": 99.0, "eff_vs_bl": 105.0, "coq_pct": 5.0,
            "yield_pct": None, "total_hrs": 30.0, "sampling_pct": 20.0, "breaches": []}]
    h = E._build_operator_breakdown({"operator_breakdown": ops, "week_label": "2026-10-26",
                                     "operator_levels": {"fta": {"alert": 92.0, "direction": "drop"}}})
    for col in ("FTA", "Eff vs BL", "CoQ", "Yield", "Hrs", "Sampling"):
        assert f">{col}</th>" in h
    assert "1 of 2</b> operators" in h and ">a</td>" in h and ">c</td>" not in h
    assert "FTA below 92%" in h
    ok = E._build_operator_breakdown({"operator_breakdown": ops[1:], "week_label": "2026-10-26",
                                      "operator_levels": {"fta": {"alert": 92.0, "direction": "drop"}}})
    assert "All 1 operators with QC data are within your alert levels" in ok
