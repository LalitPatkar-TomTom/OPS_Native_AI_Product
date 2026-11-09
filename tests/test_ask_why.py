"""'Ask why' (ADR-015): the email's numbers are saved once per email as a snapshot on the share, and the email
links to the OPS Hub page by a random id only. Off by default; without links every email is as before; a save
problem never stops an email; nothing is overwritten; no LLM (test_no_llm.py covers this module too)."""
import json
import re
import time

import pytest

import ask_why
import delivery
import email_html
import email_html_weekly as W
import trigger_engine as te
from agents import analytics_agent, uc4_state

USER = "Ask.Why@TomTom.com"
LIVE = {"live": True, "week_label": "2026-11-02", "fta_current": 90.0, "fta_rag": "RED", "coq_current": 9.0,
        "coq_rag": "RED", "efficiency_vs_bl": 95.0, "yield_current": 88.0, "process_breakdown": [],
        "root_cause": {"fta": {"action": "Coach the editors with most rejections", "causes": ["c"], "more": []}},
        "overall_trend": [{"week": "2026-11-02", "fta": 90.0}], "secret_raw_rows": [1, 2, 3]}


@pytest.fixture
def on(monkeypatch, tmp_path):
    """ASK_WHY=1 with snapshots in a temporary folder; returns that folder."""
    monkeypatch.setenv("ASK_WHY", "1")
    monkeypatch.setenv("ASK_WHY_DIR", str(tmp_path / "drill"))
    monkeypatch.delenv("OPSHUB_URL", raising=False)
    return tmp_path / "drill"


# ── Functional ──────────────────────────────────────────────────────────────────

def test_off_by_default_changes_nothing(monkeypatch, tmp_path):
    monkeypatch.delenv("ASK_WHY", raising=False)
    monkeypatch.setenv("ASK_WHY_DIR", str(tmp_path))
    a = dict(LIVE)
    assert ask_why.snapshot(a, {"user": USER}, "UC1") == {}
    assert "why_links" not in a and not list(tmp_path.iterdir())
    assert ask_why.links_row(a) == "" and ask_why.alert_link(a, "fta") == ""


def test_snapshot_holds_the_email_numbers_for_its_owner(on):
    a = dict(LIVE)
    links = ask_why.snapshot(a, {"user": USER, "project_name": "P"}, "UC3")
    files = list(on.glob("*.json"))
    assert len(files) == 1 and re.fullmatch(r"[0-9a-f]{32}\.json", files[0].name)
    doc = json.loads(files[0].read_text(encoding="utf-8"))
    assert (doc["owner"], doc["uc"], doc["project"]) == ("ask.why@tomtom.com", "UC3", "P")
    assert doc["analytics"]["fta_current"] == 90.0 and doc["analytics"]["root_cause"]["fta"]["action"]
    assert "secret_raw_rows" not in doc["analytics"]                  # only what the email is built from
    rid = files[0].stem
    assert links["fta"] == f"{ask_why.OPSHUB_BASE}/why?r={rid}&m=fta" and a["why_links"] is links
    assert set(links) == {"fta", "efficiency", "coq", "yield"}


def test_links_appear_in_the_daily_weekly_and_alert_emails(on):
    a = dict(LIVE)
    ask_why.snapshot(a, {"user": USER}, "UC1")
    skill = {"user": USER, "project_name": "P", "primary_metrics": ["fta", "coq"]}
    weekly = W.build({}, a, {}, skill=skill)
    classic = email_html.build({}, a, {}, skill=skill)
    alert = email_html.build_alert(metric="fta", rag="RED", current_value=90.0, threshold=92.0, direction="stable",
                                   week_label="2026-11-02", process_breakdown=[], skill=skill, analytics=a)
    for html in (weekly, classic):
        assert "Ask why" in html and html.count("/why?r=") == 4
    assert "See why &rarr;" in alert and a["why_links"]["fta"].replace("&", "&amp;") in alert


def test_copq_alert_opens_the_coq_page(on):
    a = dict(LIVE)
    ask_why.snapshot(a, {"user": USER}, "UC4")
    assert "m=coq" in ask_why.alert_link(a, "copq")


