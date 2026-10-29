"""Root causes and actions (root_cause.py, 29 Oct): driver trees for FTA, CoQ, efficiency and yield, the
email box that shows them, and operators grouped by work unit."""
import math
import re

import email_html as E
import root_cause as R


def ed(editor, wu, qc, acc, week="2026-10-26", pt="pt-a", qc_h=1.0):
    return {"week": week, "pt": pt, "wu": wu, "editor": editor, "qc": qc, "acc": acc, "qc_h": qc_h}


def text(s):
    return re.sub(r"<[^>]+>", "", s)


# ── FTA ─────────────────────────────────────────────────────────────────────────────────────────────

def test_few_editors_with_most_rejections_means_coaching_by_work_unit():
    eds = [ed("a", "dpu noida", 20, 10), ed("b", "dpu noida", 20, 12), ed("c", "occ", 20, 17)] + \
          [ed(f"x{i}", "occ", 50, 50) for i in range(10)]
    c = R.fta_causes(eds, [], 92)
    assert c["low"] == 3 and c["judged"] == 13 and c["rejections"] == 21 and c["concentrated"]
    assert c["by_wu"][0]["work_unit"] == "dpu noida" and c["by_wu"][0]["editors"] == 2
    action, causes, more = R.fta_texts(c, has_operator_section=True)
    assert action.startswith("Coach the 3 editors below 92% FTA, starting with DPU Noida (2 editors, 86% of rejections)")
    assert "operator section" in action and "3 of 13 editors" in text(causes[0])
    assert R.ERROR_TYPES_NOTE in more[-1]


def test_rejections_spread_over_one_package_point_at_the_package():
    eds = [ed(f"e{i}", "occ", 9, 8) for i in range(12)]          # nobody judged (< 10 QC'd), spread thin
    wps = [{"pt": "pt-a", "wu": "occ", "wp": "WP-1", "qc": 60, "acc": 50, "eds": 6}]
    action, causes, _ = R.fta_texts(R.fta_causes(eds, wps, 92), False)
    assert action.startswith("Review the instructions, specs and source data of work package WP-1")
    assert "across 6 editors" in text(causes[0])


def test_fta_drop_from_the_sample_is_called_a_sampling_effect():
    prev = [ed("low", "occ", 20, 16, week="2026-10-19")] + [ed(f"g{i}", "occ", 40, 40, week="2026-10-19") for i in range(4)]
    cur = [ed("low", "occ", 80, 64)] + [ed(f"g{i}", "occ", 40, 40) for i in range(4)]
    causes, more = R.fta_change(cur, prev, 92)
    t = " ".join(map(text, causes))
    assert "FTA fell from 97.8% to 93.3% (4 → 16 rejections" in t
    assert "more of the sample came from editors already below 92% last week (11% → 33%" in t
    assert "The other editors are at 100.0%" in t and "sampling effect" in more[0]


def test_fta_about_the_same_says_so():
    prev = [ed("a", "occ", 100, 96, week="2026-10-19")]
    assert "about the same" in R.fta_change([ed("a", "occ", 100, 96)], prev, 92)[0][0]


# ── CoQ ─────────────────────────────────────────────────────────────────────────────────────────────

W1 = {"prod_tasks": 1000, "total_qc": 100, "accepted": 97, "prod_hrs": 200, "qc_hrs": 10}


def test_coq_split_is_exact_and_names_rejections_then_sampling():
    w2 = {"prod_tasks": 1000, "total_qc": 160, "accepted": 140, "prod_hrs": 200, "qc_hrs": 16}
    d = R.coq_drivers(w2, W1)
    ratio = math.log((16 / 200) / (10 / 200))
    assert abs(sum(d["terms"].values()) - ratio) < 1e-9          # the drivers add up to the whole move
    assert d["rising"] and set(d["order"]) == {"rejections", "sampling"}
    action, causes, more = R.coq_texts(d, [], 0, 0, 92)
    t = " ".join(causes)
    assert "CoQ rose from 4.8% to 7.4%" in t
    assert "Chain: more rejections (FTA 97.0% → 87.5%) → the sampling rule" in t
    assert action in (R._COQ_ACTION["rejections"], R._COQ_ACTION["sampling"])


def test_slower_qc_with_more_edited_tasks_is_the_edits_chain():
    w2 = {**W1, "qc_hrs": 15}
    d = R.coq_drivers(w2, W1)
    assert d["main"] == "qc_speed"
    action, causes, more = R.coq_texts(d, [], 0, 0, 92, edited={"prev": 60, "cur": 75, "cur_closed": 900})
    t = " ".join(causes)
    assert action.startswith("Find out why QC takes longer per task")
    assert "Slower QC: 6.0 → 9.0 QC minutes" in t
    assert "more tasks closed with a map edit (Publish / Accepted): 60% → 75%" in t
    assert any("plan QC capacity" in m for m in more)
    _, causes2, _ = R.coq_texts(d, [], 0, 0, 92, edited={"prev": 70, "cur": 70, "cur_closed": 900})
    assert any("not from more edited tasks" in c for c in causes2)


