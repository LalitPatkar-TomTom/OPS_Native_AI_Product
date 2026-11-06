# Changelog: OPS Native AI

## v2026-11-06-2: one combined metric alert per run, time saved per breach (6 Nov 2026)

- **OSI-043 (part 2, Pranav): every UC4 metric past its level in a run goes out in one email.** `_run_uc4`
  collects the alerts and `_send_uc4_alerts` sends them: one alert alone is exactly the email of before (same
  subject, byte-for-byte the same HTML); two or more are one email "UC4 Alert RED — N metrics past their level:
  COQ 14.75%, YIELD 82.82%, …" with a summary table (now, level, gap) worst first by the gap relative to the level,
  then each metric's usual section (`email_html.build_alert(..., body_only=True)`, `build_combined_alert`; the
  shell moved to `_alert_shell`). Each metric keeps its own once-a-day state and audit row; a metric already
  alerted today is left out; a failed send marks none. `UC4_COMBINED_ALERT=0` = one email per metric. On the
  6 Nov profiles: 13 UC4 emails → 7, same charts; every other email identical. Decision: ADR-013.
- **OSI-023 (rest): time saved counts UC4 per breach, not per email** (`azure/weekly_analytics.uc4_items`): each
  breach alerted (user × metric × day, `uc4_alert_state`) counts 25 min, alone or in a combined email; days before
  the state table (9 Oct) still count emails. The consolidated table's UC4 row reads "Metric Alert (UC4),
  breaches". ADR-006 amended.
- Tests: `tests/test_osi043_023.py` (functional, technical).
- What's new note for OSI-043 dated 7 Nov: this release goes out after today's 17:00 What's new email, and
  a note dated 6 Nov would fall before next Friday's window (`week_notes`: after the last email's Friday).

## v2026-11-06-1: every Jira key, trend charts in UC3/UC4, not-assigned tickets, weekly report fix (6 Nov 2026)

- **OSI-061 (Girish): every Jira key of the Active projects is checked, not only the first.** `load_skill` adds
  `jira_projects` (the distinct keys of the "Jira Key" column, in table order; `jira_project` stays the first key
  for links and old callers). The SLA search is `project in (OM, MCPET)` for several keys and still exactly
  `project = OM` for one. With several keys each one is looked up first (`jira_agent.project_status`, MCP then
  REST): a key Jira cannot find is named in a warning in the briefing, the UC2 alert and the weekly report while
  the others are checked (`missing_keys`, `key_warning`); only when every key is missing is Jira "not checked",
  as before. Emails and subjects name every checked key (`skill_registry.jira_label`, "OM, MCPET"); a create-
  ticket link uses the first. The profile check and the daily Jira-key reminder check every key. Profiles
  without a "Jira Key" column keep their single key: their old "Code" column mixes project codes (GDN, TMC ...)
  that are not Jira projects. Decision: ADR-012.
- **OSI-010 (rest, Pranav): the 8-week trend charts are also in the UC3 Weekly Report and the UC4 alerts.**
  UC3: a new section "8-Week Trend per Process Type" with the daily briefing's chart row for the 8 process types
  with the most hours. UC4: under "Contributing Process Types", a small chart of the alerting metric for each
  process type past the level (at most 4, alert level as the dashed line). Same trend data as the daily briefing
  (no extra query); images inline (cid). A chart that cannot be drawn is left out with a WARNING; the email
  always goes. The Word report and previews are unchanged (no images asked for).
- **OSI-056 (part): UC2 lists "Not assigned" tickets**: open tickets in the same scope with no assignee, oldest
  first, at most 15, with status and days open; not counted as SLA breaches and sent only with an SLA alert (no
  new daily email). "Not linked" waits for the reporter.
- **Fix: the weekly report failed for a user whose previous week had no Yield value** (`float - None` in the
  4-week trend table, found 6 Nov 2026 in the old-vs-new run; it failed on main too, so that user's weekly
  report was not sent). A week without a value now shows N/A or no arrow (`email_html_weekly._trend_arrow`);
  arrows for normal data are unchanged. Every other user's emails were identical before and after the fix.
- Tests: `tests/test_osi061_010_056.py` (functional, technical, performance).

## v2026-11-05-1: the daily briefing per process type, for everyone (5 Nov 2026)

- **Why:** a baseline is valid only for its own process type. With several process types the briefing showed
  scope-wide "actual vs baseline tasks/hr (baseline = average of the process types in scope)", which means
  nothing to a lead (user, 4 Nov; OSI-057). Overall FTA and CoQ were already pooled (volume-weighted) and
  overall efficiency weighted since 30 Oct; the gap was the presentation and the per-type fallback.
