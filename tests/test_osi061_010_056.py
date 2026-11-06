"""User-reported OSI items, 6 Nov 2026. Functional, technical and performance cases; no Jira, Databricks or email.

- OSI-061 (Girish): every Jira key of the Active projects is checked, not only the first; a key Jira cannot find
  is named and the others are still checked; only when every key is missing is Jira "not checked".
- OSI-010 (Pranav, rest): the 8-week trend charts also in the UC3 Weekly Report and the UC4 metric alerts; a chart
  that fails is left out and the email still goes.
- OSI-056 (Mahadev/Pranav, part): UC2 lists open tickets with no assignee apart from the SLA lists.
"""
import time
from datetime import datetime, timedelta, timezone

import pytest

import briefing_charts as C
import email_briefing_pt as P
import email_html as E
import email_html_weekly as W
import profile_check as pc
import skill_registry as sr
import trigger_engine as T
from agents import jira_agent as J
from test_briefing_pt import JIRA, SKILL, _analytics, text

HEAD = "| Activity / Project | Planning ID | Jira Key | Role on Project | Status |\n| --- | --- | --- | --- | --- |\n"


def _table(*rows):
    """A 5-column Active Projects table: rows = (name, key, status)."""
    return HEAD + "".join(f"| {n} | — | {k} | PM | {s} |\n" for n, k, s in rows)


def _skill_file(tmp_path, body, email="jane.doe@tomtom.com"):
    """A loaded profile from markdown `body`."""
    p = tmp_path / f"{email}_skill.md"
    p.write_text("# Jane Doe\n" + body, encoding="utf-8")
    return sr.load_skill(p)


# ── OSI-061: keys from the profile ───────────────────────────────────────────

@pytest.mark.parametrize("rows,keys", [
    ([("A", "OM", "Active")], ["OM"]),
    ([("A", "OM", "Active"), ("B", "MCPET", "Active")], ["OM", "MCPET"]),
    ([("A", "OM", "Active"), ("B", "MCPET", "Active"), ("C", "DSM", "Active")], ["OM", "MCPET", "DSM"]),
    ([("A", "OM", "Active"), ("B", "om", "Active"), ("C", "—", "Active"), ("D", "DSM", "On Hold")], ["OM"]),
])
def test_every_active_jira_key_is_read_once_in_table_order(rows, keys):
    text_ = _table(*rows)
    assert sr._extract_jira_projects(text_, keys[0]) == keys
    assert sr._extract_project_config(text_)["jira_project"] == keys[0]       # first key unchanged


def test_old_code_column_keeps_its_single_key():
    old = "| Project | Code | Role on Project | Status |\n| --- | --- | --- | --- |\n" \
          "| x | GDN | PM | Active |\n| y | TMC | PM | Active |\n"
    first = sr._extract_project_config(old)["jira_project"]
    assert first == "GDN" and sr._extract_jira_projects(old, first) == ["GDN"]   # not GDN + TMC


def test_loaded_profile_has_all_keys_and_labels_name_the_checked_ones(tmp_path):
    s = _skill_file(tmp_path, _table(("A", "OM", "Active"), ("B", "MCPET", "Active")))
    assert s["jira_project"] == "OM" and s["jira_projects"] == ["OM", "MCPET"]
    assert sr.jira_label(s) == "OM, MCPET"
    assert sr.jira_label(s, {"missing_keys": ["MCPET"]}) == "OM"
    assert sr.jira_label(s, {"missing_keys": ["OM", "MCPET"]}) == "OM, MCPET"     # none found: name them all
    assert sr.jira_label({"jira_project": "OM"}) == "OM" and sr.jira_label({}) == ""


# ── OSI-061: the Jira search ─────────────────────────────────────────────────

