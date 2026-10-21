"""Time saved by OPS Hub Status Reports, for the weekly analytics and the impact report.

Reads report_log.jsonl lines written by OPS Hub (OPSHUB app/report_log.py) since 21 Oct 2026:
each successful generated report carries its minutes (weekly pulse 60, bi-weekly 90, monthly 180,
quarterly 240, portfolio 240; +30 own template, +30 Confluence/document context, +15 per extra
scope value up to +60). Failed reports count 0. Regenerations count once: the same person, scope
and period on the same IST day is one report (its latest version is counted).
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
LABEL = {"pulse": "Weekly pulse", "trend": "Bi-weekly trend", "digest": "Monthly digest",
         "review": "Quarterly review", "portfolio": "Portfolio report", "custom_range": "Custom range"}
USED = ("export_word", "export_pdf", "publish_confluence")


def _day(ts: str):
    d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(IST).date()


def value(entries: list) -> dict:
    """Time saved for report_log entries (already filtered to the period)."""
    gen = [e for e in entries if e.get("event") == "generate"]
    ok = sorted((e for e in gen if e.get("ok")), key=lambda e: e["ts"])
    latest = {}                                  # one report per person, scope and period per day
    for e in ok:
        key = (e.get("email", "").lower(), e.get("scope_type", ""), tuple(sorted(e.get("scope_values") or [])),
               e.get("date_from"), e.get("date_to"), _day(e["ts"]))
        latest[key] = e
    reports = list(latest.values())
    used_ids = {e.get("report_id") for e in entries if e.get("event") in USED and e.get("report_id")}
    by_topic, min_by_topic, per_user = Counter(), defaultdict(float), defaultdict(float)
    for e in reports:
        t = e.get("topic", "custom_range")
        by_topic[t] += 1
        min_by_topic[t] += e.get("minutes", 0)
        per_user[e.get("email", "").lower()] += e.get("minutes", 0)
    return {
        "reports": len(reports), "generated": len(ok), "regenerations": len(ok) - len(reports),
        "failed": len(gen) - len(ok),
        "exported_or_published": sum(1 for e in reports if e.get("report_id") in used_ids),
        "exports": sum(1 for e in entries if e.get("event") in ("export_word", "export_pdf")),
        "publishes": sum(1 for e in entries if e.get("event") == "publish_confluence"),
        "users": len({e.get("email", "").lower() for e in reports if e.get("email")}),
        "minutes": sum(e.get("minutes", 0) for e in reports),
        "by_topic": by_topic, "min_by_topic": min_by_topic, "per_user": per_user,
    }
