# Security model: OPS Native AI

## Who receives what

- **Recipient:** every email goes to the profile owner only. The owner is the profile's file name and
  must be exactly one `@tomtom.com` address; anything else is refused and logged.
- **No CCs from the job:** `EMAIL_CC=off` removes all CCs, and the sanity check verifies it after
  every deploy. Two mails are deliberate exceptions:
  - The profile-check email (`profile_check.py`) copies the OPS Native AI team.
  - The weekly analytics report (`azure/weekly_analytics.py`) goes to its fixed list of readers.
- **Parallel mode:** `EMAIL_PARALLEL_TO` sends every email to one address with no CC. The intended
  owner is written in the subject and in the analytics.
- **Recorded deliveries:** each delivery is recorded in `email_deliveries` (to, cc, intended owner,
  transport).

## Human in the loop

The engine only reads and recommends. Briefings and alerts carry P0, P1 and P2 actions with Jira
links, and the footer says that all actions need the owner's approval. The engine never updates,
closes or escalates a ticket, and never contacts anyone other than the owner.

## Data access

- **Databricks:** read-only. The guard accepts only one SELECT or WITH statement, and refuses a
  second statement and any write verb even inside a CTE. The Databricks identity must also be
  read-only; that grant is the primary control.
- **SQL values:** values from profiles (process types, planning IDs) are escaped before they go into
  SQL.
- **Jira and Confluence:** read tools only, through the MCP registry, which blocks write tools, with
  REST as the fallback. Their text is HTML-escaped before it goes into an email.

## Secrets

- **Storage:** secrets are job secrets, built by `azure/deploy_job.py` from the local `.env` and Azure.
  The script prints names, never values.
- **Graph mail:** the mail secret is copied from Azure to Azure and never lives on the laptop.
- **Git:** no secret is in git (`.gitignore` covers `.env` and the token folders).

## Known open items

| Item | Status |
|---|---|
| Personal Atlassian and Databricks tokens used as the service identity | OSI-013: service accounts planned |
| Graph Mail.Send granted on the OPS Hub Easy Auth app | OSI-021: a dedicated sender app is planned |
| `EMAIL_CC` defaults to on (the laptop backup CCs the global list) | The Azure job sets `off`. Check this before the laptop is used as backup. |
| Profile SLA hours are parsed, but the global 48/72 h are used | Behaviour as designed today. Using profile values is a feature change. |
| The legacy laptop onboarding server (CORS `*`, local OAuth tokens) | Archived 29 Oct to `_archive/Onboarding_Server`: not deployed, not run, not started by `start.bat`. |
| Unused modules: writer agents (`jira_writer.py`, `confluence_writer.py`), `data_fetcher.py`, `demo_run.py`, `send_*_preview.py`, `value_report.py` | No code path in the job imports them. They can be removed. |
