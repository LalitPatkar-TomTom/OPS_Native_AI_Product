"""Short report email after every Azure run, so a run can be checked without PIM or Log Analytics.

Called by entrypoint.sh after the analytics DB is saved:
    python run_report.py <run log> <exit code> <db saved: 1/0>
Sends to RUN_REPORT_TO (nothing is sent when it is empty). It is an operations mail: it is not
recorded in email_deliveries, so it never counts in the business analytics.
"""
import html
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/app/MultiAgent_Briefing")


def main() -> None:
    log_path, rc, db_saved = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3] == "1"
    to = os.getenv("RUN_REPORT_TO", "").strip()
    if not to:
        return
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines() if log_path.exists() else []
    plain = [l for l in lines if "SQL" not in l and "HTTP Request" not in l]

    def first(pattern):
        return next((m for l in plain if (m := re.search(pattern, l))), None)

    slot = first(r"Serving slot (\S+ \S+) IST")
    ucs = first(r"UCs to fire this slot: (\[.*?\])")
    users = first(r"Users found: (\d+)")
    done = any("fire_all_now complete." in l for l in plain)
    fired = Counter(m.group(1) for l in plain if (m := re.search(r"FIRE (UC\d)", l)))
    sent = sum("Email sent via Graph" in l for l in plain)
    failed_mail = [l for l in plain if re.search(r"Graph email failed|Outlook email failed|Graph mail not configured", l)]
    held = sum("suppressed" in l for l in plain)
    per_owner = Counter(m.group(1) for l in plain if (m := re.search(r"PARALLEL RUN: email for (\S+)", l)))
    mcp_ready = first(r"Atlassian MCP ready: (\d+) tools")
    mcp_fallback = [l for l in plain if re.search(r"via MCP failed|Atlassian MCP unavailable", l)]
    problems = [l for l in plain if re.search(r"\[(WARNING|ERROR|CRITICAL) *\]|Traceback", l)
                and not re.search(r"UC4 .*(RED|AMBER).*alert sent", l)]

    # what the analytics DB recorded for this run (the DB copy the run used)
    db_rows = None
    db = Path(os.getenv("OPS_OUTPUT_DIR", "/work/output")) / "trigger_audit.db"
    if db.exists():
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            run_id = con.execute("SELECT run_id FROM trigger_runs ORDER BY started_at DESC LIMIT 1").fetchone()
            if run_id:
                q = lambda sql: con.execute(sql, (run_id[0],)).fetchone()[0]
                db_rows = {"emails": q("SELECT COUNT(*) FROM email_deliveries WHERE run_id=? AND sent_ok=1"),
                           "events": q("SELECT COUNT(*) FROM trigger_events WHERE run_id=?")}
            con.close()
        except Exception as exc:
            problems.append(f"analytics DB not readable for the report: {exc}")

    mcp = (f"OK — {mcp_ready.group(1)} tools" if mcp_ready and not mcp_fallback
           else "FALLBACK to REST" if mcp_fallback else "not used this slot")
    ok = rc == 0 and done and db_saved and not failed_mail and not mcp_fallback and \
        (db_rows is None or db_rows["emails"] == sent)
    when = slot.group(1) if slot else datetime.now().strftime("%Y-%m-%d %H:%M")
    mode = "parallel" if os.getenv("EMAIL_PARALLEL_TO", "").strip() else "live"
    subject = (f"[OPS Native AI run {'OK' if ok else 'PROBLEM'}] {when} IST · {sent} email(s) · "
               f"MCP {'ok' if mcp.startswith('OK') else mcp.lower()} · {mode}")

    rows = [
        ("Result", "OK" if ok else "PROBLEM — see below"),
        ("Slot", f"{when} IST ({mode} mode)"),
        ("Use cases", ucs.group(1) if ucs else "-"),
        ("Users processed", f"{users.group(1) if users else '?'}; fired " + (", ".join(f"{k} × {v}" for k, v in sorted(fired.items())) or "none")),
        ("Emails sent (Graph)", str(sent) + (f" — failed: {len(failed_mail)}" if failed_mail else "")),
        ("Held back", f"{held} (quiet hours / already alerted today)"),
        ("Jira / Confluence via MCP", mcp),
        ("Analytics DB", ("saved to the share" if db_saved else "NOT saved") +
         (f"; recorded {db_rows['emails']} email(s), {db_rows['events']} event(s) for this run" if db_rows else "")),
        ("Run finished", "yes" if done else "NO — the run stopped early") ,
        ("Exit code", str(rc)),
    ]
    color = "#1e7e34" if ok else "#b02a37"
    body = [f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:13px">',
            f'<p style="font-size:15px;color:{color};margin:0 0 8px"><b>{html.escape(rows[0][1])}</b></p>',
            '<table cellpadding="5" style="border-collapse:collapse">']
    for k, v in rows[1:]:
        body.append(f'<tr><td style="border-bottom:1px solid #ddd;color:#555">{html.escape(k)}</td>'
                    f'<td style="border-bottom:1px solid #ddd">{html.escape(v)}</td></tr>')
    body.append("</table>")
    if per_owner:
        body.append("<p><b>Emails per profile owner</b> (parallel mode: all delivered to you only)</p><p>" +
                    "<br>".join(f"{html.escape(o)}: {n}" for o, n in sorted(per_owner.items())) + "</p>")
    if problems or mcp_fallback or failed_mail:
        body.append("<p><b>Warnings and errors</b></p><pre style='font-size:11px;white-space:pre-wrap'>" +
                    html.escape("\n".join(dict.fromkeys(l.strip()[:300] for l in (failed_mail + mcp_fallback + problems)))[:6000]) +
                    "</pre>")
    body.append('<p style="color:#888;font-size:11px">Sent by the Azure job ops-native-ai-trigger after each run. '
                "Operations mail only — not counted in the analytics.</p></div>")

    from delivery import _send_graph
    if not _send_graph(to, subject, "".join(body)):
        print("run report: Graph send failed")
    else:
        print(f"run report sent to {to}: {subject}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:          # the report must never fail the run
        print(f"run report failed: {type(exc).__name__}: {exc}")
