"""Per-process-type daily briefing (5 Nov 2026): each process type against its own baseline, weekly trend,
mix note, and an overall strip with only combinable numbers. Functional, technical and performance cases."""
import re
import time
from datetime import date, timedelta

import analytics_agent as A
import email_briefing_pt as P

WEEKS = A.trend_mondays("2026-11-02")


def text(html):
    """Visible text of an email, whitespace collapsed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def rows_for(pt, per_week, baseline=None):
    """_PT_TREND_SQL-shaped rows: per_week = [(accepted, qc, tasks, prod_hrs, qc_hrs)], oldest first."""
    return [{"week_start": wk, "pt": pt, "accepted": a, "total_qc": q, "tasks": t, "prod_hrs": ph, "qc_hrs": qh,
             "baseline_avg": baseline} for wk, (a, q, t, ph, qh) in zip(WEEKS[-len(per_week):], per_week)]


# ── Functional ────────────────────────────────────────────────────────────────

def test_trend_weeks_are_eight_mondays_ending_with_the_reported_week():
    assert WEEKS[-1] == "2026-11-02" and len(WEEKS) == 8 and WEEKS[0] == "2026-09-14"
    assert all(date.fromisoformat(w).weekday() == 0 for w in WEEKS)


def test_each_process_type_uses_only_its_own_baseline():
    rows = rows_for("a", [(95, 100, 100, 10, 0)]) + rows_for("b", [(90, 100, 100, 100, 0)])
    by_pt, overall = A.pt_trends(rows, {"a": 10.0, "b": 0.5}, WEEKS)
    assert by_pt["a"]["weeks"][-1]["eff_vs_bl"] == 100.0       # 10 tasks/hr vs 10
    assert by_pt["b"]["weeks"][-1]["eff_vs_bl"] == 200.0       # 1 task/hr vs 0.5
    # overall = earned hours (10 + 200) over booked hours (110), not tasks/hr vs an averaged baseline
    o = overall[-1]
    assert o["earned_hrs"] == 210.0 and o["booked_hrs"] == 110.0 and o["eff_vs_bl"] == round(210 / 110 * 100, 1)
    assert o["fta"] == 92.5                                    # pooled: 185 / 200


def test_process_type_without_baseline_gets_no_efficiency_and_is_left_out_of_the_overall():
    rows = rows_for("a", [(95, 100, 100, 10, 0)]) + rows_for("x", [(90, 100, 100, 50, 0)])
    by_pt, overall = A.pt_trends(rows, {"a": 10.0}, WEEKS)
    assert by_pt["x"]["baseline"] is None and by_pt["x"]["weeks"][-1]["eff_vs_bl"] is None
    assert overall[-1]["eff_vs_bl"] == 100.0 and overall[-1]["hrs_no_bl"] == 50.0


def test_row_baseline_is_used_when_the_baselines_view_has_none():
    by_pt, _ = A.pt_trends(rows_for("a", [(9, 10, 20, 10, 0)], baseline=4.0), {}, WEEKS)
    assert by_pt["a"]["baseline"] == 4.0 and by_pt["a"]["weeks"][-1]["eff_vs_bl"] == 50.0


def test_trend_word_needs_three_full_weeks_the_same_way():
    assert A.trend_word([97, 96, 95, 94], "fta") == "worsening"
    assert A.trend_word([5, 6, 7, 8], "coq") == "worsening"          # CoQ up is worse
    assert A.trend_word([90, 95, 100, 105], "eff") == "improving"
    assert A.trend_word([97, 96, 97, 96], "fta") == "steady"
    assert A.trend_word([97.0, 96.9, 96.8, 96.7], "fta") == "steady"  # moves too small in total
    assert A.trend_word([97, 96, 95], "fta") == ""                   # too little history
    assert A.trend_word([97, None, 96, 95, 94], "fta") == "worsening"  # gaps are skipped


def test_mix_split_names_the_mix_when_hours_move_to_a_slower_process_type():
    prev = {"fast": (100, 120.0), "slow": (100, 60.0)}               # overall 90
    now = {"fast": (20, 120.0), "slow": (180, 60.0)}                 # overall 66, no process type changed
    s = A.mix_split(now, prev)
    assert s["total"] == -24.0 and s["rate"] == 0.0 and s["mix"] == -24.0


def test_mix_split_weights_by_this_week_so_a_stopped_process_type_barely_counts():
    prev = {"big": (1489, 100.0), "main": (500, 80.0)}
    now = {"big": (13, 8.0), "main": (500, 80.0)}
    s = A.mix_split(now, prev)
    assert s["by_pt"][0][0] == "big" and abs(s["by_pt"][0][1]) < 3     # was -57.6 at last week's weights


def _analytics(today_week="2026-11-02"):
    """A small analytics result with two process types, one healthy, one below its baseline."""
    t = lambda fta, eff, coq, hrs, qc=50: [{"week": w, "fta": fta, "eff_vs_bl": eff, "coq": coq, "qc": qc,
                                           "tasks": 100, "hrs": hrs} for w in WEEKS]
    good = {"process_type": "geo-good", "fta_pct": 99.0, "fta_rag": "GREEN", "efficiency": 5.5, "eff_vs_bl": 110.0,
            "has_prod": True, "coq_pct": 3.0, "prod_tasks": 500, "total_qc": 60, "total_hrs": 100.0,
            "own_baseline": 5.0, "trend": t(99.0, 110.0, 3.0, 100.0)}
    bad = {"process_type": "geo-bad", "fta_pct": 90.0, "fta_rag": "RED", "efficiency": 1.6, "eff_vs_bl": 80.0,
           "has_prod": True, "coq_pct": 14.0, "prod_tasks": 300, "total_qc": 80, "total_hrs": 300.0,
           "own_baseline": 2.0, "trend": t(90.0, 80.0, 14.0, 300.0),
           "work_units": [{"name": n, "work_unit": n.lower(), "total_hrs": h, "fta_pct": f, "fta_rag": "RED",
                           "eff_vs_bl": 80.0, "coq_pct": 14.0, "prod_tasks": 150, "total_qc": 40}
                          for n, h, f in (("OCC", 200, 88.0), ("DPU Noida", 100, 94.0))]}
    noref = {"process_type": "geo-noref", "fta_pct": 99.5, "fta_rag": "GREEN", "efficiency": 3.0, "eff_vs_bl": 75.0,
             "eff_from_scope_average": True, "has_prod": True, "coq_pct": 2.0, "prod_tasks": 50, "total_qc": 20,
             "total_hrs": 20.0, "own_baseline": None, "trend": t(99.5, None, 2.0, 20.0)}
    ot = [{"week": w, "fta": 94.0, "coq": 10.0, "eff_vs_bl": 88.0, "earned_hrs": 352.0, "booked_hrs": 400.0,
           "hrs_no_bl": 20.0, "hrs": 420.0, "qc": 160} for w in WEEKS]
    return {"week_label": today_week, "process_breakdown": [good, bad, noref], "overall_trend": ot,
            "fta_current": 94.0, "fta_rag": "AMBER", "efficiency_vs_bl": 88.0, "efficiency_rag": "RED",
            "efficiency_raw": 2.1, "coq_current": 10.0, "coq_rag": "RED_P1", "prod_hrs": 380, "qc_hrs": 40,
            "yield_current": None}


SKILL = {"project_name": "Lanes", "jira_project": "OM", "primary_metrics": ["fta", "efficiency", "coq"],
         "domain": "Project Manager"}
JIRA = {"open_tickets": [], "sla_breaches": [], "sla_warnings": [], "total_open": 7}


def test_briefing_leads_with_cards_for_process_types_that_need_attention():
    html = P.build(JIRA, _analytics(), {}, SKILL)
    t = text(html)
    assert "1 of 3 need attention" in t
    assert t.index("Total") < t.index("Needs attention (1)")        # table first, then the cards
    card = t[t.index("Needs attention (1)"):]
    assert "geo-bad" in card and "geo-good" not in card
    assert "Efficiency vs its own baseline 80% past the alert level" in card
    assert "Work units: OCC 200 h (FTA 88.0%) · DPU Noida 100 h (FTA 94.0%)" in card


def test_no_combined_tasks_per_hour_or_averaged_baseline_anywhere():
    t = text(P.build(JIRA, _analytics(), {}, SKILL))
    assert "average of the process types" not in t
    assert "20 h on process types without a baseline are not in the efficiency total" in t


def test_table_rows_use_own_baselines_and_the_total_adds_up():
    t = text(P.build(JIRA, _analytics(), {}, SKILL))
    # geo-bad: 300 tasks, 300 h, actual 1.600 vs own baseline 2.000 -> 240 h at baseline, 80%
    assert "geo-bad 300 300 1.600 2.000 240 80%" in t
    assert "geo-good 500 100 5.500 5.000 110 110%" in t
    # Total: hours 420, hours at baseline 350 over 400 h booked = 88%; FTA 151.3/160; CoQ 4540/420
    assert "Total 420 350 88% 94.6% 10.8%" in t


def test_total_leaves_tasks_and_tasks_per_hour_empty():
    total = P._sum_numbers([P._row_numbers(p) for p in _analytics()["process_breakdown"]])
    assert total["tasks"] is None and total["actual"] is None and total["bl"] is None
    assert round(total["eff"], 1) == 87.5 and total["booked"] == 400.0


def test_rows_past_the_limit_fold_into_one_other_row_and_still_add_up():
    a = _analytics()
    base = a["process_breakdown"][0]
    a["process_breakdown"] = [{**base, "process_type": f"pt-{i}"} for i in range(P.MAX_ROWS + 3)]
    t = text(P.build(JIRA, a, {}, SKILL))
    assert "Other 3 process types 300 330 110%" in t
    assert f"Total {100 * (P.MAX_ROWS + 3):,} {110 * (P.MAX_ROWS + 3):,} 110%" in t


def test_scope_average_fallback_is_shown_as_no_baseline():
    t = text(P.build(JIRA, _analytics(), {}, SKILL))
    assert "75.0% of baseline" not in t and "75%" not in t          # nowhere, also not in the actions box
    row = t[t.rindex("geo-noref"):t.rindex("geo-noref") + 80]
    assert "no baseline" in row


def test_current_week_is_marked_so_far_and_left_out_of_trend_words():
    this_monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    assert P._in_progress(this_monday) and not P._in_progress("2020-01-06")
    series = [{"week": this_monday, "fta": 50.0}, {"week": "2020-01-06", "fta": 99.0}]
    assert P._full_weeks(series, "fta") == [99.0]


def test_small_sample_is_never_judged():
    p = {"total_qc": 5, "fta_pct": 50.0, "eff_vs_bl": 20.0, "coq_pct": 40.0, "trend": []}
    assert P._pt_rags(p, {"fta", "efficiency", "coq"}) == {} and not P.needs_attention(p, {"fta"})


def test_only_profile_metrics_colour_a_process_type():
    p = {"total_qc": 50, "fta_pct": 99.0, "eff_vs_bl": 50.0, "coq_pct": 2.0, "trend": []}
    assert not P.needs_attention(p, {"fta", "coq"})                 # efficiency not in the profile
    assert P.needs_attention(p, {"efficiency"})


def test_fta_levels_come_from_config():
    from config import FTA_ALERT, FTA_TARGET
    assert P._rag_fta(FTA_TARGET) == "GREEN" and P._rag_fta(FTA_ALERT) == "AMBER"
    assert P._rag_fta(FTA_ALERT - 0.01) == "RED"


def test_jira_section_lists_only_tickets_past_or_close_to_the_sla():
    br = {"key": "OM-1", "summary": "late", "assignee": "a", "hours_stale": 100, "sla_status": "BREACH_72H",
          "url": "https://x/OM-1"}
    j = {"open_tickets": [br, {"key": "OM-2", "summary": "fine", "sla_status": "OK"}], "sla_breaches": [br],
         "sla_warnings": [], "total_open": 2}
    t = text(P.build(j, _analytics(), {}, SKILL))
    assert "OM-1" in t and "OM-2" not in t and "2 open tickets in scope" in t


def test_operational_lead_gets_operators_before_planning_ids():
    a = _analytics()
    a["operator_breakdown"] = [{"operator": "op one", "process_type": "geo-bad", "work_unit": "OCC", "fta_pct": 80.0,
                                "eff_vs_bl": 50.0, "coq_pct": 20.0, "total_hrs": 30, "prod_tasks": 40,
                                "breaches": ["fta"]}]
    a["planning_breakdown"] = [{"planning_id": "P-1", "fta_pct": 95.0, "fta_rag": "GREEN", "eff_vs_bl": 100.0,
                                "coq_pct": 5.0, "total_qc": 10, "prod_tasks": 20, "total_hrs": 10.0}]
    lead = text(P.build(JIRA, a, {}, {**SKILL, "domain": "Operational Lead"}))
    pmgr = text(P.build(JIRA, a, {}, SKILL))
    assert lead.index("Operators —") < lead.index("Planning IDs")
    assert pmgr.index("Planning IDs") < pmgr.index("Operators —")


def test_yield_above_100_is_not_shown():
    a = _analytics()
    a["process_breakdown"][1]["yield_pct"] = 147.9
    t = text(P.build(JIRA, a, {}, SKILL))
    assert "147.9" not in t and "reads above 100%" in t


def test_far_below_baseline_for_weeks_asks_to_check_the_baseline():
    old = [{"week": w, "eff_vs_bl": 15.0} for w in ("2026-09-14", "2026-09-21", "2026-09-28", "2026-10-05",
                                                    "2026-10-12", "2026-10-19")]
    assert P.baseline_suspect({"trend": old})
    assert not P.baseline_suspect({"trend": old[:-1] + [{"week": "2026-10-19", "eff_vs_bl": 60.0}]})
    assert not P.baseline_suspect({"trend": old[:4]})                     # too few weeks
    a = _analytics()
    a["process_breakdown"][1]["trend"] = [{**w, "eff_vs_bl": 15.0} for w in a["process_breakdown"][1]["trend"]]
    assert "the baseline itself may be wrong" in text(P.build(JIRA, a, {}, SKILL))


def test_long_sla_list_is_cut_to_the_oldest():
    ts = [{"key": f"OM-{i}", "summary": "s", "assignee": "a", "hours_stale": i, "sla_status": "BREACH_72H", "url": "u"}
          for i in range(40)]
    t = text(P.build({**JIRA, "sla_breaches": ts, "total_open": 40}, _analytics(), {}, SKILL))
    assert "OM-39" in t and "OM-0 " not in t and "25 more" in t


def _with_yield(a):
    """Give geo-good and geo-bad Yield numerators / denominators in every trend week."""
    for p, (num, den) in zip(a["process_breakdown"], ((96, 100), (180, 200))):
        for w in p["trend"]:
            w.update(y_num=num, y_den=den, **{"yield": round(num * 100 / den, 2)})
        p["yield_pct"] = round(num * 100 / den, 2)
    return a


def test_yield_is_in_the_table_and_the_total_pools_it():
    t = text(P.build(JIRA, _with_yield(_analytics()), {}, SKILL))
    assert "geo-good 500 100 5.500 5.000 110 110% 99.0% 3.0% 96.0%" in t
    assert "geo-bad 300 300 1.600 2.000 240 80% 90.0% 14.0% 90.0%" in t
    assert "Total 420 350 88% 94.6% 10.8% 92.0%" in t                 # (96 + 180) / (100 + 200)


def test_yield_has_its_own_trend_row_and_word():
    a = _with_yield(_analytics())
    a["process_breakdown"][1]["trend"][-5:-1] = [{**w, "yield": v} for w, v in
                                                zip(a["process_breakdown"][1]["trend"][-5:-1], (96, 95, 94, 93))]
    assert P._words(a["process_breakdown"][1])["yield"] == "worsening"
    card = text(P.build(JIRA, a, {}, {**SKILL, "primary_metrics": ["fta", "efficiency", "coq", "yield"]}))
    card = card[card.index("Needs attention"):]
    assert " Yield " in card and "Yield 90.0% past the alert level and worsening for 3 weeks in a row" in card


def test_add_yield_trend_fills_each_week():
    by_pt = {"a": {"weeks": [{"week": w} for w in WEEKS]}}
    A.add_yield_trend(by_pt, [{"week_mon": WEEKS[-1], "pt": "A", "yield_num": 45, "yield_den": 50}])
    assert by_pt["a"]["weeks"][-1]["yield"] == 90.0 and by_pt["a"]["weeks"][0]["yield"] is None


def test_no_combined_trend_under_the_table():
    t = text(P.build(JIRA, _with_yield(_analytics()), {}, SKILL))
    assert "Total, last" not in t


def test_no_yield_data_says_orbit_sd_only():
    t = text(P.build(JIRA, _analytics(), {}, SKILL))
    assert "Yield exists for Orbit SD work only" in t


def test_yield_trend_query_is_read_only():
    sql = A._YIELD_PT_TREND_SQL.format(view="v", first_week="2026-09-14", last_week="2026-11-02", scope_filter="")
    assert sql.lstrip().upper().startswith("SELECT")
    assert not re.search(r"(INSERT|UPDATE|DELETE|MERGE|DROP|CREATE)", sql.upper())


# ── Technical ─────────────────────────────────────────────────────────────────

def test_no_scope_profile_gets_no_figures():
    a = {"no_scope": True, "week_label": "", "process_breakdown": [], "overall_trend": []}
    t = text(P.build(JIRA, a, {}, {**SKILL, "no_databricks_scope": True}))
    assert "Add your scope" in t and "Your process types" not in t and "overall (weighted)" not in t


def test_missing_trend_still_renders_this_week():
    a = _analytics()
    for p in a["process_breakdown"]:
        p.pop("trend")
    a["overall_trend"] = []
    t = text(P.build(JIRA, a, {}, SKILL))
    assert "geo-bad" in t and "What changed" not in t


def test_jira_text_is_escaped():
    br = {"key": "OM-1", "summary": "<script>x</script>", "assignee": "a", "hours_stale": 1,
          "sla_status": "BREACH_72H", "url": "u"}
    html = P.build({**JIRA, "sla_breaches": [br]}, _analytics(), {}, SKILL)
    assert "<script>" not in html


def test_trend_query_is_read_only_and_scoped():
    sql = A._PT_TREND_SQL.format(table="t", weeks="'2026-11-02'", scope_filter="AND processType = 'x'")
    assert sql.lstrip().upper().startswith("SELECT") and "AND processType = 'x'" in sql
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|CREATE)\b", sql.upper())


def test_classic_layout_is_unchanged_by_the_new_fields():
    import email_html as E
    a = _analytics()
    a.update(process_breakdown=[{k: v for k, v in p.items() if k not in ("trend", "own_baseline", "eff_from_scope_average")}
                                for p in a["process_breakdown"]])
    plain = E.build(JIRA, a, {}, SKILL)
    a2 = _analytics()
    extra = E.build(JIRA, a2, {}, SKILL)
    strip = lambda h: re.sub(r"\d{2}:\d{2} UTC", "", h)
    assert strip(plain) == strip(extra)


# ── Performance ───────────────────────────────────────────────────────────────

def test_large_scope_renders_fast_and_folds_the_rest():
    a = _analytics()
    base = a["process_breakdown"][1]
    a["process_breakdown"] = [{**base, "process_type": f"pt-{i}", "total_hrs": 1000 - i} for i in range(60)]
    start = time.perf_counter()
    html = P.build(JIRA, a, {}, SKILL)
    assert time.perf_counter() - start < 1.0
    t = text(html)
    assert t.count("past the alert level") >= P.MAX_CARDS and "52 more process types need attention" in t
    assert "Other 48 process types" in t
    assert len(html) < 400_000


def test_pt_trends_handles_a_big_scope_quickly():
    rows = [r for i in range(150) for r in rows_for(f"pt{i}", [(90, 100, 100, 50, 5)] * 8, baseline=2.0)]
    start = time.perf_counter()
    by_pt, overall = A.pt_trends(rows, {}, WEEKS)
    assert time.perf_counter() - start < 1.0 and len(by_pt) == 150 and len(overall) == 8
