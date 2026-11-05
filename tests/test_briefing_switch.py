"""The per-process-type layout as the UC1 daily briefing for everyone (5 Nov 2026): the switch back
(BRIEFING_LAYOUT=classic), the fallbacks (new -> classic -> plain text), charts passed through deliver(),
and the classic layouts no longer printing a scope-wide tasks/hr against an averaged baseline."""
import logging

import delivery
import email_briefing_pt as P
import email_html as E
from test_briefing_pt import JIRA, SKILL, _analytics, _with_yield, text


# ── build_daily: default, switch, fallbacks ───────────────────────────────────

def test_default_is_the_per_process_type_layout_with_charts(monkeypatch):
    monkeypatch.delenv("BRIEFING_LAYOUT", raising=False)
    html, images, layout = P.build_daily(JIRA, _with_yield(_analytics()), {}, SKILL)
    assert layout == "per_pt" and images and "Needs attention" in html and "cid:trend1" in html


def test_classic_switch_needs_no_release(monkeypatch):
    monkeypatch.setenv("BRIEFING_LAYOUT", "classic")
    html, images, layout = P.build_daily(JIRA, _analytics(), {}, SKILL)
    assert layout == "classic" and images == {} and "Work Unit &amp; Process-type Breakdown" in html


def test_a_failing_new_layout_falls_back_to_classic_with_a_warning(monkeypatch, caplog):
    monkeypatch.delenv("BRIEFING_LAYOUT", raising=False)
    monkeypatch.setattr(P, "build", lambda *a, **k: 1 / 0)
    with caplog.at_level(logging.WARNING):
        html, images, layout = P.build_daily(JIRA, _analytics(), {}, SKILL)
    assert layout == "classic" and html and images == {}
    assert "per-process-type layout failed" in caplog.text and "ZeroDivisionError" in caplog.text
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]      # a warning, not a failed run


def test_both_layouts_failing_gives_plain_text_as_before(monkeypatch):
    monkeypatch.setattr(P, "build", lambda *a, **k: 1 / 0)
    monkeypatch.setattr(E, "build", lambda *a, **k: 1 / 0)
    assert P.build_daily(JIRA, _analytics(), {}, SKILL) == ("", {}, "plain")


def test_preview_note_reaches_the_new_layout():
    html, _, _ = P.build_daily(JIRA, _analytics(), {}, SKILL, preview_note="PREVIEW-X")
    assert "PREVIEW-X" in html


# ── deliver(): images go with the HTML, never with plain text ─────────────────

def _capture(monkeypatch):
    """Record _send_email calls; no audit DB write."""
    calls = []
    monkeypatch.setattr(delivery, "_send_email", lambda *a, **k: calls.append(k) or (True, "graph"))
    import audit_log
    monkeypatch.setattr(audit_log, "log_delivery", lambda **k: None)
    return calls


def test_deliver_passes_the_charts_with_the_html(monkeypatch):
    calls = _capture(monkeypatch)
    delivery.deliver("md", {"user": "a@tomtom.com"}, subject="s", html_body="<img src='cid:trend1'>",
                     inline_images={"trend1": b"png"})
    assert calls[0]["inline_images"] == {"trend1": b"png"}


def test_plain_text_fallback_sends_no_images(monkeypatch):
    calls = _capture(monkeypatch)
    delivery.deliver("md", {"user": "a@tomtom.com"}, subject="s", html_body="", inline_images={"trend1": b"png"})
    assert "inline_images" not in calls[0]


def test_other_emails_are_unchanged(monkeypatch):
    calls = _capture(monkeypatch)
    delivery.deliver("md", {"user": "a@tomtom.com"}, subject="s", html_body="<p>UC3</p>")
    assert "inline_images" not in calls[0]


# ── run_uc1 uses build_daily and hands the charts to deliver ──────────────────