def test_single_key_jql_is_unchanged_and_several_keys_use_one_in_search():
    one, _ = J._build_jql({"jira_project": "OM", "user": "a@tomtom.com"})
    assert one.startswith("project = OM AND statusCategory != Done")
    two, label = J._build_jql({"jira_projects": ["OM", "MCPET"], "jira_project": "OM", "user": "a@tomtom.com"})
    assert two.startswith("project in (OM, MCPET) AND statusCategory != Done") and "project:OM, MCPET" in label


def _issue(key, hours_old, assignee=True, created_days=10):
    """A Jira search issue updated `hours_old` hours ago."""
    now = datetime.now(timezone.utc)
    return {"key": key, "fields": {
        "summary": f"s {key}", "status": {"name": "Open"}, "priority": {"name": "Medium"},
        "assignee": {"displayName": "Ana"} if assignee else None, "reporter": {"displayName": "Bo"},
        "updated": (now - timedelta(hours=hours_old)).isoformat(),
        "created": (now - timedelta(days=created_days)).isoformat()}}


@pytest.fixture
def jira_mcp(monkeypatch):
    """Jira via a fake MCP: records each JQL; `status` decides which keys exist."""
    seen, status = [], {}
    monkeypatch.setattr(J, "JIRA_API_TOKEN", "x")
    monkeypatch.setattr(J.atlassian_mcp, "enabled", lambda: True)
    monkeypatch.setattr(J, "project_status", lambda k: status.get(k, "ok"))
    issues = [_issue("OM-1", 100), _issue("OM-2", 1, assignee=False, created_days=3),
              _issue("MCPET-9", 50, assignee=False, created_days=30)]
    monkeypatch.setattr(J.atlassian_mcp, "search_jira", lambda jql, f, n: seen.append(jql) or {"issues": issues})
    return seen, status


def test_two_keys_both_checked_in_one_search(jira_mcp):
    seen, _ = jira_mcp
    r = J.run({"jira_projects": ["OM", "MCPET"], "jira_project": "OM", "user": "a@tomtom.com"})
    assert len(seen) == 1 and "project in (OM, MCPET)" in seen[0]
    assert r["error"] is None and r["source"] == "Jira OM, MCPET" and "missing_keys" not in r


def test_one_missing_key_is_named_and_the_others_are_still_checked(jira_mcp):
    seen, status = jira_mcp
    status["GDN"] = "missing"
    r = J.run({"jira_projects": ["GDN", "OM", "MCPET"], "jira_project": "GDN", "user": "a@tomtom.com"})
    assert r["error"] is None and r["missing_keys"] == ["GDN"] and "project in (OM, MCPET)" in seen[0]
    assert "GDN not found" in r["key_warning"] and "OM, MCPET are checked" in r["key_warning"]
    assert len(r["sla_breaches"]) == 1                               # OM-1, 100 h without update


def test_all_keys_missing_is_not_checked_and_nothing_is_searched(jira_mcp):
    seen, status = jira_mcp
    status.update({"GDN": "missing", "TMC": "missing"})
    r = J.run({"jira_projects": ["GDN", "TMC"], "jira_project": "GDN", "user": "a@tomtom.com"})
    assert r["project_not_found"] and "'GDN, TMC' not found" in r["error"] and seen == []


def test_single_key_profile_is_never_looked_up_first(monkeypatch, jira_mcp):
    seen, _ = jira_mcp
    monkeypatch.setattr(J, "project_status", lambda k: (_ for _ in ()).throw(AssertionError("looked up")))
    r = J.run({"jira_project": "OM", "user": "a@tomtom.com"})
    assert r["error"] is None and seen[0].startswith("project = OM ")


def test_profile_check_lists_each_missing_key(monkeypatch, tmp_path):
    s = _skill_file(tmp_path, _table(("A", "OM", "Active"), ("B", "QA", "Active"))
                    + "| UC2 | Jira SLA | x | ✅ Active |\n")
    monkeypatch.setattr(pc, "_project_status", lambda k: "missing" if k == "QA" else "ok")
    monkeypatch.setattr(pc, "jira_project_ok", lambda k: (k != "QA", "" if k != "QA" else "was not found"))
    assert [k for k, _ in pc.jira_key_problems(s)] == ["QA"]


