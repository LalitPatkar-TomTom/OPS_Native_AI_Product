"""Add the pilot history that only the laptop run log has to an analytics DB (used by copy_db_to_share.py).

Before 13 Oct 2026 emails and runs were written only to task_scheduler.log, not to the DB tables.
This counts them per IST day and use case, up to the moment each table starts, into table
history_log_daily, so pilot totals in the weekly analytics start on 1 Oct like the 19 Oct report.
Same counting rules as business_analytics/ba_extract2.py. Re-running replaces the table.
"""
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
TABLE = """CREATE TABLE IF NOT EXISTS history_log_daily (
    day_ist  TEXT NOT NULL,     -- YYYY-MM-DD
    uc_id    TEXT NOT NULL,     -- UC1..UC4, or RUN for completed scheduled runs
    count    INTEGER NOT NULL,
    source   TEXT NOT NULL,     -- where the number comes from
    PRIMARY KEY (day_ist, uc_id)
)"""


def _first_ist(con, sql) -> datetime | None:
    v = con.execute(sql).fetchone()[0]
    if not v:
        return None
    d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(IST).replace(tzinfo=None)


def import_history(db: Path, log: Path) -> dict:
    con = sqlite3.connect(db)
    emails_from = _first_ist(con, "SELECT MIN(ts) FROM email_deliveries WHERE is_test = 0")
    runs_from = _first_ist(con, "SELECT MIN(started_at) FROM trigger_runs WHERE is_test = 0")
    emails, runs, cur_uc = defaultdict(Counter), Counter(), None
    for l in log.read_text(encoding="utf-8", errors="replace").splitlines():
        if not re.match(r"2026-\d\d-\d\d \d\d:\d\d:\d\d", l):
            continue
        t = datetime.strptime(l[:19], "%Y-%m-%d %H:%M:%S")
        m = re.search(r"FIRE (UC\d) for", l)
        if m:
            cur_uc = m.group(1)
        if re.search(r"Email sent via (?:Outlook|Graph) ->", l) and (emails_from is None or t < emails_from):
            emails[l[:10]][cur_uc or "UC?"] += 1
        if "fire_all_now complete" in l and (runs_from is None or t < runs_from):
            runs[l[:10]] += 1
    con.execute("DROP TABLE IF EXISTS history_log_daily")
    con.execute(TABLE)
    src = f"laptop {log.name}"
    rows = [(d, uc, n, src) for d, c in emails.items() for uc, n in c.items()]
    rows += [(d, "RUN", n, src) for d, n in runs.items()]
    con.executemany("INSERT INTO history_log_daily VALUES (?,?,?,?)", rows)
    con.commit()
    con.close()
    return {"emails": sum(sum(c.values()) for c in emails.values()), "runs": sum(runs.values()),
            "days": sorted(set(emails) | set(runs)), "emails_until": str(emails_from), "runs_until": str(runs_from)}


if __name__ == "__main__":
    import sys
    print(import_history(Path(sys.argv[1]), Path(sys.argv[2])))