def test_fta_up_but_sampling_up_is_flagged():
    w2 = {"prod_tasks": 1000, "total_qc": 150, "accepted": 148, "prod_hrs": 200, "qc_hrs": 15}
    _, causes, _ = R.coq_texts(R.coq_drivers(w2, W1), [], 0, 0, 92)
    assert any("sampling is not following the better quality" in c for c in causes)


def test_coq_level_gives_the_sampling_that_reaches_the_target():
    d = R.coq_drivers(W1, W1)
    s = text(R.coq_level({**d["cur"], "coq": 15.0}, 7.0))
    # 7/93 * 12 min production / 6 min QC = 15.05%
    assert "CoQ reaches 7% with about 15% sampling" in s
    assert R.coq_level({**d["cur"], "coq": 5.0}, 7.0) == ""


def test_oversampled_needs_high_fta_and_high_rate():
    wps = [{"pt": "p", "wu": "occ", "qc": 30, "acc": 30, "tasks": 100, "qc_h": 9},
           {"pt": "q", "wu": "occ", "qc": 30, "acc": 25, "tasks": 100, "qc_h": 9}]
    assert [o["pt"] for o in R.oversampled(wps)] == ["p"]


# ── Efficiency and yield ────────────────────────────────────────────────────────────────────────────

def test_slow_packages_by_hours_lost_and_idle_hours():
    wps = [{"pt": "pt-a", "wu": "occ", "wp": "SLOW", "tasks": 40, "prod_h": 30, "qc_h": 2, "idle_h": 0},
           {"pt": "pt-a", "wu": "occ", "wp": "OK", "tasks": 100, "prod_h": 25, "qc_h": 0, "idle_h": 12}]
    slow, lost = R.slow_packages(wps, {"pt-a": 4.0})
    assert [s["wp"] for s in slow] == ["SLOW"] and abs(slow[0]["lost"] - 22) < 1e-9 and abs(lost - 22) < 1e-9
    action, causes, more = R.eff_texts(slow, lost, R.idle_hours(wps))
    assert action.startswith("Check work package SLOW for blockers")
    assert "31% of baseline, 22 h lost" in text(causes[0]) and "12 h booked with no completed task" in text(causes[1])


def test_yield_names_the_lowest_work_unit():
    a, c, _ = R.yield_texts([{"work_unit": "dpu noida", "yield_pct": 88.0, "total_qc": 40},
                             {"work_unit": "occ", "yield_pct": 99.0, "total_qc": 40}], 95)
    assert "DPU Noida" in a and "DPU Noida 88.0%" in c[0]


def test_analyse_splits_the_two_weeks_and_says_what_is_missing():
    eds = [ed("a", "occ", 20, 10), ed("a", "occ", 20, 19, week="2026-10-19")] + [ed(f"g{i}", "occ", 40, 40) for i in range(3)]
    out = R.analyse(eds, [], [], {}, [], 92, 95, False)
    assert out["fta"]["facts"]["judged"] == 4          # only the reported week is judged
    assert "previous full week" in out["fta"]["causes"][0] and out["partial"] == R.ERROR_TYPES_NOTE


# ── In the email ────────────────────────────────────────────────────────────────────────────────────

AN = {"live": True, "week_label": "2026-10-19", "fta_current": 90.0, "fta_rag": "RED", "coq_rag": "GREEN",
      "efficiency_rag": "GREEN", "metrics_4w": [], "process_breakdown": []}


def test_box_shows_the_driver_tree_with_next_actions_and_the_partial_note():
    rc = {"fta": {"action": "Coach the 3 editors below 92% FTA", "causes": ["Cause one.", "Cause two."],
                  "more": ["Ask QC."]}, "partial": R.ERROR_TYPES_NOTE}
    items = E.action_items({}, {**AN, "root_cause": rc}, {"fta"})
    assert items[0][1] == "FTA 90.00%: Coach the 3 editors below 92% FTA"
    assert "1. Cause one." in items[0][2] and "2. Cause two." in items[0][2] and "Next:" in items[0][2]
    assert "Ask QC." in E._build_action_box({}, {**AN, "root_cause": rc}, {"fta"})


def test_box_falls_back_without_root_cause_rows():
    items = E.action_items({}, AN, {"fta"})
    assert items[0][1].startswith("Review the rejected tasks behind FTA 90.00%")
    assert "QC feedback categories" not in E._build_action_box({}, AN, {"fta"})


def test_operators_are_grouped_by_work_unit():
    def op(name, wu, hrs):
        return {"operator": name, "work_unit": wu, "process_type": "pt-a", "fta_pct": 80.0, "coq_pct": 5.0,
                "total_hrs": hrs, "prod_tasks": 50, "breaches": ["fta"]}
    ops = [op("A", "OCC", 40), op("B", "DPU Noida", 30), op("C", "OCC", 20), op("D", "DPU Noida", 10),
           op("E", "OCC", 5), {**op("F", "DPU Noida", 1), "breaches": []}]
    html = E._build_operator_breakdown({"operator_breakdown": ops, "week_label": "2026-10-19", "operator_levels": {}})
    t = text(html)
    assert "OCC — 3 of 3 operators past a level" in t and "DPU Noida — 2 of 3 operators past a level" in t
    assert t.index("OCC — 3") < t.index("DPU Noida — 2")              # unit with most operators past first
    assert t.index("AOCC") < t.index("COCC") < t.index("EOCC") < t.index("DPU Noida — 2")