# ── OSI-061 + OSI-056 in the emails ──────────────────────────────────────────

def _jira(**extra):
    """A Jira result with one breach and the given extras."""
    br = {"key": "OM-1", "summary": "late", "status": "Open", "assignee": "Ana", "hours_stale": 100,
          "sla_status": "BREACH_72H", "url": "https://x/browse/OM-1"}
    return {"open_tickets": [br], "sla_breaches": [br], "sla_warnings": [], "total_open": 3, **extra}


def test_uc2_lists_not_assigned_tickets_apart_and_caps_them():
    un = [{"key": f"OM-{i}", "summary": "<b>x</b>", "status": "Open", "url": "u", "age_days": 40 - i,
           "created": f"2026-10-{i + 1:02d}"} for i in range(20)]
    html = E.build_sla_alert(_jira(unassigned=un), skill={"jira_project": "OM"})
    t = text(html)
    assert "Not assigned — 20 open ticket(s) with no owner" in t and "OM-0" in t and "OM-14" in t
    assert "OM-15 " not in t and "and 5 more in Jira" in t and "not counted as SLA breaches" in t
    assert "<b>x</b>" not in html                                     # Jira text escaped
    assert "1 SLA breach" in t                                        # the breach count is unchanged


def test_uc2_without_unassigned_or_missing_keys_has_no_new_section():
    t = text(E.build_sla_alert(_jira(unassigned=[]), skill={"jira_project": "OM"}))
    assert "Not assigned" not in t and "not found" not in t and "(OM)" in t


def test_emails_name_every_checked_key_and_the_missing_one():
    s = {**SKILL, "jira_projects": ["GDN", "OM", "MCPET"], "jira_project": "GDN"}
    j = _jira(missing_keys=["GDN"], key_warning="Jira project GDN not found or not visible ...; OM, MCPET are checked.")
    for html in (E.build_sla_alert(j, skill=s), P.build(j, _analytics(), {}, s), W.build(j, _analytics(), {}, skill=s)):
        t = text(html)
        assert "OM, MCPET" in t and "Jira project GDN not found" in t


def test_create_ticket_link_uses_one_project():
    assert "pid=" in E._btn("s", "d", "OM, MCPET") or "OM" in E._btn("s", "d", "OM, MCPET")
    assert "MCPET" not in E._btn("s", "d", "OM, MCPET")


# ── OSI-010: charts in UC3 and UC4 ───────────────────────────────────────────

def test_alert_chart_is_one_metric_with_the_alert_level():
    series = _analytics()["process_breakdown"][1]["trend"]
    png = C.alert_png(series, "fta", 92.0, True)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) < 150_000
    assert C.alert_png(series, "copq", 5.0, True) is None             # no weekly CoPQ series
    assert C.alert_png([{"week": "2026-11-02", "fta": None}], "fta", 92.0, True) is None


def test_uc4_alert_gets_a_chart_per_alerting_process_type():
    a = _analytics()
    rows = T.alerting_rows(a, "fta", 92.0, "drop")
    assert [r["process_type"] for r in rows] == ["geo-bad"]          # 90% < 92%; geo-good 99% is fine
    images = {}
    html = E.build_alert(metric="fta", rag="RED", current_value=94.0, threshold=92.0, direction="stable",
                         week_label="2026-11-02", process_breakdown=a["process_breakdown"], skill=SKILL,
                         analytics=a, metric_key="fta", images=images, trend_rows=rows)
    assert list(images) == ["alert1"] and 'src="cid:alert1"' in html and "Last 8 weeks" in text(html)


def test_uc4_alert_without_images_is_as_before():
    a = _analytics()
    kw = dict(metric="fta", rag="RED", current_value=94.0, threshold=92.0, direction="stable",
              week_label="2026-11-02", process_breakdown=a["process_breakdown"], skill=SKILL, analytics=a,
              metric_key="fta")
    assert "cid:" not in E.build_alert(**kw) and "Last 8 weeks" not in text(E.build_alert(**kw))


