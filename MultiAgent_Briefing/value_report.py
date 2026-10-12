"""
Business-value report for OPS Native AI, built from output/trigger_audit.db.

    python value_report.py                 # last 7 days
    python value_report.py --days 30
    python value_report.py --minutes UC1=15,UC2=10,UC3=60,UC4=15
    python value_report.py --include-test  # also count test / preview runs
    python value_report.py --db <copy.db>  # read another copy, e.g. a backup

Writes output/value_report_<date>.md and output/value_report_<date>.csv
(one row per user and use case) and prints the summary.

Time saved is an ESTIMATE: emails delivered x the minutes a user would
otherwise spend producing that information by hand. The minutes are
assumptions — set them with --minutes and state them when sharing numbers.
"""
import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import OUTPUT_DIR

DB_PATH = OUTPUT_DIR / "trigger_audit.db"
SLOT_HOURS = ("09:00", "13:00", "17:00", "21:00")
UC_NAMES = {
    "UC1": "Daily Operational Briefing",
    "UC2": "Jira SLA Follow-Up",
    "UC3": "Weekly Report",
    "UC4": "Quality & Metric Early Warning",
}
# Minutes a user would spend producing the same information manually (assumptions)
DEFAULT_MINUTES = {"UC1": 15, "UC2": 10, "UC3": 60, "UC4": 15}
ON_TIME_MIN = 30


def _parse_minutes(text: str | None) -> dict:
    m = dict(DEFAULT_MINUTES)
    for part in filter(None, (text or "").split(",")):
        k, v = part.split("=")
        m[k.strip().upper()] = float(v)
    return m


def _rows(con, sql, params=()):
    return [dict(r) for r in con.execute(sql, params)]


