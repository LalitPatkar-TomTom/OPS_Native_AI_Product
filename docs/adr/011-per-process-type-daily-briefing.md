# ADR-011: The daily briefing measures each process type against its own baseline

**Status:** Accepted, 5 Nov 2026. Issue OSI-057 (also OSI-044, OSI-010/038 weekly part, OSI-009, OSI-033).
Related: ADR-001 (no LLM), ADR-007 (reported week), ADR-008 (root causes).

## Context
A baseline (tasks per hour) is valid only for its own process type. With several process types, the UC1 summary
showed "Actual 6.413 vs baseline 5.490 tasks/hr (baseline = average of the process types in scope)": tasks of
different process types added up, against a baseline that was the scope % worked backwards. Leads read it as an
average that "does not make sense" (user, 4–5 Nov). The overall FTA and CoQ were already pooled, and the overall
efficiency already weighted (earned hours, since 30 Oct); the problem was what the email showed and how.

## Decision
- **The UC1 daily briefing is the per-process-type layout** (`email_briefing_pt.py`) for every user, in this order:
  status, recommended actions (each = the action + the one root cause it rests on), what changed (with a
  work-mix split: rate at this week's weights vs mix), **one table of all process types**, each against its own
  baseline (tasks, hours, actual and own baseline tasks/hr, hours at baseline, Eff vs own BL, FTA, CoQ, Yield),
  **a Total row that adds only what can be added** (hours, hours at baseline, FTA/CoQ/Yield pooled; tasks and
  tasks/hr left empty), then a card per process type that needs attention (why, work units, notes, **8-week
  line charts** with reference lines), operators (judged only with at least 8 production hours: worst 25, best 5
  in the team), planning IDs, and only the Jira tickets past or close to the SLA.
- A process type without its own baseline shows "no baseline"; it is never scored against another baseline. A
  type below 50% of its baseline for 6 full weeks is shown as "the baseline may be wrong".
- Weekly data only (no day column); the current week is "so far" and left out of trend words.
- Charts are PNGs drawn by matplotlib (rules only, ADR-001) and sent as inline images (`cid:`), through Graph
  and Outlook (`delivery._send_email(inline_images=...)`, passed only when there are images).
- **Safeguards:** `BRIEFING_LAYOUT=classic` on the job switches back without a release; if the new layout fails
  for a user, that user gets the classic layout and a WARNING in the run report; if that fails too, plain text as
  before. `deliver()`'s own build stays classic, so no other email changes.
- The classic layouts (UC3 weekly, Word, UC4 alerts, the fallback) no longer print the scope-wide tasks/hr; they
  print the earned-hours basis of the same %.

## Consequences
The figures are unchanged (checked on live data for three users: every Total matches the classic headline);
the email is about 40% smaller before charts (charts add 35–55 KB each, up to 8). UC3 and UC4 keep their
layout until users comment on the daily briefing.

## Revisit
When daily data arrives (switch the comparison period), when Yield exists beyond Orbit SD (OSI-041), and after
the beta users' comments.
