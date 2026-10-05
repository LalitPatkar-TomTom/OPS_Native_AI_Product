"""
fire_all_now.py — Non-interactive batch trigger for Windows Task Scheduler.

Fires all active UCs for every user whose skill file exists in Personal Skills/.
Smart UC selection based on time-of-day:

  09:00  → UC1 (morning briefing) + UC2 + UC4
  13:00  → UC2 + UC4
  17:00  → UC2 + UC4 + UC3 (if Friday)
  21:00  → UC2 + UC4

Run manually to test:
    python fire_all_now.py
    python fire_all_now.py --dry-run
"""
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

import pytz

sys.path.insert(0, str(Path(__file__).parent))

from config import SKILLS_DIR, OUTPUT_DIR
from skill_registry import load_skill

log_file = OUTPUT_DIR / "fire_all_now.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file), encoding="utf-8"),
    ],
)
log = logging.getLogger("fire_all_now")

IST = pytz.timezone("Asia/Kolkata")


def _which_ucs(hour_ist: int, weekday: int) -> list[str]:
    """Return list of UC IDs to fire based on IST hour and weekday (0=Mon, 4=Fri)."""
    ucs = []
    if hour_ist < 11:           # 09:00 slot — morning briefing
        ucs.append("UC1")
    ucs.append("UC2")           # Jira SLA check every slot
    ucs.append("UC4")           # Quality alert every slot (has built-in dedup)
    if weekday == 4 and hour_ist >= 16:   # Friday afternoon — weekly report
        ucs.append("UC3")
    return ucs


def fire_for_user(skill_file: Path, ucs: list[str], dry_run: bool):
    try:
        skill = load_skill(skill_file)
    except Exception as exc:
        log.error(f"  Could not load skill {skill_file.name}: {exc}")
        return

    user = skill.get("user", skill_file.stem)
    active_uc_ids = {uc["uc_id"] for uc in skill.get("use_cases", []) if uc.get("active")}

    log.info(f"\n  User: {user}  |  Active UCs: {sorted(active_uc_ids)}")

    for uc_id in ucs:
        if uc_id not in active_uc_ids:
            log.info(f"    SKIP {uc_id} — not active in skill profile")
            continue

        if dry_run:
            log.info(f"    DRY-RUN  {uc_id} would fire for {user}")
            continue

        log.info(f"    FIRE {uc_id} for {user}")
        try:
            _dispatch(uc_id, skill, skill_file, user)
        except Exception as exc:
            log.error(f"    ERROR {uc_id} [{user}]: {exc}", exc_info=True)


