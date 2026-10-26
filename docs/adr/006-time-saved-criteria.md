# ADR-006: Time saved as fixed minutes per item, agreed and versioned

**Status:** Accepted (19–21 Oct 2026, agreed with the product owner). Minutes updated 26 Oct 2026 from real-user feedback.

## Context
The business case is reported as time saved. Measuring time saved per email is not possible, so the
measure must be simple, transparent and stable, so that reports can be compared week to week.

## Decision
- **Minutes per item:** each delivered item counts a fixed number of manual minutes avoided. Since
  26 Oct 2026 the minutes come from **real-user feedback** (product owner, OSI-023):
  - UC1 briefing, UC2 SLA alert, UC4 metric alert: **25** each (they give key metrics and SLAs)
  - UC3 weekly report: **60** (report preparation, different in nature)
  - Before 26 Oct (assumed, used in the 19 and 20 Oct reports): UC1 20, UC2 10, UC3 90, UC4 15.
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
