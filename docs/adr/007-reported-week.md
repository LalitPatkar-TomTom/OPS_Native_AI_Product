# ADR-007: Which week each email reports, and when alerts trust this week

**Status:** Accepted (26 Oct 2026, decided with the product owner after beta feedback OSI-028/031/032/036).

## Context
The Databricks quality table has one row per calendar week (Mon–Sun) and no day column. The current
week fills up day by day. Early in the week it is a small, unrepresentative sample: on Monday
26 Oct, CoQ read 64% and efficiency 23–39% from a few hours of work, against about 18% and 100%+ for
the full week before. Users could not tell which days a number covered, and some compared a
part-week with a full month in Power BI.

## Decision
- **Daily briefing (UC1):** on Monday, last week with its full dates, "Mon 19 Oct – Sun 25 Oct 2026
  (last week)". On Tuesday to Sunday, this week from Monday to today, "Mon 26 Oct – Tue 27 Oct 2026
  (this week so far)", with the previous full week as a reference row.
- **Metric alerts (UC4):** this week first, but only once it has at least **50 QC'd tasks and 20% of
  last week's QC'd tasks** in the profile's scope (`analytics_agent.ALERT_MIN_QC`, `ALERT_MIN_SHARE`).
  From 27 Oct also **20% of last week's production hours**, because CoQ and efficiency are hour-based and
  hours arrive after QC counts (`alert_hours_too_early`). Otherwise last week, labelled
  "(last week · this week too early: N QC'd / N production h so far, alerts use it from M)".
- **Everywhere:** the exact date range is in every subject, header, section and data-period row
  (`email_html.period_label`).
- **Small samples:** a process type, work unit or planning ID with fewer than 10 QC'd tasks is shown
  but never flagged (`MIN_QC_TO_FLAG`). Operators need 10 QC'd tasks for FTA and 10 production tasks
  for the other metrics (`OP_MIN_TASKS`).

## Consequences
- **Monday:** the briefing never shows an empty or tiny week.
- **Alerts:** no false alerts from part-weeks. The bar scales with each scope, so small scopes switch
  to this week at 50 QC'd tasks and large ones after about a day of normal work.
- **"So far" ends at today, not at the last day loaded,** because the table has no day column.

## Revisit when
The source table gets a day column or a load timestamp (then "so far" can name the last loaded day),
or users report that alerts switch to the current week too late.
