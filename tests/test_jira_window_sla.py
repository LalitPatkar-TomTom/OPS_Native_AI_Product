"""OSI-003/025/037: Jira tickets only from a created-date window; OSI-006: SLA levels per profile."""
from agents import jira_agent as ja


def test_default_window_is_last_12_months():
    clause, label = ja.created_window({})
    assert clause == "AND created >= -365d " and label == "created in the last 12 months"


def test_profile_window_since_date_and_duration():
    assert ja.created_window({"jira_window": {"since": "2026-01-01"}})[0] == 'AND created >= "2026-01-01" '
    assert ja.created_window({"jira_window": {"days": 730}})[1] == "created in the last 2 year(s)"


def test_jql_contains_the_window():
    jql, _ = ja._build_jql({"jira_project": "OM", "user": "a@tomtom.com"})
    assert "AND created >= -365d AND (" in jql and jql.endswith("ORDER BY updated ASC")


def test_sla_status_uses_profile_levels():
    warn, esc = ja.sla_levels({"sla_thresholds": {"warning_hours": 300, "escalation_hours": 360}})
    assert (warn, esc) == (300, 360)
    assert ja._sla_status(100, warn, esc) == "OK"
    assert ja._sla_status(320, warn, esc) == "WARNING_48H"
    assert ja._sla_status(400, warn, esc) == "BREACH_72H"
    assert ja.sla_levels({}) == (48, 72)
