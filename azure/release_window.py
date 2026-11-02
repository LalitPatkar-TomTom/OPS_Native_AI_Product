"""Stop a Native AI release that would overlap a scheduled run (rule book sections 2 and 7, 2 Nov 2026).

The job runs at 09:00, 13:00, 17:00 and 21:00 IST and writes the analytics DB on the share for up to ~25 minutes
(Monday 09:00 also sends the weekly analytics, Friday 17:00 the What's new). A backup taken during a run can
copy a half-written DB, and a job update during a run can cut it off, so azure/release.sh refuses to start from
BEFORE_MIN minutes before a run until AFTER_MIN minutes after it. Exit 0 = safe to release, 1 = wait.

Usage: python azure/release_window.py            (prints the next safe time when it is not safe now)
"""
import sys
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
RUN_HOURS_IST = (9, 13, 17, 21)       # same slots as deploy_job.CRON (03:30, 07:30, 11:30, 15:30 UTC)
BEFORE_MIN = 15                       # a release (tests, backup, build) can take 10+ minutes
AFTER_MIN = 45                        # longest run seen ~25 min, plus the weekly/What's new step and margin


def blocked_until(now: datetime) -> datetime | None:
    """When now (any timezone) falls in a run window, the IST time the window ends; else None."""
    now = now.astimezone(IST)
    for day in (now.date() - timedelta(days=1), now.date()):
        for h in RUN_HOURS_IST:
            run = datetime(day.year, day.month, day.day, h, tzinfo=IST)
            if run - timedelta(minutes=BEFORE_MIN) <= now < run + timedelta(minutes=AFTER_MIN):
                return run + timedelta(minutes=AFTER_MIN)
    return None


def main() -> int:
    """Print whether a release may start now; 0 = yes, 1 = wait."""
    until = blocked_until(datetime.now(timezone.utc))
    if until:
        print(f"STOP: a Native AI run is due or still running; release after {until:%H:%M} IST "
              f"(runs at {', '.join(f'{h:02d}:00' for h in RUN_HOURS_IST)} IST)")
        return 1
    print("    no run due in the next 15 minutes; safe to release")
    return 0


if __name__ == "__main__":
    sys.exit(main())
