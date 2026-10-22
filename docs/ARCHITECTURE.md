# OPS Native AI architecture

This page covers the runtime view: the components, one scheduled run step by step, where data is
stored, and how the engine fails safe. The reasons behind the main choices are recorded in
[`adr/`](adr/). The chat app, where users onboard and edit their profiles, is OPS Hub (separate
repository).

## Components

| Component | Code | Responsibility |
|---|---|---|
| Job entry | `azure/entrypoint.sh` | One job execution: run lock, load the analytics DB, run, save the DB, run report, weekly analytics |
| Slot runner | `MultiAgent_Briefing/fire_all_now.py` | Picks the use cases for the IST slot and runs them for every profile, one after another |
| Trigger engine | `MultiAgent_Briefing/trigger_engine.py` | One use case for one user: quiet hours, decision logic, alert state, delivery, audit |
| Profile registry | `MultiAgent_Briefing/skill_registry.py` | Parses each `<email>_skill.md` into the user's projects, scope, metrics, levels and active use cases |
| Jira agent | `agents/jira_agent.py` | Open tickets and SLA status (48 h warning, 72 h breach). MCP first, REST fallback |
| Confluence agent | `agents/confluence_agent.py`, `confluence_fetch.py` | Staleness of the user's pages. MCP first, REST fallback |
| Analytics agent | `agents/analytics_agent.py`, `db_client.py` | FTA, CoQ, efficiency, yield and breakdowns from Databricks (read-only) |
| Alert state | `agents/uc4_state.py` | One UC4 alert per user per metric per day |
| Renderers | `email_html.py`, `email_html_weekly.py`, `word_report_weekly.py` | Deterministic HTML email and Word templates (no LLM) |
| Delivery | `delivery.py` | Microsoft Graph `sendMail` from `opsai@tomtom.com`, to the profile owner only |
| Analytics | `audit_log.py`, `azure/weekly_analytics.py`, `azure/impact_report.py` | Every run, event and delivery, the time saved, and the weekly Word report |
| Profile check | `profile_check.py` | Email to a user when their profile is new or changed: what works, and what to fix |

## One scheduled run (09:00, 13:00, 17:00, 21:00 IST)

```
Container Apps job (cron 30 3,7,11,15 * * * UTC, parallelism 1, no retry, 3.5 h timeout)
└─ entrypoint.sh
   1. RUN_LOCK on the share: a run still active → this slot is skipped (never two runs at once)
   2. copy trigger_audit.db from the share into the container (SQLite and SMB locking do not mix);
      if the DB was migrated but is missing → STOP, no emails
   3. fire_all_now.py --scheduled
        slot: 09:00 → UC1 + UC2 + UC4 · 13/17/21 → UC2 + UC4 · Friday 17/21 → + UC3
        for each profile in /data/skills/Personal Skills (the OPS Hub share):
          for each due use case that is Active in the profile:
            quiet hours? → skip (UC4 alerts may break them)
            UC1: Jira + Analytics + Confluence (in parallel) → briefing + P0/P1/P2 actions → deliver
            UC2: Jira → tickets past the SLA → alert → deliver
            UC3: once per day; Jira + Analytics + Confluence → weekly email + Word attachment → deliver
            UC4: Analytics (live data only) → each metric against the user's level → alert once per day
            every outcome → trigger_events · every email → email_deliveries
        end of run: one daily DB snapshot to the share's backups/ (last 30 kept)
   4. profile_check.py → email for a new or changed profile (09, 13, 17 only)
   5. save the DB back to the share (SQLite backup API, write-then-rename)
   6. run_report.py → "[OPS Native AI run OK | PROBLEM]" email to the operator
   7. Monday 09:00 → weekly analytics (Word) to the four report readers
```

## Delivery rules

| Rule | How |
|---|---|
| Only the profile owner | The recipient is the profile's file name, and it must be one `@tomtom.com` address (`is_valid_recipient`) |
| No CC | `EMAIL_CC=off` on the job, verified by the sanity check after every deploy |
| Parallel mode for cut-overs | `EMAIL_PARALLEL_TO` sends everything to one address; the intended owner is shown in the subject and the analytics |
| No double sends | No job retry, one run at a time, UC4 once per metric per day, UC3 once per day, retry only after a failed send |
| Human in the loop | Emails recommend P0, P1 and P2 actions with Jira links; the engine never changes Jira or Confluence |

## Where data is stored

| Location | Contents | Kept |
|---|---|---|
| `opshub-skills` share → `/data/skills` | `Personal Skills/<email>_skill.md`, written by OPS Hub onboarding | Until the user's next onboarding |
| `opshub-config` share → `/data/config/native-ai/` | `trigger_audit.db`, the single analytics master. Tables: `trigger_runs`, `trigger_events`, `email_deliveries`, `uc4_alert_state`, `profile_checks` | Permanent |
| `…/native-ai/backups/` | Daily consistent snapshots of the analytics DB | Last 30 |
| `…/native-ai/output/`, `logs/` | Run outputs (briefing text, UC3 reports) and the run log | No automatic purge |
| Container `/work/output` | Working copy during a run | Gone after the run |

## Fail-safe behaviour

| Situation | Behaviour |
|---|---|
| Databricks unavailable or no data | Placeholder values marked `live=False`. UC4 sends no alert and records the reason |
| Atlassian MCP unavailable | The request falls back to the REST API, and the run report shows "FALLBACK to REST" |
| One user's use case fails | Logged and counted as an error, and the run continues with the next user. The run report says PROBLEM |
| Graph send fails | Recorded as `send_failed`; UC4 retries at the next slot |
| Previous run still active | The slot is skipped and reported; no overlapping runs |
| Analytics DB missing after migration | The run stops before sending anything |
| Invalid profile owner | No email; the error is logged |

## Limits today

- **Sequential processing.** Users are processed one after another, up to about 3 minutes each on a
  Friday. Parallel per-user processing (OSI-017) is needed before about 50 users.
- **Personal service tokens.** Personal Atlassian and Databricks tokens act as the service identity
  (OSI-013).
- **Shared mail app.** Graph Mail.Send is granted on the OPS Hub sign-in app; a dedicated sender app
  is planned (OSI-021).
