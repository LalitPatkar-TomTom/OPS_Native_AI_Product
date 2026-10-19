"""Full-period (1 Oct →) totals from the run log: emails per use case per day, runs per slot."""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\patkar\OneDrive - TomTom\Deployed\OPS_Native_AI_Product\MultiAgent_Briefing\output")
OUT = Path(__file__).resolve().parent
lines = (ROOT / "task_scheduler.log").read_text(encoding="utf-8", errors="replace").splitlines()

cur_uc = None
emails = defaultdict(Counter)          # day -> uc -> n
recips = defaultdict(set)              # day -> people reached (to + cc)
fires = defaultdict(Counter)
runs = []                              # (day, start time)
users_to = set()
for l in lines:
    if not re.match(r"2026-1\d-\d\d", l):
        continue
    day = l[:10]
    m = re.search(r"FIRE (UC\d) for (\S+)", l)
    if m:
        cur_uc = m.group(1)
        fires[day][cur_uc] += 1
    m = re.search(r"Email sent via (?:Outlook|Graph) -> (\S+)(?: \(CC: (.*)\))?", l)
    if m:
        emails[day][cur_uc or "?"] += 1
        recips[day].add(m.group(1).lower())
        users_to.add(m.group(1).lower())
        for c in (m.group(2) or "").split(","):
            if c.strip():
                recips[day].add(c.strip().lower())
    if "UCs to fire this slot" in l:
        runs.append((day, l[11:16]))

days = sorted(emails)
tot = Counter()
for d in days:
    tot.update(emails[d])
D = {
    "days": days,
    "emails_by_day_uc": {d: dict(emails[d]) for d in days},
    "emails_total": sum(tot.values()),
    "emails_by_uc": dict(tot),
    "people_reached_by_day": {d: len(recips[d]) for d in days},
    "distinct_profile_owners_emailed": sorted(users_to),
    "runs": runs,
    "runs_by_day": dict(Counter(d for d, _ in runs)),
    "fires_total_by_uc": dict(sum((fires[d] for d in fires), Counter())),
}
json.dump(D, open(OUT / "ba_data2.json", "w", encoding="utf-8"), indent=1)
print("days:", days[0], "→", days[-1], len(days), "| emails total:", D["emails_total"], D["emails_by_uc"])
print("runs:", len(runs), D["runs_by_day"])
print("people reached/day:", D["people_reached_by_day"])
print("profile owners emailed:", len(users_to))
