# Code review guide: OPS Native AI

**For:** the technical expert reviewing the code · **Owner:** Lalit Patkar (lalit.patkar@tomtom.com), Maps Operations
**Branch under review:** `tech-review`. It is `main` as it runs in production, plus this guide.
**Live version:** job image `v2026-10-27-1` on Azure Container Apps job `ops-native-ai-trigger` (27 Oct 2026).
**Sister repository:** [OPS Hub](https://github.com/LalitPatkar-TomTom/OPSHUB/tree/tech-review) (the chat and self-service web app). Review both together.

---

## 1. What this is

A deterministic, scheduled multi-agent engine. Four times a day, it reads each user's profile and builds their emails from Jira, Confluence and Databricks:

| Use case | When | What the user gets |
|---|---|---|
| UC1 daily briefing | 09:00 IST | Open work, SLA status, quality and efficiency at a glance |
| UC2 SLA alerts | 09 · 13 · 17 · 21 IST | Tickets with no update past the profile's warning and breach hours |
| UC3 weekly report | Fri 17:00 IST | Weekly summary with a Word draft attached |
| UC4 metric alerts | 09 · 13 · 17 · 21 IST | FTA, CoQ, efficiency and yield past the profile's alert levels, including an operator breakdown |

These design rules matter most when reading the code:

- **No LLM in the decide or send path** ([ADR-001](docs/adr/001-deterministic-engine.md)). Code computes every number and every email is built from a template.
- **Owner-only delivery** ([ADR-003](docs/adr/003-owner-only-delivery.md)). The recipient is the profile owner, one `@tomtom.com` address, and the job sends no CC.
- **Read-only sources.** Nothing is written to Jira, Confluence or Databricks.

## 2. Reading order (about 60 minutes)

1. [`README.md`](README.md): the architecture and design rules, and where each rule lives in the code.
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): the runtime flow per run, where state is kept, and fail-safe behaviour.
3. [`docs/adr/`](docs/adr/): 7 decision records. [ADR-007](docs/adr/007-reported-week.md) explains which week the numbers come from and when alerts may use a part week. The rule is subtle, so read it before `analytics_agent.py`.
4. [`SECURITY.md`](SECURITY.md) and [`TESTING.md`](TESTING.md).
5. The code, in the order of section 3.
6. [`CHANGELOG.md`](CHANGELOG.md): every release and the reason for it, including the 27 Oct fixes.

## 3. Where to look in the code

Paths are under `MultiAgent_Briefing/` unless they start with `azure/`, `scripts/` or `tests/`.

| Concern | File | What to check |
|---|---|---|
| Entry point and run lock | `azure/entrypoint.sh` → `fire_all_now.py` | One run at a time, no automatic retry, run report at the end |
| Per-user flow | `trigger_engine.py` | UC1–UC4 per profile; one user's failure must not stop the others |
| Profiles as configuration | `skill_registry.py`, `scripts/check_profiles.py` | Parsing and validation of each user's SKILL.md |
| Jira (MCP first, REST fallback) | `agents/jira_agent.py`, `agents/atlassian_mcp.py`, `registry_mcp.py` | Paging up to 1,000 tickets; SLA hours; JQL escaping (`_jql_str`) |
| Databricks, read-only | `agents/db_client.py`, `agents/analytics_agent.py` | SELECT guard; reported week (ADR-007); small samples never flagged |
| UC4 repeat suppression | `agents/uc4_state.py` | An alert is marked sent only after a successful send |
| Email building | `email_html.py`, `email_html_weekly.py`, `word_report_weekly.py` | HTML escaping of Jira and Confluence text; list caps (100 tickets, 50 operators) |
| Delivery | `delivery.py` | Recipient checks, Microsoft Graph, owner only |
| Audit and analytics | `audit_log.py`, `azure/weekly_analytics.py` | UC3 sent once per day; time-saved criteria (ADR-006) |
| Release | `azure/release.sh`, `azure/deploy_job.py`, `azure/sanity_check.py`, `Dockerfile` | Gate: tests → build → deploy → sanity check |

## 4. Evidence

| | Result | Where |
|---|---|---|
| Unit tests (offline: no Jira, Databricks or mail) | **119 / 119 passed** | `tests/` · report `test_reports/2026-10-27_1007_9f0c4f3_unit.md` |
| Profile check | All profiles in the repo valid | `scripts/check_profiles.py`, run in CI |
| Post-deploy sanity check (read-only, live) | **All passed** | `test_reports/2026-10-27_1009_9f0c4f3_sanity.md` |
| CI | Every push and pull request | `.github/workflows/tests.yml` (Python 3.11) |

Every release writes dated test reports to `test_reports/`, and they are committed with the release. Changes from the first review (22 Oct) to now: [compare f1f70cb...tech-review](https://github.com/LalitPatkar-TomTom/OPS_Native_AI_Product/compare/f1f70cb...tech-review).

## 5. Known limits and open items

These are listed so that review time goes to what we don't know yet.

| Item | Plan |
|---|---|
| Personal Atlassian and Databricks tokens act as the service identity | Service accounts (OSI-013) |
| Graph Mail.Send is granted on the OPS Hub sign-in app | A dedicated sender app (OSI-021) |
| Builds and deploys run from a laptop (scripted and gated) | A CI/CD pipeline (OSI-016) |
| Users are processed one after another | Parallel processing before about 50 users (OSI-017) |
| Analytics state is SQLite on Azure Files, copied in and out per run | Fine with one run at a time; revisit with OSI-017 |
| Unused legacy modules not on the live path: `agents/jira_writer.py`, `agents/confluence_writer.py`, `agents/data_fetcher.py`, `demo_run.py`, `fire_all_now.v1_backup_2026-10-09.py`, `AI Architecture/Onboarding_Server/` | To be deleted after the review |
| User profiles are kept in the repository (`AI Architecture/skills/Personal Skills/`) | They hold configuration (scope, alert levels), not metrics; moving them to the share only is under discussion |

## 6. Questions for the reviewer

1. **Correctness of the numbers.** Are the FTA, CoQ, efficiency and yield formulas, and the week rule in ADR-007, sound? See `analytics_agent.py` and `tests/test_alert_week.py`.
2. **Failure handling.** If Jira, Databricks or Graph fail mid-run, could a user get a wrong or duplicate email, or no email without anyone noticing?
3. **Security.** Escaping of JQL, SQL and HTML, the recipient checks, and how secrets are handled.
4. **Scale to 100+ users.** What should change first: the run time per user, the state on Azure Files, or the use of MCP?
5. **Maintainability.** `email_html.py` is about 1,900 lines. Should it be split, and where?

Please leave comments as GitHub review comments on this branch, or send them by email.
