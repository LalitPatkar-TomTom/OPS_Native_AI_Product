"""Email content safety (MultiAgent_Briefing/email_html.py): text from Jira and Confluence is
written by other people and is escaped before it reaches an email from the shared mailbox."""
import email_html as e
import email_html_weekly as w

TICKET = {"key": "OM-1", "summary": "<script>x</script> & <a href='http://evil'>click</a>", "status": "Open",
          "priority": "High", "assignee": "<b>A</b>", "reporter": "R", "hours_stale": 80.0,
          "url": "https://tomtom.atlassian.net/browse/OM-1", "sla_status": "BREACH_72H", "labels": []}
JIRA = {"sla_breaches": [TICKET], "sla_warnings": [], "open_tickets": [TICKET], "total_open": 1}


def test_sla_alert_escapes_jira_text():
    h = e.build_sla_alert(JIRA, skill={"project_name": "P"})
    assert "<script>" not in h and "href='http://evil'" not in h
    assert "&lt;script&gt;" in h and "1 SLA breach(es)" in h


def test_escaping_copies_and_keeps_original_for_word_report():
    escaped = e._escape_jira(JIRA)
    assert escaped["sla_breaches"][0]["summary"].startswith("&lt;script&gt;")
    assert JIRA["sla_breaches"][0]["summary"].startswith("<script>")      # original untouched
    assert e._escape_jira(None) == {}


def test_confluence_titles_are_escaped():
    c = e._escape_confluence({"pages": [{"page_title": "<img src=x>"}], "error": "<i>"})
    assert c["pages"][0]["page_title"] == "&lt;img src=x&gt;" and c["error"] == "&lt;i&gt;"


def test_ticket_button_gets_plain_text():
    assert "&amp;amp;" not in e._btn("A &amp; B", "d &lt;x&gt;", "OM")


def test_weekly_builder_uses_the_escape_helpers():
    assert w._escape_jira is e._escape_jira


def test_small_formatters():
    assert e._eff_str(None) == "N/A"
    assert e._eff_str(95.0) == "95.0% (-5.0%)"
    assert e._arrow("unknown") == "&#8594;"
    assert ">AMBER P3</span>" in e._badge("AMBER_P3")
