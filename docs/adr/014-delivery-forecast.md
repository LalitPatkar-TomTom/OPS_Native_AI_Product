# ADR-014: Delivery forecast per work package and OM ticket ("Ops Weather")

**Status:** Proposed, work in progress — the prediction still needs work (product owner, 9 Nov) · branch `delivery-weather`, not released · **Date:** 9 Nov 2026 · **Asked for by:** the product owner (6 Nov 2026)

## Context
Managers ask "when will this work package / OM be done". Pending work is in
`mo_occ_reporting.manual_efficiency.project_pending_task_tbl` (a snapshot, no date column); the real pace is in
the weekly KPI table. On 9 Nov 2026 most pending tasks sat in work packages nobody had booked hours on in 4 weeks
(4.95M tasks in WPs never seen in the KPI table), so a forecast must say "waiting" instead of inventing a date.

## Decision
- Grouped by **work package and OM ticket, never by process type** (product owner, 6 Nov).
- Work days left = pending tasks / tasks done per work day over the **last 4 full weeks** (= tasks/h x editors'
  hours per day). The running week is left out because it is partial.
- Basis, in order: the WP's own pace (at least 50 tasks in 4 weeks); else its OM's pace, and the WP is forecast to
  finish with its OM (all of the OM's pending / the OM's pace); else "trickle" or "no editor in 4 weeks", with no
  number. 50 tasks: below it a pace gives absurd numbers (1 task in 4 weeks = 674,840 days).
- OM key = DeliverableID, else "OM-nnnnnn" in the WP name.
- **ADP, training and pilot process types are left out** (product owner, 9 Nov); WPs without a process type stay.
- The PM must understand each number: a "How to read this" box with one real row worked through, the evidence in
  the Basis column, and "> 1 year" instead of a figure past 250 work days.
- Bands: sunny up to 20 work days, cloudy 21-60, rainy over 60, storm for trickle / no editor.
- Scope: the pending table has no planning ID, so a WP is in a profile's scope when its process type or name
  matches a profile name / keyword, or the profile's KPI scope booked work on it in the last 8 weeks.
- Shown as a section of the UC3 weekly email. Rules and one read-only SELECT, no LLM (ADR-001). A failure leaves the
  section out and never stops the report; `DELIVERY_FORECAST=0` switches it off without a release.

## Consequences
- The section names stalled work packages, which managers may not have seen before.
- The pending table's refresh time is unknown, so the email shows no "data as of" time for it yet.
- Not in the Word report yet.
