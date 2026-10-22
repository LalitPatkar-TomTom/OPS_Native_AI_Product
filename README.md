# OPS Native AI

OPS Native AI is a multi-agent engine that sends each operations lead a personal briefing, SLA
alerts, metric alerts and a weekly report. Each user's profile (`<email>_skill.md`, saved through OPS
Hub onboarding) defines their projects, metrics, thresholds and active use cases.

It runs as an Azure Container Apps job (`ops-native-ai-trigger`, resource group `ops-hub-rg`) at
09:00, 13:00, 17:00 and 21:00 IST. Email is sent through Microsoft Graph from `opsai@tomtom.com`.

## Use cases

| UC | What | When | Minutes saved per item |
|---|---|---|---|
| UC1 | Daily briefing: Jira, metrics, Confluence and prioritised actions | 09:00 slot | 20 |
| UC2 | Jira SLA alert for tickets with no update for 48 or 72 h | every slot | 10 |
| UC3 | Weekly report with a Word attachment | Friday 17:00 (21:00 is the catch-up) | 90 |
| UC4 | Metric alert (FTA, CoQ, efficiency, yield) against the user's own levels | every slot, once per metric per day | 15 |

## Architecture

```
entrypoint.sh (one job run; RUN_LOCK, so one run at a time; analytics DB copied from the share)
  └─ fire_all_now.py: picks the use cases for this slot, then for each profile:
       trigger_engine._make_job(uc, profile)       quiet hours (UC4 may break them)
         ├─ agents/jira_agent.py        Jira through the MCP registry first, REST fallback
         ├─ agents/confluence_agent.py  Confluence, the same way
         ├─ agents/analytics_agent.py   Databricks, read-only (agents/db_client.py SELECT guard)
         ├─ email_html*.py / word_report_weekly.py   deterministic templates, no LLM
         └─ delivery.py                 Graph mail, to the profile owner only (EMAIL_CC=off)
  audit_log.py (SQLite analytics: runs, events, deliveries) → saved back to the share
  run_report.py → short "[OPS Native AI run OK]" email to the operator after every run
```

The engine is deterministic: no LLM writes or sends anything.

## Design rules

These are checked by the tests in `tests/`.

| Rule | Where |
|---|---|
| An email goes only to the profile owner, and the owner must be one `@tomtom.com` address. | `delivery.deliver`, `is_valid_recipient` |
| Human in the loop: the engine recommends P0, P1 and P2 actions with Jira links, and people decide and act. | `email_html._build_actions` footer |
| No alert is sent on placeholder data. When Databricks is unavailable, UC4 sends nothing. | `trigger_engine._run_uc4` |
| No double emails: no automatic retry, one run at a time, one UC4 alert per metric per day, one UC3 per day. | `deploy_job.py`, `entrypoint.sh`, `uc4_state`, `audit_log.sent_today` |
| Databricks is read-only, and profile values are escaped in SQL. | `agents/db_client.py`, `analytics_agent._sql_str` |
| Jira and Confluence text is HTML-escaped in emails. | `email_html._escape_jira` |

## Test, release, verify

- `python -m pytest`: offline unit tests. CI runs them on every push.
- `python scripts/check_profiles.py`: read-only check of the profiles.
- `bash azure/release.sh <tag> live`: runs the tests, builds the image, updates the job, then runs
  the sanity check. Reports go to `test_reports/`. See `TESTING.md`.
- **Never start a manual run of the job to test it.** A manual run sends real emails.

More detail:
- `docs/ARCHITECTURE.md`: a scheduled run step by step, where data is stored, and fail-safe behaviour.
- `docs/adr/`: the architecture decision records.
- `SECURITY.md`: the security model and open items.
- `CHANGELOG.md`: the list of changes.
`AI Architecture/Onboarding_Server/` is the legacy laptop onboarding server. OPS Hub `/onboarding`
replaced it; it is not in the image.
