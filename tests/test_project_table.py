"""OSI-001/002 (3 Nov 2026): the onboarding form's Active Projects table now has separate Planning ID and
Jira Key columns. The Jira key is read from the "Jira Key" column; profiles made before keep the old
reading, and a planning ID can never be taken for a Jira key."""
import time

import skill_registry as sr

NEW = """## 1. Active Projects

| Activity / Project | Planning ID | Jira Key | Role on Project | Status |
| --- | --- | --- | --- | --- |
| Geocoding Ops | GEOCODING | — | Lead | Active |
| RM Lanes | ADAS-RMLanes | om | PM | Active |
| Old work | X-1 | DSM | PM | On Hold |

- **Project Keys monitored:** OM, DSM
"""

OLD = """## 1. Active Projects

| Project | Code | Role on Project | Status |
| --- | --- | --- | --- |
| RM Lanes | MCPET | Manager | Active |
"""


def test_new_table_takes_the_first_active_real_key():
    # GEOCODING sits in the Planning ID column and must not become the key; "om" is accepted in any case
    assert sr._extract_project_config(NEW) == {"project_name": "RM Lanes", "jira_project": "OM"}


def test_old_profiles_read_as_before():
    assert sr._extract_project_config(OLD) == {"project_name": "RM Lanes", "jira_project": "MCPET"}


def test_new_table_without_any_key_falls_back_to_project_keys_line_not_to_planning_ids():
    text = NEW.replace("| om |", "| — |")
    out = sr._extract_project_config(text)
    assert out["jira_project"] == "OM"                      # from "Project Keys monitored", not GEOCODING
    text = text.replace("- **Project Keys monitored:** OM, DSM\n", "")
    assert sr._extract_project_config(text)["jira_project"] == ""


def test_only_active_rows_count_and_table_needs_no_status_column():
    assert sr._jira_key_column(NEW.replace("| PM | Active |", "| PM | On Hold |"))[2] == ""
    no_status = "| Activity / Project | Jira Key |\n| --- | --- |\n| A | RTE |\n"
    assert sr._jira_key_column(no_status) == (True, "A", "RTE")
    assert sr._jira_key_column(OLD) == (False, "", "")


def test_reading_a_large_profile_stays_fast():
    big = NEW + "\n".join(f"| P{i} | ID-{i} | — | x | Active |" for i in range(2000))
    t = time.perf_counter()
    for _ in range(50):
        sr._extract_project_config(big)
    assert time.perf_counter() - t < 2.0