- **The UC1 daily briefing is now the per-process-type layout for every user** (user, 5 Nov: "keep this as daily
  briefing ... for everyone"). `orchestrator.run_uc1` builds it with `email_briefing_pt.build_daily` and passes
  the charts to `deliver(html_body=..., inline_images=...)`. **Safeguards:** `BRIEFING_LAYOUT=classic` on the job
  switches back without a release; if the new layout fails for a user that user gets the classic layout and a
  WARNING in the run report, and if that fails too, plain text as before. `deliver()`'s own build stays classic,
  so UC2/UC3/UC4 and every other email are unchanged. Decision: ADR-011. Tests: `tests/test_briefing_switch.py`.
- **Fix (live bug): UC1 crashed for profiles with planning IDs when FTA was not green** ("Unknown format code
  'f' for object of type 'str'"): the plain-text briefing's planning-ID loop overwrote the scope FTA with text.
  The user got no daily briefing that run (Sheetal 4 Nov 09:00, Girish 5 Nov 09:00, both in the run reports).
  Found in the 5 Nov full local run; `briefing_agent` uses its own names in that loop now. Test in
  `tests/test_briefing_switch.py`.
- **Classic layouts no longer print "Actual x vs baseline y tasks/hr (baseline = average of the process types
  in scope)"** (UC3 weekly, Word, UC4, the fallback and the plain-text briefing): they print the earned-hours
  basis of the same % (`email_html.eff_earned_text`, e.g. "1,357 h of work at each process type's own baseline
  in 1,162 h booked"). The % itself is unchanged.
- **The layout (`email_briefing_pt.py`):** status + actions, "what changed" with
  a work-mix split (rate vs mix, this week's weights), **one table of all process types** (tasks, hours,
  actual and own baseline tasks/hr, hours at baseline, Eff vs own BL, FTA, CoQ; 12 rows + "Other") with a
  **Total row built from the rows** that adds only what can be added (hours, hours at baseline, FTA/CoQ
  pooled; tasks and tasks/hr left empty) and its 8-week trend (user, 5 Nov: "instead of cumulative can we
  have such table"), then a card per process type needing attention (why, work units, notes, 8-week trend
  + trend word), operators first for Operational Leads / planning IDs first for PMs, only SLA tickets (15
  oldest).
  Never scores a type against the scope-average baseline ("no baseline" instead); Yield >100% hidden; a
  type below 50% of its baseline for 6 full weeks asks to check the baseline. Weekly data only.
- **Later the same day (user review of mock-ups v2-v5):** no combined "Total, last 8 weeks" trend (each process
  type has its own); **Yield** in the table (Total pooled) and in each trend (`_YIELD_PT_TREND_SQL`,
  `add_yield_trend`); **line charts** as the trend (`briefing_charts.py`, matplotlib, inline cid images; numbers
  table only when images cannot be sent); `delivery._send_email/_send_graph/_send_outlook(inline_images=...)`,
  passed only when there are images so every existing email is unchanged; **crisp recommended actions** = action
  + the one root cause it rests on (`root_cause.analyse` adds `"root"`; classic box unchanged); **operators**:
  judged only with at least 8 production hours (user: "only focus on prod hrs"), worst 25 (most levels missed,
  then production hours) and best 5 in the team (relative, not in the worst list, no FTA/yield problem, with a
  factual remark); `_OPERATOR_SQL` adds `prod_hrs`. Tests: `tests/test_briefing_pt_v4.py`.
- **Analytics (additive, classic email unchanged):** `_PT_TREND_SQL` (read-only, 8 weeks per process type),
  `pt_trends`, `trend_word`, `mix_split`, `trend_mondays`; `process_breakdown[i].trend / own_baseline /
  eff_from_scope_average`, `overall_trend`, `trend_weeks`. No LLM (rules, SQL, templates; test_no_llm green).
  Tests: `tests/test_briefing_pt.py`.

## Unreleased (branch osi-002-jira-key-column): Jira key from the "Jira Key" column (3 Nov 2026)

- **The Jira key is read from the profile's "Jira Key" column** when the Active Projects table has one (the
  OPS Hub form writes Activity / Project · Planning ID · Jira Key · Role · Status from 3 Nov). A planning ID
  in the next column can no longer be taken for a key. Older profiles read exactly as before: checked on all
  48 profile files on the laptop. Release this before the OPS Hub form change. Decision: ADR-010.
  Tests: `tests/test_project_table.py` (184 tests).

## Unreleased (branch rulebook-safeguards): rule book safeguards (2 Nov 2026)

- **Daily analytics DB snapshots are never deleted:** older than the newest 30 they move to
  `backups/archive/` on the share (before: deleted, from about mid-November).
- **Every release starts with a checked backup** of all three shares (`azure/verify_backup.py`, same as
  OPS Hub's) and stops when it is incomplete; the storage key is in an environment variable, never on a
  command line. `BACKUP_ONLY=1` stops after the backup check.
- **No release in a run window** (`azure/release_window.py`): 15 minutes before to 45 minutes after
  09/13/17/21 IST.
- **Delete guard:** `tests/test_no_data_delete.py`. Decision: ADR-009. Tests:
  `tests/test_release_safeguards.py`.
- **No more false "All clear" for Jira** (found in the 2 Nov 09:00 run): Jira search answers 0 tickets for a
  project key that does not exist (or the engine's Jira account cannot see), so the profiles with Geocoding,
  GDN, QA and LMDF got "Jira SLA: All clear" and GREEN every day. The project is now looked up first (read-only,
  once per key per run, `jira_agent.project_missing`); when Jira answers 404 the briefing, weekly email and Word
  report say "Jira SLA: Not checked" with the reason, the overall status is at least AMBER, the UC1 subject says
  "Jira not checked" and the actions list it. Tests never call Jira (autouse stub in `tests/conftest.py`).
  Tests: `tests/test_jira_not_checked.py`. What's new note added.
- **The project is checked by the run's own route:** the MCP search's "does not exist" error stops the run from
  falling back to REST; before a REST search the project is looked up with the same account
  (`jira_agent.project_status` / `project_missing`). A REST-only check would have flagged DPOT, which the MCP
  reads fine but the REST account cannot see.
- **Daily Jira-key reminder** (`profile_check.py`, user 2 Nov): at the 09:00 run, every profile whose Jira project
  key the run cannot read gets one email a day until it is fixed (CC as the profile check: Ketki, Vrushali,
  Pratish, Lalit); table `profile_reminders` keeps one per profile per day; a Jira outage sends nothing. Before,
  only new or changed profiles were checked, and the profiles seeded on 21 Oct never were.
  `--reminders --to ADDRESS` sends them to one test address. Tests: `tests/test_profile_reminder.py`.

## v2026-10-30-2: weekly "What's new" email, automatic every Friday (30 Oct 2026)

- **Every Friday after the 17:00 IST run** the job sends "What's new in OPS Native AI & OPS Hub" from
  opsai@ to all beta users (every profile owner on the skills share) plus the stakeholders, like the Monday
  weekly analytics email (`comms/whats_new/send_weekly.py`, called from `azure/entrypoint.sh`). No review step.
- **Content:** `comms/whats_new/notes.json`, one functional note per user-visible change, written at release
  time; only notes dated after the last email are sent; a marker on the share prevents a second send, and a
  week without notes sends nothing. No AI model is involved.
- The 28 Oct prototype lead-mail scripts are kept in `prototypes/lead_mail/` (data and output git-ignored).
- Tests: `tests/test_whats_new.py`.

## v2026-10-30-1: fixes from the 30 Oct 09:00 run check (30 Oct 2026, released 11:33 IST)

- **One overall status, with the reason:** UC1 (body and subject), UC3 and the Word report use the same rule:
  SLA plus only the KPIs in the profile (a KPI with no alert level never turns an email red; Dhammaratna's
  false RED). The headline names the reason, e.g. "3 Jira tickets past the SLA" or "CoQ 14.64% past your alert
  level", instead of "quality metrics are below threshold" for every RED; no-scope profiles say so.
- **Overall efficiency weighted by the work done** (OSI-033): hours at baseline / hours booked over the process
  types, per week, so it agrees with the process-type and work-unit rows (was a plain average of baselines:
  9.2% overall with every row at 142-250%). The old value stays as fallback.
- **UC4 per metric:** Yield and Efficiency alerts show their own reference week, sorting (lowest yield first),
  advice and a Yield column, no longer FTA's. The root-cause box follows the user's own alert level (Shital's FTA
  alert at 96.3% vs her 98% had no box). Red CoQ is red, not amber.
- **Work-mix guard:** a CoQ factor moving more than 3x week on week is reported as a change of work, with the
  action taken from today's level (Devika: "production 69 -> 8 min per task" was read as faster production).
- **No repeated actions:** the older "Recommended Actions & Conclusion" and UC4 "Suggested Action" leave out
  KPIs the root-cause box explains; SLA follow-ups stay. Rows with no work unit read "work unit not recorded".

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
