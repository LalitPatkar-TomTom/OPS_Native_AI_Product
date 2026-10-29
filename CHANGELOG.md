# Changelog: OPS Native AI

## v2026-10-29-2: no LLM leftovers (29 Oct 2026)

- **No model setting on the job:** `DATABRICKS_LLM_MODEL` is no longer sent to the Azure job (`deploy_job.SKIP`).
  Nothing in the engine read it; the engine makes no LLM call (ADR-001). OPS Hub keeps its own model setting.
- **Retired laptop onboarding server archived:** `AI Architecture/Onboarding_Server` and `UserOnboarding.HTML`
  moved to `_archive/` (see its README). It was the only code here that called an AI model (Sonnet, for the
  profile merge), replaced by OPS Hub `/onboarding` in October; `start.bat` no longer starts it.
- **Unused LLM helpers removed** from `registry_mcp.py` (`openai_tools`, `anthropic_tools`); `.env.example`
  no longer lists a model or the onboarding server's port.
- **Guard test** `tests/test_no_llm.py`: fails if an AI library or a Model Serving call is added to the
  shipped code, or if the job gets a model setting again.

## v2026-10-29-1: root causes and actions, work units (29 Oct 2026)

- **Root causes and actions** (`agents/root_cause.py`, ADR-008; OSI-027/035/040, first part of OSI-047):
  every KPI past its level gets a rule-based driver tree against the previous full week, with no AI.
  - FTA: the work units that moved it; coaching when a few editors make the rejections, the work package
    when it fails across 3 or more editors; the sampling effect; more edited tasks.
  - CoQ: rejections, sampling, QC minutes per task and production speed, with the two chains (rejection →
    sampling → CoQ, more edits → QC time → CoQ), over-sampled high-FTA areas, and the sampling that would
    reach 7%.
  - Efficiency: the work packages losing the most hours against their baseline, and hours with no completed
    task. Yield: the lowest work unit.
  - Shown in the Recommended actions box (UC1, UC4 and now UC3) and in the Word report. It falls back to
    the 26 Oct text when the rows cannot be read. Error types still need the ORBIT QC feedback categories.
- **Work units:** operators carry their work unit. The operator section (UC1/UC3), the UC4 operator table and
  the Word table are grouped by work unit, with "N of M operators past a level" per unit.
- `metrics_4w` also carries the week's totals (QC'd, accepted, tasks, hours) for the CoQ split.

## v2026-10-27-1: fixes from the 27 Oct 09:00 run check (27 Oct 2026)

- **Subjects:** UC2 and UC4 subjects show the Jira key (e.g. "OM") instead of "Project".
- **Alerts wait for production hours too:** this week is used only once it also has 20% of last week's
  production hours; CoQ and efficiency are hour-based, and hours arrive after QC counts (a scope read CoQ
  36% with 14% of its hours). The label says which bar is not reached yet (ADR-007).
- **Jira past 100 tickets:** up to 1,000 open tickets per profile, MCP and REST both paging; counts are
  complete, and ticket lists in the email stay at the oldest 100 with "+N more in Jira".
- **Operators:** up to 50 operators past a level, those with the most hours in the scope first, then by task
  volume (was the first 40); all of them when fewer. Yield per operator
  above 100% (too few tasks to attribute) is left out, with a note.

## v2026-10-26-1 … -8: beta feedback (26 Oct 2026)

**Jira (UC1, UC2)**
- **Created-date window:** only tickets created in the last 12 months by default; a profile can set
  `**Jira created since:**` or `**Jira created within:**` (OSI-003, 025, 037).
- **SLA levels per profile,** in hours or days, read only from the "SLA — Warning/Escalation" lines
  (OSI-006); the UC2 email explains the rule (OSI-034).

**Which week, and how sure**
- **Date ranges everywhere,** in subjects too, and the week rule in ADR-007: Monday = last week;
  Tuesday–Sunday = this week so far, with the previous full week as reference (OSI-031).
- **Alerts trust this week** only from 50 QC'd tasks and 20% of last week's volume; before that they
  use last week and say why.
- **Small samples are never flagged:** fewer than 10 QC'd tasks are shown greyed and listed last (the
  "Lowest FTA 0.00%" from one task is gone).

**Content**
- **Recommended actions** with the likely root cause at the top of UC1 and every UC4 alert
  (OSI-027/035/040, first step).
- **No scope in the profile:** no quality or efficiency figures, a note asking for the scope; Jira is
  unchanged; UC4 skipped.
- **Six headline KPIs** for everyone: FTA, Eff vs BL, CoQ, Yield, Hours, Sampling; only the profile's
  metrics have a RAG badge and alert (OSI-008).
- **Alert levels per process type / planning ID** from the Metrics Profile's Scope column, exact names;
  whole-scope rows work as before (OSI-030).
- **Yield like the other metrics:** every work unit (DPU RMSI included), per planning ID, and a note
  when the scope has no Yield (only Orbit SD has it today; OSI-004, OSI-041).
- **Operators past an alert level,** with all six KPIs, for Operational Leads and Level = Operator
  profiles, in UC1, UC3 and UC4 (OSI-009). Operators are shown by name; HR check open.
- **Subject status = body status;** the Jira key instead of "Project (OM)".

**Analytics**
- **Minutes per email from real-user feedback:** UC1/UC2/UC4 25, UC3 60 (ADR-006, OSI-023).

**Release flow**
- `azure/release.sh` waits for the job to finish provisioning before the sanity check.
- Tests: 113 (from 73).

## v2026-10-22-1: architecture review hardening (22 Oct 2026)

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
