# ADR-008: Root causes and actions as rule-based driver trees

**Status:** Accepted (29 Oct 2026, with the product owner, after leads asked for the 28 Oct prototype's root
causes and actions in every email; OSI-027 / 035 / 040 / 047).

## Context
Leads said the emails repeat Power BI. What they want is why a KPI missed its level and what to do about it.
The 28 Oct prototype lead mail did this by hand for RM Lanes. The first step, live since 26 Oct, named only the
two process types behind a low KPI. AI-written root causes were rejected for now: they cost tokens at 50–100
users (OSI-049), and beta users said "trust the numbers first" (OSI-045). An AI root cause can also invent a
cause that the data does not show.

## Decision
- **Rules, not AI.** `agents/root_cause.py` builds a driver tree for each KPI from the reported week and the
  previous full week of the KPI table, in the profile's scope and on the same QC rows as the headline, so
  every number reconciles. ADR-001 still holds: there is no LLM anywhere in the send path.
- **FTA:** what changed and where (each work unit's effect in FTA points). Then who: if editors below the FTA
  level make at least 50% of the rejections, the action is to coach them, by work unit. If a work package
  fails across 3 or more editors, the action is to review its instructions, specs or data. Then the sample:
  if more of the QC'd work came from editors who were already low last week while the others held steady,
  the drop is called a sampling effect. Finally edits: more tasks closed with a map edit.
- **CoQ:** the change against the previous full week splits exactly into four drivers: rejections (each
  rejection is reworked and QC'd again), sampling, QC minutes per QC'd task and production minutes per task.
  Each driver has one action. Two chains, as the leads read them:
  - higher rejection → lower FTA → the sampling rule QCs more → higher CoQ;
  - more edited tasks (Publish / Accepted share, Orbit SD only) → more QC time per task → higher CoQ.
  
  The tree also flags FTA up with sampling still up, high-FTA areas still sampled at 15% or more, and the
  QC time spent on low-FTA editors. "Why it is at X%" gives the sampling that would bring CoQ to 7% at
  today's QC and production times.
- **Efficiency:** the work packages that lose the most hours against their process type's baseline
  (hours booked minus tasks ÷ baseline), and hours booked with no completed task.
- **Yield:** the work unit with the lowest yield.
- **Shown** in the Recommended actions box of the daily briefing, the metric alerts and the weekly report,
  and as a "Root Causes & Actions" section in the Word report. Only KPIs past their level are shown. If the
  root-cause rows cannot be read, the box falls back to the 26 Oct process-type cause.
- **Privacy:** editors are counted, never named, in the box. Names stay in the operator section that only
  leads get (HR check open, OSI-009). The operator section is now grouped by work unit.

## Consequences
- Every run makes two extra read-only queries (per editor for 2 weeks, per work package for 1 week) plus one
  on the yield view. Measured on the RM Lanes scope: 355 editor rows and 99 work packages.
- **Partly done, said in the email:** the error types behind rejections need the QC feedback categories from
  ORBIT, which no table we read holds. The edits chain is confirmed from data only for Orbit SD work.
- The thresholds (10 QC'd per editor, 20 per area, 80% of baseline, 97% FTA / 15% sampling, 50% share, 3
  editors) are constants at the top of `root_cause.py`. Change them there, with the tests.
