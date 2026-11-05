"""Per-process-type briefing, 5 Nov 2026 round 4: line charts as trend, crisp recommended actions with their root
cause, operators worst 25 / best 5 judged only with enough work, and inline images in delivery.
Functional, technical and performance cases."""
import re
import sys
import time
import types

import delivery
import email_briefing_pt as P
import root_cause as R
from test_briefing_pt import JIRA, SKILL, WEEKS, _analytics, _with_yield, text


def ed(editor, wu, qc, acc, week="2026-10-26", pt="pt-a", qc_h=1.0):
    """An editor row as root_cause expects."""
    return {"week": week, "pt": pt, "wu": wu, "editor": editor, "qc": qc, "acc": acc, "qc_h": qc_h}


# ── Root cause behind each action ─────────────────────────────────────────────

def test_fta_root_is_the_editors_line_when_coaching():
    eds = [ed("a", "dpu noida", 20, 10), ed("b", "dpu noida", 20, 12), ed("c", "occ", 20, 17)] + \
          [ed(f"x{i}", "occ", 50, 50) for i in range(10)]
    out = R.analyse(eds, [], [], {}, [], 92, 95, True)
    assert out["fta"]["action"].startswith("Coach") and "3</b> of 13 editors" in out["fta"]["root"]


def test_fta_root_is_the_package_line_when_the_package_is_the_action():
    eds = [ed(f"e{i}", "occ", 9, 8) for i in range(12)]
    wps = [{"pt": "pt-a", "wu": "occ", "wp": "WP-1", "qc": 60, "acc": 50, "eds": 6}]
    out = R.analyse(eds, wps, [], {}, [], 92, 95, False)
    assert "work package WP-1" in out["fta"]["action"] and out["fta"]["root"].startswith("Work package")


def test_yield_and_efficiency_roots_are_their_first_cause():
    wus = [{"work_unit": "occ", "yield_pct": 80.0, "total_qc": 50}]
    out = R.analyse([], [], [], {}, wus, 92, 95, False)
    assert out["yield"]["root"].startswith("Lowest yield by work unit: OCC 80.0%")


def test_crisp_box_is_action_plus_one_root_cause():
    a = _analytics()
    a["root_cause"] = {"efficiency": {"action": "Check work package WP-9 for blockers", "causes": ["c1", "c2", "c3"],
                                      "more": ["m1"], "root": "Slowest work packages: <b>WP-9</b> (12% of baseline)"}}
    t = text(P.build(JIRA, a, {}, SKILL))
    box = t[t.index("Recommended actions"):t.index("What changed") if "What changed" in t else None]
    assert "Efficiency 88.0% of baseline: Check work package WP-9 for blockers" in box
    assert "Root cause: Slowest work packages: WP-9 (12% of baseline)" in box
    assert "c2" not in box and "m1" not in box and "Next:" not in box          # no long list


def test_long_root_cause_keeps_its_first_item():
    long = "Slowest: " + "; ".join(f"WP-{i} ({'x' * 40})" for i in range(8))
    short = P._short_root(long)
    assert short.startswith("Slowest: WP-0") and "WP-1" not in short and "and more" in short


def test_jira_item_root_cause_is_the_oldest_ticket():
    br = {"key": "OM-7", "summary": "s", "assignee": "Ana", "hours_stale": 500, "sla_status": "BREACH_72H", "url": "u"}
    t = text(P.build({**JIRA, "sla_breaches": [br]}, _analytics(), {}, SKILL))
    assert "Root cause: No update for more than 72 h. Oldest: OM-7 (Ana, 500 h" in t


# ── Operators: enough production hours, worst 25, best 5 ─────────────────────

def op(name, pt="pt-a", tasks=100, hrs=20.0, prod=None, qc=20, fta=99.0, eff=110.0, coq=4.0, breaches=()):
    """An operator row as analytics_agent builds it (prod = production hours, default = hrs)."""
    return {"operator": name, "process_type": pt, "work_unit": "OCC", "prod_tasks": tasks, "total_hrs": hrs,
            "prod_hrs": hrs if prod is None else prod, "total_qc": qc, "fta_pct": fta, "eff_vs_bl": eff,
            "coq_pct": coq, "yield_pct": None, "breaches": list(breaches)}


