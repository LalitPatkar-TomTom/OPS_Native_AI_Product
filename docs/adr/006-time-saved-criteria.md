# ADR-006: Time saved as fixed minutes per item, agreed and versioned

**Status:** Accepted (19–21 Oct 2026, agreed with the product owner).

## Context
The business case is reported as time saved. Measuring time saved per email is not possible, so the
measure must be simple, transparent and stable, so that reports can be compared week to week.

## Decision
- **Minutes per item:** each delivered item counts a fixed number of manual minutes avoided:
  - UC1 briefing: 20
  - UC2 SLA alert: 10
  - UC3 weekly report: 90
  - UC4 metric alert: 15
- **Where it lives:** `azure/weekly_analytics.py` `MINUTES`.
- **Not counted:** test sends and parallel-mode sends.
- **OPS Hub:** chat answers and Status Reports are valued per item, from the work each one did
  (`app/time_saved.py` and `app/report_log.py` in OPSHUB). Those values are versioned.

## Consequences
- **Explainable:** the figures can be explained in one sentence and recomputed from the analytics DB.
- **Changes must be deliberate:** a unit test pins the values, so changing them is a decision, not
  an accident.
- **Estimates, not measurements:** they are estimates of avoided effort (capacity freed), not
  measured time or headcount, and are presented that way.

## Revisit when
Real time-and-motion figures from users are available. Update the minutes, record the date and the
source here, and keep the old version for past reports.