def _dispatch(uc_id: str, skill: dict, skill_file: Path, user: str):
    if uc_id == "UC1":
        from orchestrator import run_uc1
        out = run_uc1(skill_file=skill_file)
        log.info(f"    OK  UC1 -> {out}")

    elif uc_id == "UC2":
        from agents import jira_agent
        from delivery import deliver
        from email_html import build_alert
        jira = jira_agent.run(skill)
        breaches = jira.get("sla_breaches", [])
        warnings = jira.get("sla_warnings", [])
        if not breaches and not warnings:
            log.info(f"    OK  UC2 — no SLA issues")
            return
        lines = [f"# UC2 Jira SLA Alert\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        for t in breaches:
            lines.append(f"- BREACH [{t['key']}] {t['summary']} | {t['assignee']} | {t['hours_stale']}h")
        for t in warnings:
            lines.append(f"- WARNING [{t['key']}] {t['summary']} | {t['assignee']} | {t['hours_stale']}h")
        content = "\n".join(lines)
        out_path = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_UC2_{user}_SLA.md"
        out_path.write_text(content, encoding="utf-8")
        deliver(content, skill, subject=f"UC2 — Jira SLA Alert ({skill.get('project_name','')})"),
        log.info(f"    OK  UC2 — alert sent -> {out_path}")

    elif uc_id == "UC3":
        import concurrent.futures
        from agents import jira_agent, analytics_agent
        from agents.confluence_agent import run as run_confluence
        from email_html_weekly import build as build_weekly
        from delivery import deliver
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            f_j = pool.submit(jira_agent.run, skill)
            f_a = pool.submit(analytics_agent.run, skill)
            f_c = pool.submit(run_confluence, skill)
            jira, ana, conf = f_j.result(), f_a.result(), f_c.result()
        html = build_weekly(jira, ana, conf, skill=skill)
        week = ana.get("week_label", datetime.now().strftime("%Y-%m-%d"))
        content = f"UC3 Weekly Report: {skill.get('project_name','')} | Week {week}"
        out_path = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_UC3_Weekly_{user}.md"
        out_path.write_text(content, encoding="utf-8")
        deliver(content, skill, subject=f"UC3 — Weekly Report (week {week})", html_body=html)
        log.info(f"    OK  UC3 -> {out_path}")

    elif uc_id == "UC4":
        from agents import analytics_agent
        from agents.uc4_state import already_alerted_today, mark_alerted
        from email_html import build_alert
        from delivery import deliver
        analytics = analytics_agent.run(skill)
        fta   = analytics.get("fta_current", 0.0)
        coq   = analytics.get("coq_current", 0.0)
        week  = analytics.get("week_label", "")
        trend = analytics.get("fta_trend", "stable")
        bd    = analytics.get("process_breakdown", [])
        fta_thr = skill.get("fta_thresholds", {"target": 95.0, "alert": 92.0})
        coq_thr = skill.get("coq_thresholds", {"target": 7.0,  "alert": 10.0})

        if fta < fta_thr["alert"] and not already_alerted_today(user, "fta"):
            html = build_alert(metric="fta", rag="RED", current_value=fta,
                               threshold=fta_thr["alert"], direction=trend,
                               week_label=week, process_breakdown=bd, skill=skill)
            content = f"UC4 FTA Alert RED: {fta:.2f}%"
            deliver(content, skill, subject=f"UC4 FTA Alert: {fta:.2f}% — {skill.get('project_name','')}", html_body=html)
            mark_alerted(user, "fta")
            log.warning(f"    ALERT  UC4 FTA {fta:.2f}% RED — sent")
        elif coq >= coq_thr["alert"] and not already_alerted_today(user, "coq"):
            html = build_alert(metric="coq", rag="RED", current_value=coq,
                               threshold=coq_thr["alert"], direction="declining",
                               week_label=week, process_breakdown=bd, skill=skill)
            content = f"UC4 CoQ Alert RED: {coq:.2f}%"
            deliver(content, skill, subject=f"UC4 CoQ Alert: {coq:.2f}% — {skill.get('project_name','')}", html_body=html)
            mark_alerted(user, "coq")
            log.warning(f"    ALERT  UC4 CoQ {coq:.2f}% RED — sent")
        else:
            log.info(f"    OK  UC4 — FTA {fta:.2f}%  CoQ {coq:.2f}%  (healthy or already alerted)")


def main():
    parser = argparse.ArgumentParser(description="OPS Native AI — batch trigger all users")
    parser.add_argument("--dry-run", action="store_true", help="Print what would run without executing")
    parser.add_argument("--uc", default=None, choices=["UC1","UC2","UC3","UC4"],
                        help="Force a specific UC regardless of time (e.g. --uc UC1)")
    args = parser.parse_args()

    now_ist  = datetime.now(IST)
    hour_ist = now_ist.hour
    weekday  = now_ist.weekday()
    ucs      = [args.uc] if args.uc else _which_ucs(hour_ist, weekday)

    log.info("=" * 60)
    log.info(f"fire_all_now starting — {now_ist.strftime('%Y-%m-%d %H:%M %Z')}")
    log.info(f"UCs to fire this slot: {ucs}  {'(DRY RUN)' if args.dry_run else ''}")
    log.info("=" * 60)

    skill_files = sorted([f for f in SKILLS_DIR.glob("*_skill.md") if "@" in f.name])
    if not skill_files:
        log.error(f"No skill files found in {SKILLS_DIR}")
        sys.exit(1)

    log.info(f"Users found: {len(skill_files)}")
    for sf in skill_files:
        fire_for_user(sf, ucs, dry_run=args.dry_run)

    log.info("\n" + "=" * 60)
    log.info("fire_all_now complete.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
