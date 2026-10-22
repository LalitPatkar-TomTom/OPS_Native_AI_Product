# Changelog: OPS Native AI

## Unreleased: architecture review hardening (22 Oct 2026)

**Safety**
- **Recipient check:** an email is sent only when the owner is exactly one `@tomtom.com` address.
  Invalid CC addresses are dropped.
- **No alert on placeholder numbers:** UC4 no longer evaluates them when Databricks has no data or is
  unreachable. The reason is recorded instead, so no false alert is sent.
- **Failed UC4 sends:** a failed send no longer suppresses that metric's alert for the rest of the
  day. It is retried at the next slot.
- **One UC3 per day:** UC3 goes out once per user per day. The Friday 21:00 slot is now only a
  catch-up when 17:00 did not send. Manual runs are not held back.
- **Read-only guard:** the guard now refuses a second statement and write verbs anywhere in a query,
  for example `WITH … INSERT`, after blanking string literals and comments.
- **Profile values in SQL:** process types and planning IDs are escaped in the Databricks queries.
- **Email HTML:** Jira and Confluence text (summaries, names, statuses, page titles) is HTML-escaped
  in emails. The Word report still gets the original text.

**Fixes**
- **Error counts:** a failing use case is now counted as an error in `trigger_runs.errors`. It used to
  be recorded as 0.
- **Run report:** it says PROBLEM when a run logged an ERROR. It used to say OK.

**Engineering**
- **Tests:** offline unit tests (`tests/`, 73 tests) and a read-only profile check
  (`scripts/check_profiles.py`), both run in CI.
- **Release flow:** `azure/release.sh` runs the tests, builds the image, updates the job and then runs
  the sanity check (`azure/sanity_check.py`). Reports go to `test_reports/`.
- **Manual scripts:** the live-service scripts `test_*.py` are now `manual_*.py`, so pytest can never
  run them. They called live services, could send email, and one cleared the UC4 alert state.
- **Documentation:** `README.md`, `TESTING.md` and `SECURITY.md` are new, and comments were added at
  the decision points.

## Earlier releases

See the git history. Highlights:
- 21 Oct: profile-check email.
- 20 Oct: live from Azure, with one analytics DB on the share, a run report after every run, and
  weekly analytics.
- 19 Oct: Microsoft Graph mail and the Azure job; Jira and Confluence through the TomTom MCP registry.