def _has_table(con, name):
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def build(days: int, minutes: dict, include_test: bool, db_path: Path = DB_PATH) -> tuple[str, list[dict]]:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    first_day = (date.today() - timedelta(days=days - 1)).isoformat()
    test_clause = "" if include_test else " AND COALESCE(is_test,0)=0"

    has_cols = {r[1] for r in con.execute("PRAGMA table_info(trigger_events)")}
    if "is_test" not in has_cols:
        test_clause = ""
    events = _rows(con, f"SELECT * FROM trigger_events WHERE ts >= ?{test_clause}", (since,))
    deliveries = (_rows(con, f"SELECT * FROM email_deliveries WHERE ts >= ?{test_clause}", (since,))
                  if _has_table(con, "email_deliveries") else [])
    runs = (_rows(con, f"SELECT * FROM trigger_runs WHERE started_at >= ?{test_clause}", (since,))
            if _has_table(con, "trigger_runs") else [])

    # ── Emails per use case (events are the full history; deliveries add recipients) ──
    sent = [e for e in events if e["status"] == "sent"]
    sent_by_uc = Counter(e["uc_id"] for e in sent)
    failed_by_uc = Counter(e["uc_id"] for e in events if e["status"] == "send_failed")
    users_by_uc = defaultdict(set)
    for e in sent:
        users_by_uc[e["uc_id"]].add(e["user_email"].lower())
    profiles = {e["user_email"].lower() for e in events}

    recipients, cc_counter = set(), Counter()
    for d in deliveries:
        if not d["sent_ok"]:
            continue
        recipients.add((d["to_email"] or "").lower())
        for cc in json.loads(d["cc_emails"] or "[]"):
            recipients.add(cc.lower()); cc_counter[cc.lower()] += 1
    recipients.discard("")

    # ── Alerts raised ──
    uc4_by_metric = Counter(e["metric_key"] for e in sent if e["uc_id"] == "UC4")
    uc4_repeats = sum(1 for e in events if e["uc_id"] == "UC4" and e["status"] == "suppressed")
    uc4_checks = sum(1 for e in events if e["uc_id"] == "UC4")
    uc2_sent = [e for e in sent if e["uc_id"] == "UC2"]
    sla_breaches = sum(e["sla_breaches"] or 0 for e in uc2_sent)
    sla_warnings = sum(e["sla_warnings"] or 0 for e in uc2_sent)
    # ── Jira tickets flagged by UC2 (keys recorded from the trigger-analytics update) ──
    tickets: dict = {}                      # key -> {days, max_hours, users, last_ts, level}
    last_uc2_check: dict = {}               # user -> latest UC2 check (sent or healthy)
    for e in events:
        if e["uc_id"] != "UC2" or e["status"] not in ("sent", "healthy"):
            continue
        u = e["user_email"].lower()
        last_uc2_check[u] = max(last_uc2_check.get(u, ""), e["ts"])
        if e["status"] != "sent":
            continue
        for col, level in (("sla_breach_tickets", "breach"), ("sla_warning_tickets", "warning")):
            for t in json.loads(e.get(col) or "[]"):
                rec = tickets.setdefault(t["key"], {"days": set(), "max_hours": 0, "users": set(),
                                                     "last_ts": "", "level": level})
                rec["days"].add(e["ts"][:10]); rec["users"].add(u)
                rec["max_hours"] = max(rec["max_hours"], t.get("hours") or 0)
                rec["last_ts"] = max(rec["last_ts"], e["ts"])
                if level == "breach":
                    rec["level"] = "breach"
    # Not flagged in the user's latest check any more → probably updated after the alert
    cleared = [k for k, r in tickets.items()
               if all(last_uc2_check.get(u, "") > r["last_ts"] for u in r["users"])]
    repeated = sorted((k for k, r in tickets.items() if len(r["days"]) >= 3),
                      key=lambda k: -len(tickets[k]["days"]))
    longest = sorted(tickets, key=lambda k: -tickets[k]["max_hours"])[:5]

    skipped = Counter(e["uc_id"] for e in events if e["status"] == "skipped")
    errors = Counter(e["uc_id"] for e in events if e["status"] == "error")

    # ── Reliability: scheduled slots served vs expected ──
    # A slot counts once: served if any scheduled run covered it, late if even the first was late
    first_delay: dict = {}
    for r in runs:
        if r["trigger_source"] == "scheduled":
            key = (r["slot_date_ist"], r["slot_ist"])
            first_delay[key] = min(first_delay.get(key, 10**9), r["delay_min"] or 0)
    served = set(first_delay)
    late = [k for k, v in first_delay.items() if v > ON_TIME_MIN]
    first_slot = min(served, default=None)          # tracking starts at the first slot served
    run_tracking_since = f"{first_slot[0]} {first_slot[1]} IST" if first_slot else None
    expected, missed = [], []
    if first_slot:
        start_dt = datetime.strptime(f"{first_slot[0]} {first_slot[1]}", "%Y-%m-%d %H:%M")
        d = max(date.fromisoformat(first_day), start_dt.date())
        now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        while d <= now_ist.date():
            for s in SLOT_HOURS:
                slot_dt = datetime.combine(d, datetime.strptime(s, "%H:%M").time())
                if slot_dt >= start_dt and slot_dt + timedelta(minutes=ON_TIME_MIN) <= now_ist:
                    expected.append((d.isoformat(), s))
                    if (d.isoformat(), s) not in served:
                        missed.append(f"{d.isoformat()} {s}")
            d += timedelta(days=1)

    # ── Time saved (estimate) ──
    hours_by_uc = {uc: sent_by_uc.get(uc, 0) * minutes.get(uc, 0) / 60 for uc in UC_NAMES}
    total_hours = sum(hours_by_uc.values())

    # ── Per user × UC table (CSV) ──
    table = []
    per = defaultdict(Counter)
    for e in events:
        per[(e["user_email"].lower(), e["uc_id"])][e["status"]] += 1
    for (u, uc), c in sorted(per.items()):
        table.append({
            "user": u, "use_case": uc, "sent": c.get("sent", 0), "send_failed": c.get("send_failed", 0),
            "healthy_checks": c.get("healthy", 0), "repeats_suppressed": c.get("suppressed", 0),
            "skipped": c.get("skipped", 0), "errors": c.get("error", 0),
            "est_hours_saved": round(c.get("sent", 0) * minutes.get(uc, 0) / 60, 2),
        })

    # ── Markdown ──
    period = f"{first_day} to {date.today().isoformat()}"
    L = [f"# OPS Native AI — Business Value Report", "",
         f"**Period:** {period} ({days} days)  ",
         f"**Generated:** {datetime.now():%Y-%m-%d %H:%M}  ",
         f"**Test runs:** {'included' if include_test else 'excluded'}", "",
         "## Headline", "",
         f"- **{sum(sent_by_uc.values())} emails delivered** to **{len(profiles)} profiles**"
         + (f", reaching **{len(recipients)} people** including CC" if deliveries else ""),
         f"- **{sum(uc4_by_metric.values())} metric alerts** raised and **{len(uc2_sent)} SLA follow-ups** "
         f"flagging {sla_breaches} breached and {sla_warnings} at-risk tickets",
         f"- **≈ {total_hours:.1f} hours saved** (estimate — see assumptions)", ""]
    L += ["## By use case", "",
          "| Use case | Emails sent | Users | Send failures | Minutes saved / email (assumed) | Est. hours saved |",
          "|---|---:|---:|---:|---:|---:|"]
    for uc, name in UC_NAMES.items():
        L.append(f"| {uc} {name} | {sent_by_uc.get(uc, 0)} | {len(users_by_uc.get(uc, ()))} | "
                 f"{failed_by_uc.get(uc, 0)} | {minutes.get(uc, 0):g} | {hours_by_uc[uc]:.1f} |")
    L += ["", "## Alerts", "",
          f"- Metric checks run: {uc4_checks}; alerts sent: {sum(uc4_by_metric.values())}; "
          f"repeat alerts held back (one per metric per day): {uc4_repeats}"]
    for m, n in uc4_by_metric.most_common():
        L.append(f"  - {(m or '?').upper()}: {n}")
    L += [f"- SLA follow-up emails: {len(uc2_sent)} — {sla_breaches} breaches (>72 h), {sla_warnings} warnings (>48 h) surfaced",
          "  (the same ticket can appear in several emails until it is updated)", ""]
    if tickets:
        n_breach = sum(1 for r in tickets.values() if r["level"] == "breach")
        repeated_txt = ", ".join(f"{k} ({len(tickets[k]['days'])} days)" for k in repeated[:8])
        longest_txt = ", ".join(f"{k} ({tickets[k]['max_hours']:.0f} h)" for k in longest)
        L += ["## Jira tickets flagged", "",
              f"- **{len(tickets)} distinct tickets** flagged ({n_breach} breached >72 h, "
              f"{len(tickets) - n_breach} warnings >48 h only)",
              f"- **{len(cleared)} no longer flagged** in the owner's latest check — most likely updated after the alert",
              f"- Flagged on 3 or more days: {len(repeated)}" + (f" — {repeated_txt}" if repeated else ""),
              f"- Longest without an update: {longest_txt}",
              ""]
    L += ["## Reliability", ""]
    if run_tracking_since:
        L += [f"- Scheduled slots due since run tracking started ({run_tracking_since}): {len(expected)}; "
              f"served: {len(expected) - len(missed)}; missed: {len(missed)}; "
              f"served more than {ON_TIME_MIN} min late: {len(late)}"]
        if missed:
            L.append(f"- Missed slots: {', '.join(missed[:20])}{' …' if len(missed) > 20 else ''}")
    else:
        L.append("- Run tracking not available for this period yet (added with the trigger-analytics update).")
    L += [f"- Skipped for quiet hours: {sum(skipped.values())}; errors: {sum(errors.values())}"
          + (f" ({', '.join(f'{k} {v}' for k, v in errors.items())})" if errors else ""), ""]
    if cc_counter:
        L += ["## Most copied (CC)", ""] + [f"- {a}: {n}" for a, n in cc_counter.most_common(5)] + [""]
    L += ["## Assumptions and data notes", "",
          "- Time saved = emails delivered × minutes a user would otherwise spend preparing that "
          "information manually: " + ", ".join(f"{uc} {minutes.get(uc, 0):g} min" for uc in UC_NAMES) + ". "
          "Change with `--minutes`.",
          "- It does not yet measure whether recipients read or acted on an email.",
          "- Audit history starts 2026-10-09; UC2, recipients and run tracking start with the "
          "trigger-analytics update. Earlier periods undercount."]
    return "\n".join(L) + "\n", table


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--minutes", help="e.g. UC1=15,UC2=10,UC3=60,UC4=15")
    ap.add_argument("--include-test", action="store_true")
    ap.add_argument("--db", type=Path, default=DB_PATH, help="audit DB to read (default: output/trigger_audit.db)")
    args = ap.parse_args()

    md, table = build(args.days, _parse_minutes(args.minutes), args.include_test, args.db)
    stamp = f"{date.today():%Y-%m-%d}"
    md_path = OUTPUT_DIR / f"value_report_{stamp}.md"
    csv_path = OUTPUT_DIR / f"value_report_{stamp}.csv"
    md_path.write_text(md, encoding="utf-8")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0].keys()) if table else ["user"])
        w.writeheader(); w.writerows(table)
    sys.stdout.reconfigure(encoding="utf-8")
    print(md)
    print(f"Saved: {md_path}\n       {csv_path}")


if __name__ == "__main__":
    main()
