"""Business-analytics extract for OPS Native AI + OPS Hub (read-only). Writes ba_data.json."""
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\patkar\OneDrive - TomTom\Deployed\OPS_Native_AI_Product")
OUT = Path(__file__).resolve().parent
con = sqlite3.connect(f"file:{ROOT / 'MultiAgent_Briefing/output/trigger_audit.db'}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
q = lambda sql, *a: [dict(r) for r in con.execute(sql, a)]
D = {}

# ── events (9 Oct →) ──
ev = q("SELECT * FROM trigger_events WHERE is_test = 0")
D["events_total"] = len(ev)
D["events_by_uc"] = Counter(e["uc_id"] for e in ev)
D["events_by_day_uc"] = defaultdict(dict)
for e in ev:
    d = e["ts"][:10]
    D["events_by_day_uc"][d][e["uc_id"]] = D["events_by_day_uc"][d].get(e["uc_id"], 0) + 1
D["status_by_uc"] = {uc: Counter(e["status"] for e in ev if e["uc_id"] == uc) for uc in sorted(D["events_by_uc"])}
D["users_active"] = sorted({e["user_email"].lower() for e in ev if e["user_email"]})
D["users_by_day"] = {d: len({e["user_email"].lower() for e in ev if e["ts"][:10] == d}) for d in sorted({e["ts"][:10] for e in ev})}
D["projects"] = sorted({e["project_name"] for e in ev if e["project_name"]})

# UC4 alerts: breached metric checks
uc4 = [e for e in ev if e["uc_id"] == "UC4"]
D["uc4_checks"] = len(uc4)
D["uc4_status"] = Counter(e["status"] for e in uc4)
D["uc4_rag"] = {m: Counter(e[f"{m}_rag"] for e in uc4 if e.get(f"{m}_rag")) for m in ("fta", "efficiency", "coq")}
alert_state = q("SELECT * FROM uc4_alert_state")
D["uc4_alerts_raised"] = len(alert_state)
D["uc4_alerts_by_metric"] = Counter(a["metric_key"] for a in alert_state)
D["uc4_alerts_by_user"] = Counter(a["user_email"].lower() for a in alert_state)
D["uc4_alert_days"] = sorted({a["alert_date"] for a in alert_state})

# UC2 SLA
uc2 = [e for e in ev if e["uc_id"] == "UC2"]
D["uc2_checks"] = len(uc2)
D["uc2_with_issues"] = sum(1 for e in uc2 if (e["sla_breaches"] or 0) + (e["sla_warnings"] or 0) > 0)
tick = set()
for e in uc2:
    for col in ("sla_breach_tickets", "sla_warning_tickets"):
        try:
            for t in json.loads(e[col] or "[]"):
                tick.add(t if isinstance(t, str) else (t.get("key") if isinstance(t, dict) else str(t)))
        except Exception:
            pass
D["uc2_distinct_tickets_flagged"] = len(tick)
D["uc2_open_tickets_max_per_user"] = {}
for e in uc2:
    u = e["user_email"].lower()
    D["uc2_open_tickets_max_per_user"][u] = max(D["uc2_open_tickets_max_per_user"].get(u, 0), e["open_tickets"] or 0)
D["uc2_open_tickets_tracked"] = sum(D["uc2_open_tickets_max_per_user"].values())

# UC1 briefings
uc1 = [e for e in ev if e["uc_id"] == "UC1"]
D["uc1_briefings"] = len(uc1)
D["uc1_rag"] = Counter(e["fta_rag"] for e in uc1 if e["fta_rag"])

# ── runs (13 Oct →) ──
runs = q("SELECT * FROM trigger_runs WHERE is_test = 0 ORDER BY started_at")
D["runs"] = [{k: r[k] for k in ("started_at", "finished_at", "slot_date_ist", "slot_ist", "delay_min", "ucs_selected", "users", "trigger_source", "errors")} for r in runs]

# ── emails (table 13 Oct →; log for all days) ──
em = q("SELECT * FROM email_deliveries WHERE is_test = 0")
D["emails_table_total"] = len(em)
D["emails_table_ok"] = sum(e["sent_ok"] for e in em)
D["emails_table_by_uc"] = Counter(e["uc_id"] for e in em)
D["emails_table_recipients"] = sum(e["recipient_count"] or 0 for e in em)
cc = Counter()
for e in em:
    for c in json.loads(e["cc_emails"] or "[]"):
        cc[c.lower()] += 1
D["emails_cc_people"] = sorted(cc)

log = (ROOT / "MultiAgent_Briefing/output/task_scheduler.log").read_text(encoding="utf-8", errors="replace").splitlines()
sent = [l for l in log if "Email sent via Outlook" in l]
D["log_emails_by_day"] = Counter(l[:10] for l in sent if re.match(r"2026-\d\d-\d\d", l))
rx = re.compile(r"Email sent via Outlook -> (\S+)")
D["log_email_recipients_by_day"] = {d: len({rx.search(l).group(1).lower() for l in sent if l.startswith(d) and rx.search(l)}) for d in D["log_emails_by_day"]}
D["log_runs_complete_by_day"] = Counter(l[:10] for l in log if "fire_all_now complete" in l and re.match(r"2026-\d\d-\d\d", l))
D["log_fire_by_uc"] = Counter(m.group(1) for l in log for m in [re.search(r"FIRE (UC\d) for", l)] if m and l >= "2026-10-09")

# ── profiles (skills share mirror) ──
sk = ROOT / "AI Architecture/skills/Personal Skills"
D["profiles"] = sorted(p.name.replace("_skill.md", "").lower() for p in sk.glob("*_skill.md"))
pt_total, pid_total = set(), set()
for p in sk.glob("*_skill.md"):
    t = p.read_text(encoding="utf-8", errors="replace")
    for key, bag in (("Databricks Process Types", pt_total), ("Databricks Planning IDs", pid_total)):
        m = re.search(rf"\*\*{key}:\*\*\s*(.+)", t)
        if m:
            bag.update(v.strip().lower() for v in m.group(1).split(",") if v.strip() and v.strip().lower() not in ("none", "-", "n/a"))
D["process_types_monitored"] = len(pt_total)
D["planning_ids_monitored"] = len(pid_total)

json.dump(D, open(OUT / "ba_data.json", "w", encoding="utf-8"), indent=1, default=lambda o: dict(o) if isinstance(o, Counter) else str(o))
for k, v in D.items():
    s = json.dumps(v, default=lambda o: dict(o) if isinstance(o, Counter) else str(o))
    print(f"{k}: {s[:300]}")
