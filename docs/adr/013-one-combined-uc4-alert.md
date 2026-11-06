# ADR-013: One combined UC4 alert per run

**Status:** Accepted · **Date:** 6 Nov 2026 · **Issue:** OSI-043 part 2 (beta survey, 27 Oct; asked for by a project manager)

## Context
Every metric past its level sent its own UC4 email, so one run could send a user up to five alerts in the same
minute (FTA, Efficiency, CoQ, Yield, plus scoped alerts). Users asked for one consolidated alert.

## Decision
- During a run, alerts are collected per metric, then sent together: **one alert alone is the email of before,
  byte for byte**; two or more go out as one email with a summary table (metric, now, level, gap), worst first by
  the gap relative to the level, then each metric's usual section (`build_alert(..., body_only=True)`).
- Each metric keeps its own once-a-day state and its own audit row, so suppression, the analytics counts and the
  value report keep working. A metric already alerted today is left out of the combined email.
- A failed send marks no metric, so all of them are retried at the next slot (same rule as before).
- `UC4_COMBINED_ALERT=0` switches back to one email per metric without a release.

## Consequences
- Fewer UC4 emails (13 → 7 on the 6 Nov profiles); the content is the same.
- Emails are no longer one per breach, so time saved counts breaches, not emails (ADR-006 amendment, OSI-023).
- Part 1 of OSI-043 (switch use cases and metrics off per project in the profile form) is still open.