def test_one_task_done_well_is_not_best():
    ops = [op(f"o{i}") for i in range(6)] + [op("lucky", tasks=1, hrs=0.5, qc=1, fta=100.0, eff=190.0)]
    worst, best, judged = P.operator_lists(ops)
    assert "lucky" not in [o["operator"] for o in best] and judged == 6


def test_only_production_hours_decide_who_is_judged():
    ops = [op("ok", prod=8.0), op("short", prod=7.9), op("qc-heavy", hrs=30, prod=4), op("few-qc", qc=2),
           op("few-tasks", tasks=3)]
    names = {o["operator"] for o in P.enough_work(ops)}
    assert names == {"ok", "few-qc", "few-tasks"}             # QC hours, QC'd and task counts do not decide


def test_worst_is_most_levels_missed_then_most_production_hours_and_capped():
    ops = [op(f"w{i}", prod=10 + i, breaches=("fta",)) for i in range(30)] + [op("two", prod=9, breaches=("fta", "coq"))]
    worst, _, _ = P.operator_lists(ops)
    assert len(worst) == P.WORST_MAX and worst[0]["operator"] == "two" and worst[1]["operator"] == "w29"


def test_best_is_relative_top_five_not_in_worst_and_no_quality_problem():
    ops = [op(f"g{i}", eff=80 + i) for i in range(8)] + [op("badfta", eff=150, breaches=("fta",)),
           op("misbooked", eff=260.0), op("slowpoke", eff=40.0, breaches=("efficiency",))]
    worst, best, _ = P.operator_lists(ops)
    assert [o["operator"] for o in best] == ["g7", "g6", "g5", "g4", "g3"]      # whole team below baseline
    assert "slowpoke" in [o["operator"] for o in worst] and "badfta" not in [o["operator"] for o in best]


def test_praise_is_factual_and_honest_about_the_baseline():
    assert P.praise(op("x", tasks=420, prod=38, fta=100.0, eff=128.0)) ==         "Top quality at high speed: 420 tasks in 38 production h. Worth a thank-you."
    assert P.praise(op("y", qc=3, eff=105.0)).startswith("Above baseline (105%)")
    assert P.praise(op("z", eff=92.0)).startswith("Best in your team this week at 92% of baseline")


def test_operator_section_shows_worst_and_best_with_the_rule():
    a = _analytics()
    a["operator_breakdown"] = [op(f"w{i}", breaches=("fta",), fta=85.0) for i in range(3)] + [op("star", eff=130.0)]
    a["operator_levels"] = {"fta": {"alert": 92.0, "direction": "fall"}}
    t = text(P.build(JIRA, a, {}, {**SKILL, "domain": "Operational Lead"})).replace("&apos;", "'")
    assert "Needs support — the 3 operators furthest off your levels" in t
    assert "Doing well — top 1 in your team to recognise" in t and "star" in t and "Worth a thank-you" in t
    assert "at least 8 production hours (4 of 4 operators)" in t and "Prod hrs" in t


def test_operator_names_are_escaped():
    a = _analytics()
    a["operator_breakdown"] = [op("<b>x</b>", breaches=("fta",)) for _ in range(2)]
    assert "<b>x</b>" not in P.build(JIRA, a, {}, {**SKILL, "domain": "Operational Lead"})


def test_operator_query_returns_production_hours():
    import analytics_agent as A
    assert "AS prod_hrs" in A._OPERATOR_SQL


# ── Line charts ───────────────────────────────────────────────────────────────

def test_chart_is_a_png_with_a_panel_per_metric_and_yield_only_when_present():
    import briefing_charts as C
    a = _with_yield(_analytics())
    s_y, s_n = a["process_breakdown"][1]["trend"], _analytics()["process_breakdown"][1]["trend"]
    assert [p[0] for p in C.panels_for(s_y)] == ["fta", "eff_vs_bl", "coq", "yield"]
    assert [p[0] for p in C.panels_for(s_n)] == ["fta", "eff_vs_bl", "coq"]
    png = C.trend_png(s_y, in_progress=True)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_cards_get_an_inline_chart_when_images_can_be_sent():
    images = {}
    html = P.build(JIRA, _with_yield(_analytics()), {}, SKILL, images=images)
    assert list(images) == ["trend1"] and 'src="cid:trend1"' in html
    assert "Eff vs own BL" not in html[html.index("Needs attention"):]       # chart instead of the numbers table


