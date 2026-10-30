"""Fixes from the 30 Oct 09:00 run check: overall status and headline, UC4 per metric, weighted efficiency,
the work-mix guard, no repeated KPI actions."""
import re

import analytics_agent as A
import email_html as E
import root_cause as R


def text(s):
    """Visible text with tags removed and spaces collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s).replace("&nbsp;", " "))


AN = {"live": True, "week_label": "2026-10-26", "fta_current": 100.0, "fta_rag": "GREEN",
      "efficiency_vs_bl": 9.2, "efficiency_rag": "RED", "coq_current": 13.87, "coq_rag": "RED_P1",
      "yield_current": 42.86, "yield_rag": "RED", "metrics_4w": [], "process_breakdown": []}


# ── Overall status and headline ─────────────────────────────────────────────────────────────────────

def test_kpi_without_alert_level_never_colours_the_email():
    assert E.overall_rag({}, AN, {"fta"}) == "GREEN"                 # Dhammaratna: only FTA in her profile
    assert E.overall_rag({}, AN, {"fta", "efficiency"}) == "RED"
    assert E.overall_rag({"sla_warnings": [1]}, AN, {"fta"}) == "AMBER"


def test_headline_names_the_real_reason():
    h = E.headline_text("OM", {"sla_breaches": [1, 2, 3]}, AN, {"fta"})
    assert h == "Action needed for OM: 3 Jira tickets past the SLA." and "quality" not in h
    h = E.headline_text("RM", {}, AN, {"coq", "yield"})
    assert "CoQ 13.87% past your alert level" in h and "Yield 42.86% past your alert level" in h
    assert E.headline_text("Geo", {}, AN, {"fta"}).startswith("Geo is on track")
    no_scope = {"no_scope": True, "fta_rag": "GREEN"}
    assert "no scope in your profile" in E.headline_text("DPOT", {}, no_scope, {"none"})
    assert E.headline_text("DPOT", {"sla_breaches": [1]}, no_scope, {"none"}) == \
        "Action needed for DPOT: 1 Jira ticket past the SLA."


# ── UC4: the alert's own metric and level ───────────────────────────────────────────────────────────

def test_fired_alert_gets_its_item_even_when_the_general_level_says_fine():
    an = {**AN, "fta_current": 96.32, "fta_rag": "GREEN"}            # Shital: 96.32% vs her 98%
    assert E.action_items({}, an, set(), only="fta") == []
    items = E.action_items({}, an, set(), only="fta", fired=True)
    assert len(items) == 1 and items[0][0] == "RED"
    assert E.action_items({}, AN, set(), only="copq", fired=True)[0][1].startswith("Find where QC")


def test_red_coq_is_red_not_amber():
    assert E.action_items({}, AN, {"coq"})[0][0] == "RED"


def test_yield_alert_is_about_yield():
    an = {**AN, "metrics_4w": [{"week": "2026-10-26", "yield": 91.1, "qc_tasks": 100},
                               {"week": "2026-10-19", "yield": 85.1, "fta": 96.6, "qc_tasks": 2000}]}
    ops = [{"operator": "A", "work_unit": "OCC", "process_type": "p", "fta_pct": 50.0, "yield_pct": 99.0,
            "prod_tasks": 50, "coq_pct": 1.0, "total_hrs": 5, "breaches": ["yield"]},
           {"operator": "B", "work_unit": "OCC", "process_type": "p", "fta_pct": 99.0, "yield_pct": 70.0,
            "prod_tasks": 50, "coq_pct": 1.0, "total_hrs": 5, "breaches": ["yield"]}]
    html = E.build_alert("fta", "RED", 91.11, 94.0, "stable", "2026-10-26", [], {"user_name": "L"},
                         label="Yield", alert_on="drop", operator_breakdown=ops, analytics=an, metric_key="yield")
    t = text(html)
    assert "lowest yield first" in t and t.index(" B ") < t.index(" A ")
    assert "Yield 85.10%" in t and "FTA 96.60%" not in t                  # reference row is the yield
    assert "low FTA" not in t and "Yield 91.11%" in t                     # advice and box are about yield


# ── Weighted efficiency ─────────────────────────────────────────────────────────────────────────────

def test_weighted_efficiency_agrees_with_the_rows():
    rows = [{"week_start": "2026-10-26", "pt": "a", "tasks": 900, "hrs": 100},     # 2.5x its baseline 3.6
            {"week_start": "2026-10-26", "pt": "b", "tasks": 10, "hrs": 10},       # rarely used, baseline 200
            {"week_start": "2026-10-26", "pt": "c", "tasks": 5, "hrs": 5}]         # no baseline: left out
    w = A.weighted_eff_vs_bl(rows, {"a": 3.6, "b": 200.0})
    assert w == {"2026-10-26": round((900 / 3.6 + 10 / 200) * 100 / 110, 1)}
    assert A._eff_vs_bl_from_baselines(9.15 / 1.1, ["a", "b"], {"a": 3.6, "b": 200.0}) < 10   # old way: ~8%


# ── Work-mix guard ──────────────────────────────────────────────────────────────────────────────────

def test_work_mix_change_is_not_read_as_faster_production():
    prev = {"prod_tasks": 100, "total_qc": 60, "accepted": 60, "prod_hrs": 115, "qc_hrs": 4.5}     # 69 min/task
    cur = {"prod_tasks": 1810, "total_qc": 1147, "accepted": 1142, "prod_hrs": 241, "qc_hrs": 86}  # 8 min/task
    d = R.coq_drivers(cur, prev)
    assert d["mix"]
    action, causes, _ = R.coq_texts(d, [], 0, 0, 92)
    assert "work mix changed a lot" in causes[0] and not any("Faster production" in c for c in causes)
    out = R.analyse([], [], [cur, prev], {}, [], 92, 95, False)
    assert out["coq"]["action"].startswith("Review the sampling: 63% of tasks are QC'd")
    assert any("Why it is at" in c for c in out["coq"]["causes"])


def test_normal_weeks_are_not_a_mix_change():
    w1 = {"prod_tasks": 1000, "total_qc": 100, "accepted": 97, "prod_hrs": 200, "qc_hrs": 10}
    w2 = {"prod_tasks": 1000, "total_qc": 160, "accepted": 140, "prod_hrs": 200, "qc_hrs": 16}
    assert not R.coq_drivers(w2, w1)["mix"]


# ── No repeated KPI actions; labels ─────────────────────────────────────────────────────────────────

def test_old_action_list_leaves_out_kpis_the_box_explains():
    rc = {"coq": {"action": "Lower the sampling", "causes": ["c"], "more": []}}
    an = {**AN, "root_cause": rc}
    assert E.box_covered(an, {"coq", "fta"}) == {"coq"}
    old = text(E._build_actions({}, an, primary_metrics=["coq"]))
    assert "audit rework" not in old.lower() and "CoQ 13.87% (RED)" not in old


def test_blank_work_unit_is_named_as_not_recorded():
    assert R._wu("") == "work unit not recorded" and R._wu("dpu noida") == "DPU Noida"
