# Testing and release checks: OPS Native AI

| Level | What | When | Evidence |
|---|---|---|---|
| Unit tests | `python -m pytest` (offline) | every push (CI) and before every release | CI run and `test_reports/*_unit.md` |
| Profile check | `python scripts/check_profiles.py` | part of the pre-release gate; warnings only | in the unit report |
| Pre-release gate | `python scripts/run_checks.py` | started by `azure/release.sh`, and stops the release if a test fails | `test_reports/<date>_<commit>_unit.md` |
| Post-deploy sanity | `python azure/sanity_check.py --image <tag> --mode live` (read-only) | started by `azure/release.sh` | `test_reports/<date>_<commit>_sanity.md` |
| First live run | the run report email `[OPS Native AI run OK]` | the next scheduled slot | the email |

## Unit tests (`tests/`)

The tests make no network calls: no Jira, Confluence, Databricks or Graph mail. Before anything
imports, `tests/conftest.py` points the output folder, analytics DB and backups at a temporary
folder. It also clears every test and mail switch, so a test run never writes the real analytics DB
and never sends email.

| File | Covers |
|---|---|
| `test_delivery.py` | Owner-only delivery, `EMAIL_CC=off`, the parallel-mode redirect, refusal of an invalid owner (`a@tomtom.com;b@x.com`, external, empty), and invalid CCs being dropped. |
| `test_trigger_engine.py` | A UC4 alert on a breach, with the repeat suppressed. No alert on placeholder data. A failed send is retried at the next slot. A healthy metric sends nothing. One UC3 per day for scheduled runs, while manual runs are never held back. A failing use case counts as an error. Quiet hours. |
| `test_sql_guard.py` | The read-only guard (writes, a second statement, injection attempts), the table scope, and profile values escaped in the scope filters. |
| `test_email_html.py` | Jira and Confluence text is escaped, and the original text stays unescaped for the Word report. The small formatters. |
| `test_schedule.py` | Which use cases run in each IST slot, and which slot a run serves and how late it is. |
| `test_skill_registry.py` | Profile parsing: triggers, quiet hours, time zone, metric names, thresholds, SLA, CC, the owner taken from the file name. |
| `test_time_saved_criteria.py` | Minutes per use case: UC1 20, UC2 10, UC3 90, UC4 15. |

The `MultiAgent_Briefing/manual_*.py` files are manual checks against the live services. They are not
tests, pytest does not collect them, and they must never run unattended.

## Post-deploy sanity check

`azure/sanity_check.py` reads only the job definition and its recent executions. It checks:

- the schedule (09, 13, 17 and 21 IST);
- no automatic retry and one run at a time;
- the expected image;
- the required settings, with secrets as secret references;
- `EMAIL_CC=off`, mail through Graph, and the mode (live or parallel);
- no test switches;
- the share mounts;
- that the recent runs succeeded.

## Release checklist

1. `python -m pytest` passes locally and in CI.
2. `bash azure/release.sh vYYYY-MM-DD-N live`. The tests run first, then the build, the job update
   and the sanity check.
3. Wait for the next slot's run report email. It must say "run OK" and "MCP ok".
4. Commit the new files in `test_reports/` and add a `CHANGELOG.md` entry.
5. Rollback: `python azure/deploy_job.py --image <previous tag> --mode live`. The last image tags are
   in the run report emails and in `az acr repository show-tags -n tomtomopshub --repository ops-native-ai`.