def test_uc4_run_puts_see_why_in_the_combined_alert(on, monkeypatch):
    sent = []
    monkeypatch.setattr(delivery, "deliver", lambda content, skill, **kw: (sent.append(kw) or {"email": True}))
    monkeypatch.setattr(analytics_agent, "run", lambda skill, report_type="daily": {**LIVE, "fta_current": 90.0,
                                                                                    "coq_current": 9.0})
    monkeypatch.delenv("UC4_COMBINED_ALERT", raising=False)
    monkeypatch.delenv("FORCE_UC4_ALERT", raising=False)
    user = "askwhy.uc4@tomtom.com"
    uc4_state.clear_for_testing(user)
    try:
        te._run_uc4({"user": user, "project_name": "P", "primary_metrics": ["fta", "coq"],
                     "metric_thresholds": {"fta": {"alert": 92.0, "target": 95.0, "direction": "drop"},
                                           "coq": {"alert": 7.0, "target": 6.0, "direction": "rise"}}}, user)
    finally:
        uc4_state.clear_for_testing(user)
    assert len(sent) == 1 and sent[0]["html_body"].count("See why &rarr;") == 2
    assert len(list(on.glob("*.json"))) == 1                         # one snapshot per alert email


# ── Technical ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("analytics,skill", [
    (None, {"user": USER}), ({**LIVE, "no_scope": True}, {"user": USER}), ({**LIVE, "live": False}, {"user": USER}),
    (dict(LIVE), {}), (dict(LIVE), None)])
def test_no_snapshot_without_live_data_or_an_owner(on, analytics, skill):
    assert ask_why.snapshot(analytics, skill, "UC1") == {}
    assert not on.exists() or not list(on.iterdir())


def test_a_save_problem_sends_the_email_without_links(on, monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("ASK_WHY_DIR", str(blocker / "drill"))          # a folder cannot be made inside a file
    a = dict(LIVE)
    assert ask_why.snapshot(a, {"user": USER}, "UC1") == {} and "why_links" not in a


def test_every_email_gets_its_own_file_and_nothing_is_overwritten(on):
    for _ in range(3):
        ask_why.snapshot(dict(LIVE), {"user": USER}, "UC1")
    assert len(list(on.glob("*.json"))) == 3 and not list(on.glob(".*.tmp"))


def test_link_base_can_be_set_and_is_escaped(on, monkeypatch):
    monkeypatch.setenv("OPSHUB_URL", "https://hub.example/")
    a = dict(LIVE)
    ask_why.snapshot(a, {"user": USER}, "UC1")
    assert a["why_links"]["fta"].startswith("https://hub.example/why?r=")
    assert "&amp;m=fta" in ask_why.links_row(a)


def test_ids_are_random_hex():
    ids = {ask_why.new_id() for _ in range(200)}
    assert len(ids) == 200 and all(re.fullmatch(r"[0-9a-f]{32}", i) for i in ids)


# ── Performance ─────────────────────────────────────────────────────────────────

def test_snapshot_of_a_large_scope_is_fast(on):
    big = {**LIVE, "process_breakdown": [{"process_type": f"pt{i}", "trend": [{"week": "w", "fta": 90}] * 8}
                                         for i in range(300)],
           "operator_breakdown": [{"operator": f"op{i}", "fta_pct": 90} for i in range(2000)]}
    t = time.perf_counter()
    ask_why.snapshot(big, {"user": USER}, "UC3")
    assert time.perf_counter() - t < 0.5
    assert next(on.glob("*.json")).stat().st_size < 2_000_000



def test_snapshot_keeps_the_email_period_and_rules(on):
    a = dict(LIVE)
    ask_why.snapshot(a, {"user": USER}, "UC3")
    doc = json.loads(next(on.glob("*.json")).read_text(encoding="utf-8"))
    assert doc["period"] == email_html.period_label("2026-11-02", fallback_note=email_html.alert_week_note(a))
    assert doc["rules"] == {"min_qc_to_judge": 10, "op_min_prod_hours": 8.0}
