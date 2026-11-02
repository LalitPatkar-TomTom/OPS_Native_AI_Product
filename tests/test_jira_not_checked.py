"""A Jira project key that does not exist is reported as "not checked", never as "All clear" (2 Nov 2026).

Jira search answers 200 with 0 tickets for an unknown project, so four profiles (Geocoding, GDN, QA, LMDF)
got "Jira SLA: All clear" and GREEN every day. Now the project is looked up first (read-only, once per key per
run); a 404 makes the Jira result an error, and every email says "Not checked" with the reason, the overall
status is at least AMBER, the subject says "Jira not checked" and the actions name it.
"""
import html
import re

import pytest

import email_html as E
import email_html_weekly as W
import skill_registry as sr
from agents import analytics_agent as A, jira_agent as J

PROFILE = """# Jane Doe
Jira project key: QA
"""


class _Resp:
    """Minimal httpx response for the project lookup."""
    def __init__(self, code):
        self.status_code = code


def _skill(tmp_path):
    p = tmp_path / "jane.doe@tomtom.com_skill.md"
    p.write_text(PROFILE, encoding="utf-8")
    return sr.load_skill(p)


@pytest.mark.real_project_lookup
def test_project_lookup_404_only_counts_as_missing_and_is_cached(monkeypatch):
    calls = []
    answers = {"QA": 404, "OM": 200, "DOWN": 503}

    def get(url, **kw):
        key = url.rsplit("/", 1)[1]
        calls.append(key)
        if key == "BOOM":
            raise OSError("network")
        return _Resp(answers[key])
    monkeypatch.setattr(J.httpx, "get", get)
    monkeypatch.setattr(J, "_missing_projects", {})
    assert J.project_missing("QA") and J.project_missing("QA")
    assert not J.project_missing("OM") and not J.project_missing("DOWN") and not J.project_missing("BOOM")
    assert calls.count("QA") == 1                                   # one lookup per key per run


@pytest.mark.real_project_lookup
def test_missing_project_is_an_error_and_no_search_is_sent(monkeypatch, tmp_path):
    monkeypatch.setattr(J, "JIRA_API_TOKEN", "x")
    monkeypatch.setattr(J, "_missing_projects", {"QA": True})
    monkeypatch.setattr(J.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("searched")))
    r = J.run(_skill(tmp_path))
    assert r["project_not_found"] and "Jira project 'QA' not found" in r["error"] and r["total_open"] == 0


@pytest.mark.real_project_lookup
def test_mcp_says_project_does_not_exist_so_no_rest_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(J, "JIRA_API_TOKEN", "x")
    monkeypatch.setattr(J.atlassian_mcp, "enabled", lambda: True)

    def search(jql, fields, n):
        raise J.atlassian_mcp.MCPError("JQL validation failed: The value 'QA' does not exist for the field 'project'.")
    monkeypatch.setattr(J.atlassian_mcp, "search_jira", search)
    monkeypatch.setattr(J.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("REST searched")))
    r = J.run(_skill(tmp_path))
    assert r["project_not_found"] and "'QA' not found" in r["error"]


@pytest.mark.real_project_lookup
def test_project_status_follows_mcp_then_rest(monkeypatch):
    monkeypatch.setattr(J.atlassian_mcp, "enabled", lambda: True)
    seen = {"OK": None, "GONE": J.atlassian_mcp.MCPError("value 'GONE' does not exist for the field 'project'"),
            "VPN": J.atlassian_mcp.MCPError("registry returned no Atlassian tools")}

    def search(jql, fields, n):
        key = jql.split("= ")[1]
        if seen[key]:
            raise seen[key]
        return {"issues": []}
    monkeypatch.setattr(J.atlassian_mcp, "search_jira", search)
    monkeypatch.setattr(J.httpx, "get", lambda url, **k: _Resp(404 if url.endswith("/VPN") else 200))
    assert J.project_status("OK") == "ok"            # the MCP can read it (DPOT: the REST account cannot)
    assert J.project_status("GONE") == "missing"
    assert J.project_status("VPN") == "missing"      # MCP down: REST decides


def _not_checked():
    return {"sla_breaches": [], "sla_warnings": [], "open_tickets": [], "total_open": 0, "source": "Jira QA",
            "as_of": "2026-11-02", "project_not_found": True,
            "error": "Jira project 'QA' not found or not visible to the OPS AI Jira account — check the Jira "
                     "project key in your profile (OPS Hub → My profile)"}


def test_status_is_never_green_and_headline_names_the_reason():
    jira = _not_checked()
    assert E.overall_rag(jira, {}, set()) == "AMBER"
    assert "Jira SLA not checked (project key not found in Jira or not visible)" in E.headline_text("QA", jira, {}, set())
    assert E.overall_rag({**jira, "error": None, "project_not_found": False}, {}, set()) == "GREEN"


def test_daily_and_weekly_emails_say_not_checked_never_all_clear(tmp_path):
    s = _skill(tmp_path)
    a = A.run(s, "daily")                                            # no scope: no Databricks query
    def text(h):
        """Visible text of an email: tags removed, entities decoded, spaces collapsed."""
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))
    daily = text(E.build(_not_checked(), a, {}, s))
    weekly = text(W.build(_not_checked(), a, {}, skill=s))
    assert "Jira SLA: Not checked — Jira project 'QA' not found" in daily
    for t in (daily, weekly):
        assert "Jira SLA not checked (project key not found in Jira or not visible)" in t       # the headline
        assert "All clear" not in t and "ALL CLEAR" not in t and "on track" not in t


def test_word_report_says_not_checked(tmp_path):
    import io
    import pytest
    docx = pytest.importorskip("docx")
    import word_report_weekly as WR
    s = _skill(tmp_path)
    data = WR.build(_not_checked(), A.run(s, "daily"), {}, skill=s)
    text = "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
    text += "\n".join(c.text for t in docx.Document(io.BytesIO(data)).tables for r in t.rows for c in r.cells)
    assert "Not checked" in text and "All clear" not in text
