# UC1 daily briefing per process type: full local run and old-vs-new check

**Date:** 05 Nov 2026 12:57 IST · **Branch:** daily-briefing-per-pt (before commit) · **Decision:** ADR-011
**Rule book:** 3 (functional, technical, performance), 7.5 (test emails to the owner only), 7.6 (old-vs-new).

## How it was run
- All 15 current profiles, copied read-only from the `opshub-skills` share.
- Full UC1 pipeline (`orchestrator.run_uc1`) with live Jira (REST), Databricks (read-only) and Confluence.
- Every email redirected to the owner (`TEST_RECIPIENT_OVERRIDE`), `EMAIL_CC=off`, no Teams, sent through the
  owner's Outlook; a guard refused any other recipient. Throwaway output folder: the real analytics DB was not written.
- Old-vs-new: for each profile, analytics read once, the classic and the new layout built from the same data;
  the new table's Total row compared with the classic headline.

## Results
- **Unit tests:** 257 passed (incl. `test_briefing_pt.py`, `test_briefing_pt_v4.py`, `test_briefing_switch.py`,
  `test_no_llm.py`).
- **Full run:** 14 of 15 sent with the new layout, 0 fallbacks, no ERROR lines. 1 crash (GP) from an existing
  live bug (below), fixed and re-checked with the same live data: briefing and new layout build (33 KB, 1 chart).
- **Old-vs-new:** 11 profiles with scope: Total = classic headline for all (largest difference 0.07 pts efficiency,
  0.02 pts FTA/CoQ/Yield, rounding). 4 profiles without scope: same "add your scope" note in both. The classic
  layout prints no tasks/hr any more (0 of 15).
- **Performance:** 9 profiles with scope took 48–192 s each (median
  121 s), about 23 min for all 15, one after another as in production. Email size
  4–112 KB HTML plus 0–4 charts of 35–55 KB (largest email ~290 KB with charts; Graph limit 4 MB). Chart drawing:
  8 charts in well under 15 s (unit test). The two new read-only queries per user were not timed separately:
  compare the 17:00 run duration with the runs before.

| User | Seconds | Full run | New KB | Classic KB | Charts | Total = headline | Diff eff / FTA / CoQ / Yield (pts) |
|---|---|---|---|---|---|---|---|
| DS | 47.9 | sent | 39.9 | 56.8 | 4 | yes | -0.06 / -0.01 / -0.01 / — |
| DD | 99.4 | sent | 17.2 | 36.5 | 0 | yes | -0.03 / +0.01 / -0.02 / — |
| GP | 165.9 | error (fixed, see below) | 33.9 | 60.9 | 1 | yes | +0.07 / -0.00 / +0.01 / +0.00 |
| KV | 0.6 | sent | 4.2 | 9.4 | 0 | no scope | — / — / — / — |
| LP | 190.7 | sent | 84.6 | 164.6 | 3 | yes | +0.03 / -0.00 / -0.00 / +0.00 |
| MG | 91.7 | sent | 46.2 | 84.2 | 2 | yes | -0.06 / -0.00 / +0.00 / +0.00 |
| NP | 1.1 | sent | 4.2 | 9.4 | 0 | no scope | — / — / — / — |
| PD | 100.0 | sent | 36.9 | 88.5 | 4 | yes | +0.05 / +0.00 / -0.00 / +0.00 |
| PB | 0.7 | sent | 4.2 | 9.3 | 0 | no scope | — / — / — / — |
| PD | 0.7 | sent | 4.2 | 9.4 | 0 | no scope | — / — / — / — |
| SS | 121.5 | sent | 18.0 | 28.0 | 0 | yes | +0.00 / +0.00 / -0.00 / — |
| ST | 177.8 | sent | 30.0 | 67.3 | 3 | yes | +0.06 / -0.00 / -0.00 / +0.00 |
| SD | 191.7 | sent | 93.0 | 168.1 | 3 | yes | +0.06 / -0.00 / -0.00 / +0.00 |
| VM | 121.4 | sent | 33.3 | 53.3 | 0 | yes | +0.04 / +0.00 / +0.00 / — |
| VK | 0.8 | sent | 4.2 | 9.4 | 0 | no scope | — / — / — / — |

## Live bug found and fixed
UC1 crashed for profiles with planning IDs when FTA was not green ("Unknown format code 'f' for object of type
'str'"): the plain-text briefing's planning-ID loop overwrote the scope FTA with text. In production this stopped
ST's briefing on 4 Nov 09:00 and GP's on 5 Nov 09:00 (both in the run reports). Fixed in `briefing_agent.py`,
regression test added.

## Safeguards in this release
- `BRIEFING_LAYOUT=classic` via `python azure/deploy_job.py --image <tag> --mode live --layout classic`
  switches back without a build; the sanity check shows the layout.
- New layout fails for a user: classic layout for that user, WARNING in the run report. Classic fails too:
  plain text, as before.
- `deliver()`'s own build and every other email unchanged (inline images passed only when there are any).