def test_without_image_support_the_numbers_table_stays():
    html = P.build(JIRA, _analytics(), {}, SKILL)
    assert "cid:" not in html and "Eff vs own BL" in html[html.index("Needs attention"):]


def test_chart_with_gaps_and_no_current_week_still_draws():
    import briefing_charts as C
    s = [{"week": w, "fta": None if i % 3 == 0 else 97.0, "eff_vs_bl": 90.0, "coq": 5.0} for i, w in enumerate(WEEKS)]
    assert C.trend_png(s, in_progress=False)[:4] == b"\x89PNG"


def test_charts_are_small_and_fast():
    import briefing_charts as C
    s = _with_yield(_analytics())["process_breakdown"][1]["trend"]
    start = time.perf_counter()
    pngs = [C.trend_png(s, True) for _ in range(8)]                         # MAX_CARDS charts in one email
    assert time.perf_counter() - start < 15 and max(len(p) for p in pngs) < 80_000


# ── Delivery of inline images ─────────────────────────────────────────────────

def test_graph_sends_images_inline_with_their_cid(monkeypatch):
    sent = {}

    class R202:
        status_code, content, headers = 202, b"", {}

    monkeypatch.setenv("MAIL_SENDER", "opsai@tomtom.com")
    monkeypatch.setenv("MAIL_CLIENT_SECRET", "x")
    monkeypatch.setattr(delivery, "_graph_access_token", lambda: "tok")
    import httpx
    monkeypatch.setattr(httpx, "post", lambda url, headers=None, json=None, timeout=None: sent.update(json) or R202())
    assert delivery._send_graph("a@tomtom.com", "s", "<img src='cid:trend1'>", inline_images={"trend1": b"\x89PNG"})
    att = sent["message"]["attachments"][0]
    assert att["isInline"] is True and att["contentId"] == "trend1" and att["contentType"] == "image/png"


def test_graph_without_images_sends_no_attachments_key(monkeypatch):
    sent = {}

    class R202:
        status_code, content, headers = 202, b"", {}

    monkeypatch.setenv("MAIL_SENDER", "opsai@tomtom.com")
    monkeypatch.setenv("MAIL_CLIENT_SECRET", "x")
    monkeypatch.setattr(delivery, "_graph_access_token", lambda: "tok")
    import httpx
    monkeypatch.setattr(httpx, "post", lambda url, headers=None, json=None, timeout=None: sent.update(json) or R202())
    assert delivery._send_graph("a@tomtom.com", "s", "<p>x</p>")
    assert "attachments" not in sent["message"]                                # unchanged for every existing email


def test_outlook_marks_each_image_with_its_content_id(monkeypatch):
    props = []

    class Att:
        """A fake Outlook attachment that records the content id it is given."""
        class PropertyAccessor:
            @staticmethod
            def SetProperty(name, value):
                props.append((name, value))

    class Mail:
        """A fake Outlook mail item."""
        def __init__(self):
            self.Attachments = types.SimpleNamespace(Add=lambda path: Att())

        def Send(self):
            pass

    fake = types.ModuleType("win32com.client")
    fake.Dispatch = lambda name: types.SimpleNamespace(CreateItem=lambda kind: Mail())
    pkg = types.ModuleType("win32com")
    pkg.client = fake
    monkeypatch.setitem(sys.modules, "win32com", pkg)
    monkeypatch.setitem(sys.modules, "win32com.client", fake)
    assert delivery._send_outlook("a@tomtom.com", "s", "<p/>", inline_images={"trend1": b"png", "trend2": b"png"})
    assert [v for _, v in props] == ["trend1", "trend2"] and all(n.endswith("0x3712001F") for n, _ in props)


def test_send_email_passes_images_only_when_there_are_some(monkeypatch):
    calls = []
    monkeypatch.setenv("EMAIL_TRANSPORT", "graph")
    monkeypatch.setattr(delivery, "_send_graph", lambda *a, **k: calls.append(k) or True)
    delivery._send_email("a@tomtom.com", "s", "b")
    delivery._send_email("a@tomtom.com", "s", "b", inline_images={"t": b"x"})
    assert calls == [{}, {"inline_images": {"t": b"x"}}]
