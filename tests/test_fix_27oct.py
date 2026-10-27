"""Fixes from the 27 Oct 09:00 run check: subject project name, operator Yield above 100%, the production-hours
bar for alerts, Jira paging past 100 tickets, ticket lists capped in the email, the worst 20 operators."""
import email_html as E
import trigger_engine as T
from agents import analytics_agent as A
from agents import jira_agent as J


def test_subjects_use_the_jira_key_not_project():
    assert T.project_name_of({"jira_project": "OM"}) == "OM"
    src = open(T.__file__, encoding="utf-8").read()
    assert 'skill.get("project_name") or "Project"' not in src


def test_alerts_also_wait_for_production_hours():
    assert A.alert_hours_too_early(86.5, 599.7) == 120       # Devika on 27 Oct: CoQ read 36%
    assert A.alert_hours_too_early(150, 599.7) is None
    assert A.alert_hours_too_early(5, 0) is None             # no hours last week: no bar
    note = E.alert_week_note({"early_week": {"qc": 255, "needed": None, "hrs": 86, "needed_hrs": 120}})
    assert "86 production h so far, alerts use it from 120 h" in note and "QC&apos;d" not in note


def test_operator_yield_above_100_is_left_out_with_a_note():
    ops = [{"operator": "a", "process_type": "pt", "fta_pct": 80.0, "coq_pct": 5.0, "eff_vs_bl": 99.0,
            "yield_pct": None, "yield_over_100": True, "total_hrs": 10, "sampling_pct": 20.0, "breaches": ["fta"],
            "severity": 0.1}]
    h = E._build_operator_breakdown({"operator_breakdown": ops, "week_label": "2026-10-26",
                                     "operator_levels": {"fta": {"alert": 92.0, "direction": "drop"}}})
    assert "Yield is left out where it reads above 100%" in h


def test_worst_20_operators_by_how_far_past_their_level():
    levels = {"fta": {"alert": 90.0, "direction": "drop"}}
    ops = [{"operator": f"op{i}", "process_type": "pt", "fta_pct": 89.0 - i, "total_qc": 50, "prod_tasks": 50,
            "coq_pct": 1.0, "total_hrs": 5} for i in range(30)]
    A.mark_operator_breaches(ops, levels)
    h = E._build_operator_breakdown({"operator_breakdown": ops, "week_label": "2026-10-26", "operator_levels": levels})
    assert "30 of 30</b> operators" in h and "(the worst 20 shown)" in h
    assert ">op29</td>" in h and ">op10</td>" in h and ">op9</td>" not in h      # op29 is furthest below


def test_ticket_lists_stay_at_100_rows_with_the_rest_counted():
    ts = [{"key": f"OM-{i}", "summary": "s", "status": "Open", "assignee": "x", "url": "u",
           "hours_stale": float(i), "sla_status": "BREACH_72H"} for i in range(250)]
    shown = E.shown_tickets(ts)
    assert len(shown) == 100 and shown[0]["key"] == "OM-249"        # oldest without update first
    assert "150 more" in E.more_in_jira(ts) and E.more_in_jira(ts[:100]) == ""
    assert "150 more" in E._build_tickets({"open_tickets": ts})


def test_jira_rest_pages_past_100(monkeypatch):
    pages = [{"issues": [{"key": f"OM-{i}", "fields": {"updated": "2026-10-01T00:00:00.000+0000"}} for i in range(n, n + 100)],
              "nextPageToken": f"t{n}", "isLast": False} for n in (0, 100)] + \
            [{"issues": [{"key": "OM-200", "fields": {"updated": "2026-10-01T00:00:00.000+0000"}}], "isLast": True}]
    calls = []

    class R:
        def __init__(self, d): self.d = d
        def raise_for_status(self): pass
        def json(self): return self.d

    def post(url, json, headers, timeout):
        calls.append(json.get("nextPageToken"))
        return R(pages[len(calls) - 1])

    monkeypatch.setattr(J, "JIRA_API_TOKEN", "x")
    monkeypatch.setattr(J.atlassian_mcp, "enabled", lambda: False)
    monkeypatch.setattr(J.httpx, "post", post)
    r = J.run({"jira_project": "OM", "user": "a@tomtom.com"})
    assert r["total_open"] == 201 and calls == [None, "t0", "t100"]