def test_run_uc1_sends_the_new_layout_with_its_charts(monkeypatch, tmp_path):
    import orchestrator as O
    sent = {}
    skill = {**SKILL, "user": "a@tomtom.com", "databricks_process_types": ["geo-good"]}
    monkeypatch.setattr(O, "load_skill", lambda f: skill)
    monkeypatch.setattr(O, "load_uc_definition", lambda *a, **k: {"name": "UC1", "trigger": "daily"}, raising=False)
    monkeypatch.setattr(O.jira_agent, "run", lambda s: JIRA)
    monkeypatch.setattr(O.analytics_agent, "run", lambda s, rt: _with_yield(_analytics()))
    monkeypatch.setattr(O.confluence_agent, "run", lambda s: {"pages": []})
    monkeypatch.setattr(O.briefing_agent, "run", lambda *a, **k: "markdown")
    monkeypatch.setattr(O, "deliver", lambda *a, **k: sent.update(k) or {"email": True})
    monkeypatch.delenv("BRIEFING_LAYOUT", raising=False)
    f = tmp_path / "a@tomtom.com_skill.md"
    f.write_text("x", encoding="utf-8")
    O.run_uc1(f)
    assert "Needs attention" in sent["html_body"] and list(sent["inline_images"]) == ["trend1"]


# ── Classic layouts: earned hours instead of tasks/hr vs an averaged baseline ──

def test_earned_hours_text_comes_from_the_reported_week():
    a = _analytics()
    assert E.eff_earned_text(a) == "352 h of work at each process type&apos;s own baseline in 400 h booked"
    assert E.eff_earned_text({}) == "" and E.eff_earned_text({**a, "overall_trend": []}) == ""


def test_classic_briefing_no_longer_prints_tasks_per_hour_or_an_averaged_baseline():
    html = E.build(JIRA, _analytics(), {}, SKILL)
    assert "average of the process types" not in html and "tasks/hr" not in html
    assert "352 h of work at each process type" in html


def test_plain_text_briefing_uses_earned_hours_too():
    from agents import briefing_agent
    md = briefing_agent.run(JIRA, {**_analytics(), "efficiency_rag": "RED"}, {}, skill=SKILL)
    assert "tasks/hr" not in md and "352 h of work at each process type's own baseline in 400 h booked" in md


# ── Release tooling: the layout switch is explicit and visible ────────────────

def test_deploy_job_sets_the_classic_layout_only_when_asked(monkeypatch):
    import deploy_job
    assert deploy_job.SKIP.match("BRIEFING_LAYOUT")                      # a laptop .env value never reaches the job
    src = open(deploy_job.__file__, encoding="utf-8").read()
    assert '"--layout", choices=["per_pt", "classic"], default="per_pt"' in src
    assert '{"name": "BRIEFING_LAYOUT", "value": "classic"}' in src


def test_sanity_check_shows_the_layout_as_a_warning_only():
    import sanity_check
    assert "BRIEFING_LAYOUT" in sanity_check.SWITCHES
    src = open(sanity_check.__file__, encoding="utf-8").read()
    assert 'check("Daily briefing layout"' in src and "warn_only=True" in src


def test_planning_ids_with_fta_not_green_no_longer_crash_the_briefing():
    """Live bug found in the 5 Nov full run (Girish): the planning-ID loop overwrote `fta` with text, so the
    actions line '{fta:.2f}%' crashed and the user's whole UC1 failed."""
    from agents import briefing_agent
    a = {**_analytics(), "fta_current": 92.86, "fta_rag": "AMBER",
         "planning_breakdown": [{"planning_id": "GDN-1", "fta_pct": 90.0, "fta_rag": "RED", "eff_vs_bl": 80.0,
                                 "coq_pct": 9.0, "total_qc": 50, "prod_tasks": 300, "total_hrs": 40.0}]}
    md = briefing_agent.run(JIRA, a, {}, skill=SKILL)
    assert "current 92.86%" in md and "| GDN-1 |" in md
