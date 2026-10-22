# ADR-002: Container Apps job on 4 IST slots, one run at a time, no automatic retry

**Status:** Accepted (19–20 Oct 2026, moved from the laptop Task Scheduler to Azure).

## Context
The pilot ran from a laptop under the Windows Task Scheduler. Production needs to run without the
laptop, in the same landing zone and environment as OPS Hub, and must never send the same email
twice.

## Decision
- **Schedule:** an Azure Container Apps job `ops-native-ai-trigger`, cron `30 3,7,11,15 * * *` UTC,
  which is 09:00, 13:00, 17:00 and 21:00 IST.
- **One run at a time:** `parallelism 1`, plus a `RUN_LOCK` file on the share. A lock older than the
  timeout is treated as left over from a killed run.
- **No automatic retry:** `replicaRetryLimit 0`, because a retried run could resend emails. Instead
  there is a run report email after every run, and a catch-up where it is safe: UC3 at 21:00 if 17:00
  did not send, and a UC4 alert after a failed send.
- **Timeout:** 3.5 h, below the 4 h gap between slots.

## Consequences
- **Reliability:** no dependency on a laptop, and a missed or failed run is visible within minutes
  through the run report.
- **No overlap:** a slot can be skipped (and reported) when the previous run overran.
- **Manual runs:** a manual job start sends real emails, so it is never used as a test.
  `azure/sanity_check.py` checks the configuration instead.

## Revisit when
Runs approach the slot gap as users grow. Add parallel processing per user (OSI-017), or split the job
by use case.