def test_a_failing_chart_never_stops_the_alert_or_the_weekly_report(monkeypatch, caplog):
    monkeypatch.setattr(C, "alert_png", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no font")))
    monkeypatch.setattr(C, "trend_png", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no font")))
    a, images = _analytics(), {}
    html = E.build_alert(metric="fta", rag="RED", current_value=94.0, threshold=92.0, direction="stable",
                         week_label="2026-11-02", process_breakdown=a["process_breakdown"], skill=SKILL,
                         analytics=a, metric_key="fta", images=images, trend_rows=a["process_breakdown"])
    weekly = W.build(JIRA, a, {}, skill=SKILL, images=images)
    assert images == {} and "Contributing Process Types" in html and "Weekly Operational Report" in weekly
    assert "8-Week Trend per Process Type" not in weekly
    assert any("left out" in r.message for r in caplog.records)


def test_uc3_weekly_report_has_a_chart_per_process_type_only_when_asked():
    a = _analytics()
    images = {}
    t = text(W.build(JIRA, a, {}, skill=SKILL, images=images))
    assert "8-Week Trend per Process Type" in t and len(images) == 3        # geo-good, geo-bad, geo-noref
    assert "8-Week Trend per Process Type" not in text(W.build(JIRA, a, {}, skill=SKILL))   # Word / previews


def test_uc3_charts_are_capped_and_biggest_first():
    a = _analytics()
    base = a["process_breakdown"][0]
    a["process_breakdown"] = [{**base, "process_type": f"pt-{i}", "total_hrs": float(i)} for i in range(12)]
    images = {}
    t = text(P.weekly_trend_html(a, {"fta", "efficiency", "coq"}, images))
    assert len(images) == P.MAX_CARDS and t.index("pt-11") < t.index("pt-4") and "pt-3 " not in t
    assert "4 smaller process types are not drawn" in t


def test_chart_time_and_size_stay_small():
    """Performance: 8 weekly charts + 4 alert charts in a few seconds, each PNG well under Graph's limits."""
    series = _analytics()["process_breakdown"][1]["trend"]
    t0 = time.perf_counter()
    pngs = [C.trend_png(series, True) for _ in range(8)] + [C.alert_png(series, "coq", 10.0, True) for _ in range(4)]
    assert time.perf_counter() - t0 < 15
    assert sum(len(p) for p in pngs) < 1_500_000 and max(len(p) for p in pngs) < 200_000


# ── Weekly report trend table: a week with no value (found 6 Nov 2026, DD's weekly report failed) ──────────

def test_weekly_trend_table_week_without_yield_does_not_fail():
    """A previous week with yield=None used to raise TypeError and stop the whole weekly report."""
    import email_html_weekly as W
    ana = {"metrics_4w": [{"week": "W45", "fta": 97.0, "coq": 5.0, "yield": 96.0, "efficiency_vs_bl": 101.0},
                          {"week": "W44", "fta": None, "coq": None, "yield": None, "efficiency_vs_bl": None}]}
    html = W._build_trend_table(ana, {"fta", "coq", "yield", "efficiency"})
    assert "96.00%" in html and "97.00%" in html and "N/A" in html


def test_weekly_trend_arrow_unchanged_when_previous_week_has_values():
    """Same arrows as before for normal data: FTA up is green, CoQ up is red, no move is a flat arrow."""
    import email_html_weekly as W
    assert "&#8593;" in W._trend_arrow(97.0, 95.0, 0.5, True) and W._GREEN in W._trend_arrow(97.0, 95.0, 0.5, True)
    assert W._RED in W._trend_arrow(6.0, 5.0, 0.2, False)
    assert "&#8594;" in W._trend_arrow(5.0, 5.0, 0.2, False)
    assert W._trend_arrow(5.0, None, 0.2, False) == ""
