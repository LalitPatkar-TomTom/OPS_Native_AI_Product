"""
Trigger Engine — scans AI Architecture/skills/Personal Skills/ for all user skill
files and fires UC orchestrators on schedule for each user.

Run once and leave it running:
    python trigger_engine.py

What it does:
  - Loads every *_skill.md from the Personal Skills directory
  - Registers cron/poll jobs for every Active use case per user
  - At the scheduled time, calls the right orchestrator function for that user
  - Respects each user's quiet hours and timezone
  - Logs every trigger event to console + trigger_engine.log

Adding a new user: drop their combined *_skill.md into
  AI Architecture/skills/Personal Skills/
and restart the engine — it picks them up automatically.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

sys.path.insert(0, str(Path(__file__).parent))

from skill_registry import load_all_skills, load_skill
from config import SKILLS_DIR, OUTPUT_DIR


# ── Logging setup ──────────────────────────────────────────────────────────────

log_file = OUTPUT_DIR / "trigger_engine.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file), encoding="utf-8"),
    ],
)
log = logging.getLogger("trigger_engine")


# ── Quiet hours guard ──────────────────────────────────────────────────────────

def _in_quiet_hours(quiet: tuple[int, int] | None, timezone: str) -> bool:
    if quiet is None:
        return False
    try:
        tz  = pytz.timezone(timezone)
        now = datetime.now(tz)
        h   = now.hour
        start, end = quiet
        if start > end:
            return h >= start or h < end
        return start <= h < end
    except Exception:
        return False


# ── UC orchestrator dispatch ───────────────────────────────────────────────────

def _run_uc1(skill_file: Path, user: str):
    from orchestrator import run_uc1
    log.info(f"▶ UC1  Daily Briefing starting … [{user}]")
    out = run_uc1(skill_file=skill_file)
    log.info(f"✓ UC1  Done -> {out}  [{user}]")


def _run_uc2(skill: dict, user: str):
    from agents import jira_agent
    from delivery import deliver

    proj_name    = skill.get("project_name") or "Project"
    jira_project = skill.get("jira_project") or ""
    proj_label   = f"{proj_name} / {jira_project}" if jira_project else proj_name
    user_first   = skill.get("user_first_name") or "you"
    cc_list      = skill.get("cc_recipients") or []

    log.info(f"▶ UC2  Jira SLA poll starting … [{user}]")
    jira = jira_agent.run(skill)

    breaches = jira.get("sla_breaches", [])
    warnings = jira.get("sla_warnings", [])

    if not breaches and not warnings:
        log.info(f"✓ UC2  No SLA issues detected  [{user}]")
        return

    sla_lines = [
        f"# UC2 — Jira SLA Alert ({proj_label})",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    if breaches:
        sla_lines.append(f"## 🔴 SLA BREACH — {len(breaches)} ticket(s) over 72h\n")
        for t in breaches:
            sla_lines.append(
                f"- [{t['key']}]({t['url']}) — {t['summary']}  "
                f"| Owner: **{t['assignee']}** | Silent: **{t['hours_stale']}h**"
            )
        sla_lines.append(f"\n> Draft follow-up ready for {user_first}'s approval.")
    if warnings:
        sla_lines.append(f"\n## 🟡 SLA WARNING — {len(warnings)} ticket(s) approaching 48h\n")
        for t in warnings:
            sla_lines.append(
                f"- [{t['key']}]({t['url']}) — {t['summary']}  "
                f"| Owner: **{t['assignee']}** | Silent: **{t['hours_stale']}h**"
            )

    content    = "\n".join(sla_lines)
    date_stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_path   = OUTPUT_DIR / f"{date_stamp}_UC2_{user}_SLA_Alert.md"
    out_path.write_text(content, encoding="utf-8")
    deliver(content, skill, subject=f"UC2 — Jira SLA Alert ({proj_name})",
            cc_recipients=cc_list or None)
    log.info(f"✓ UC2  SLA alert saved -> {out_path}  [{user}]")


def _run_uc3(skill: dict, skill_file: Path, user: str):
    """Weekly Report — full analytics + Jira, formatted as a weekly HTML email."""
    import concurrent.futures
    import os
    from agents import jira_agent, analytics_agent
    from agents.confluence_agent import run as run_confluence
    from delivery import deliver

    proj_name    = skill.get("project_name") or "Project"
    jira_project = skill.get("jira_project") or ""
    cc_list      = skill.get("cc_recipients") or []

    log.info(f"▶ UC3  Weekly Report starting … [{user}]")

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        f_jira = pool.submit(jira_agent.run,      skill)
        f_ana  = pool.submit(analytics_agent.run, skill)
        f_conf = pool.submit(run_confluence,       skill)
        jira   = f_jira.result()
        ana    = f_ana.result()
        conf   = f_conf.result()

    from email_html_weekly import build as build_weekly
    _preview_note = None
    if os.getenv("PREVIEW_MODE"):
        _preview_note = (
            "This is a preview of your weekly operational report. Once live, "
            "you will receive this every Friday at 16:00. If you have feedback, "
            "please reply to Lalit Patkar."
        )
    html = build_weekly(jira, ana, conf, skill=skill, preview_note=_preview_note)

    week = ana.get("week_label", datetime.now().strftime("%Y-%m-%d"))
    content = (
        f"UC3 — Weekly Report: {proj_name}\n"
        f"Week: {week}  |  FTA: {ana.get('fta_current', 0):.2f}%"
        f"  |  CoQ: {ana.get('coq_current', 0):.2f}%\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    today    = datetime.now().strftime("%Y-%m-%d")
    out_path = OUTPUT_DIR / f"{today}_UC3_Weekly_{user}.md"
    out_path.write_text(content, encoding="utf-8")

    subject = f"UC3 — Weekly Report: {proj_name} (week {week})"
    deliver(content, skill, subject=subject, html_body=html, cc_recipients=cc_list or None)
    log.info(f"✓ UC3  Saved -> {out_path}  [{user}]")


def _run_uc4(skill: dict, user: str):
    """
    Quality Early Warning — checks FTA and CoQ, fires per-metric HTML alerts.
    One alert per metric per user per day (suppressed on repeat polls).
    Respects primary_metrics: skips metrics the user hasn't opted into.
    Set FORCE_UC4_ALERT=1 to bypass suppression and thresholds (testing only).
    """
    import os
    from agents import analytics_agent
    from agents.uc4_state import already_alerted_today, mark_alerted
    from delivery import deliver
    from email_html import build_alert

    force = bool(os.getenv("FORCE_UC4_ALERT"))
    pm    = set(skill.get("primary_metrics") or ["fta", "efficiency", "coq"])

    proj_name    = skill.get("project_name") or "Project"
    jira_project = skill.get("jira_project") or ""
    cc_list      = skill.get("cc_recipients") or []

    fta_thr = skill.get("fta_thresholds", {"target": 95.0, "alert": 92.0})
    coq_thr = skill.get("coq_thresholds", {"target": 7.0,  "alert": 10.0})

    log.info(f"▶ UC4  Quality poll … [{user}]")
    analytics = analytics_agent.run(skill)

    fta   = analytics.get("fta_current",   0.0)
    coq   = analytics.get("coq_current",   0.0)
    trend = analytics.get("fta_trend",     "stable")
    week  = analytics.get("week_label",    "")
    bd    = analytics.get("process_breakdown", [])

    alerts_sent = 0

    # ── FTA check ──────────────────────────────────────────────────────────────
    if "fta" in pm:
        fta_alert_thr = fta_thr["alert"]
        fta_target    = fta_thr["target"]
        if force or fta < fta_alert_thr:
            rag = "RED" if (force or fta < fta_alert_thr) else "AMBER"
            if force or not already_alerted_today(user, "fta"):
                html = build_alert(
                    metric="fta", rag=rag,
                    current_value=fta,
                    threshold=fta_alert_thr,
                    direction=trend, week_label=week,
                    process_breakdown=bd, skill=skill,
                )
                subj = f"UC4 ⚠️ FTA Alert {rag}: {fta:.2f}% — {proj_name}"
                content = f"UC4 FTA Alert {rag}: {fta:.2f}% (threshold {fta_alert_thr}%)"
                out  = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_UC4_{user}_FTA_Alert.md"
                out.write_text(content, encoding="utf-8")
                deliver(content, skill, subject=subj, html_body=html, cc_recipients=cc_list or None)
                if not force:
                    mark_alerted(user, "fta")
                alerts_sent += 1
                log.warning(f"✗ UC4  FTA {fta:.2f}% {rag} — alert sent  [{user}]")
            else:
                log.info(f"  UC4  FTA {fta:.2f}% RED — suppressed (already alerted today)  [{user}]")
        elif fta < fta_target:
            log.info(f"  UC4  FTA {fta:.2f}% — AMBER watch item (in UC1 morning briefing)  [{user}]")
        else:
            log.info(f"  UC4  FTA {fta:.2f}% — healthy  [{user}]")

    # ── CoQ check ──────────────────────────────────────────────────────────────
    if "coq" in pm or "copq" in pm:
        coq_alert_thr = coq_thr["alert"]
        if force or coq >= coq_alert_thr:
            rag = "RED" if (force or coq >= coq_alert_thr) else "AMBER"
            if force or not already_alerted_today(user, "coq"):
                html = build_alert(
                    metric="coq", rag=rag,
                    current_value=coq,
                    threshold=coq_alert_thr,
                    direction="declining",   # CoQ going up = quality declining
                    week_label=week,
                    process_breakdown=bd, skill=skill,
                )
                subj = f"UC4 ⚠️ CoQ Alert {rag}: {coq:.2f}% — {proj_name}"
                content = f"UC4 CoQ Alert {rag}: {coq:.2f}% (threshold {coq_alert_thr}%)"
                out  = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_UC4_{user}_CoQ_Alert.md"
                out.write_text(content, encoding="utf-8")
                deliver(content, skill, subject=subj, html_body=html, cc_recipients=cc_list or None)
                if not force:
                    mark_alerted(user, "coq")
                alerts_sent += 1
                log.warning(f"✗ UC4  CoQ {coq:.2f}% {rag} — alert sent  [{user}]")
            else:
                log.info(f"  UC4  CoQ {coq:.2f}% RED — suppressed (already alerted today)  [{user}]")
        else:
            log.info(f"  UC4  CoQ {coq:.2f}% — healthy  [{user}]")

    if alerts_sent == 0 and not force:
        log.info(f"✓ UC4  All metrics healthy — no alerts  [{user}]")


def _run_uc5(user: str):
    log.info(f"▶ UC5  Plan vs Actual placeholder  [{user}]")


# ── Job factory ────────────────────────────────────────────────────────────────

def _make_job(uc_id: str, skill: dict, skill_file: Path):
    """Return a zero-argument callable for APScheduler — one closure per user+UC."""
    quiet = skill.get("quiet_hours")
    tz    = skill.get("timezone", "Asia/Kolkata")
    user  = skill.get("user", "unknown")

    def job():
        is_p0 = uc_id == "UC4"   # FTA P1 can break quiet hours
        if not is_p0 and _in_quiet_hours(quiet, tz):
            log.info(f"  {uc_id} [{user}] suppressed — quiet hours {quiet}")
            return
        try:
            if   uc_id == "UC1": _run_uc1(skill_file, user)
            elif uc_id == "UC2": _run_uc2(skill, user)
            elif uc_id == "UC3": _run_uc3(skill, skill_file, user)
            elif uc_id == "UC4": _run_uc4(skill, user)
            elif uc_id == "UC5": _run_uc5(user)
            else:
                log.warning(f"  No handler for {uc_id}")
        except Exception as exc:
            log.error(f"  {uc_id} [{user}] raised: {exc}", exc_info=True)

    job.__name__ = f"job_{uc_id}_{user}"
    return job


# ── Engine startup ─────────────────────────────────────────────────────────────

def start(dry_run: bool = False):
    """
    Load all *_skill.md files from Personal Skills/, register jobs for every
    active UC across all users, then start the scheduler.

    dry_run=True -> prints the schedule and exits without blocking.
    """
    # Only load email-named files (personal profiles); skip domain templates
    skill_files = [f for f in sorted(SKILLS_DIR.glob("*_skill.md")) if "@" in f.name]
    if not skill_files:
        log.error(f"No skill files found in {SKILLS_DIR} — nothing to schedule.")
        return

    log.info("=" * 60)
    log.info(f"Trigger Engine starting — {len(skill_files)} user(s) found")
    log.info(f"Skills dir : {SKILLS_DIR}")
    log.info(f"Output     : {OUTPUT_DIR}")
    log.info("=" * 60)

    scheduler        = BlockingScheduler()
    total_registered = 0

    for skill_file in skill_files:
        try:
            skill = load_skill(skill_file)
        except Exception as exc:
            log.error(f"Failed to load {skill_file.name}: {exc}")
            continue

        user = skill["user"]
        tz   = skill["timezone"]
        log.info(f"\n  User : {user}  (TZ: {tz})")

        registered = 0
        for uc in skill["use_cases"]:
            uc_id = uc["uc_id"]
            spec  = uc["trigger_spec"]

            if not uc["active"]:
                log.info(f"    SKIP  {uc_id} ({uc['name']}) — inactive")
                continue
            if spec["type"] == "unknown":
                log.warning(f"    SKIP  {uc_id} — unrecognised trigger: {uc['trigger_str']!r}")
                continue

            job_fn = _make_job(uc_id, skill, skill_file)

            if spec["type"] == "cron":
                dow = spec.get("day_of_week", "*")
                asc_trigger = CronTrigger(
                    hour=spec["hour"], minute=spec["minute"],
                    day_of_week=dow, timezone=tz,
                )
                day_label = f"every {dow}" if dow != "*" else "daily"
                log.info(
                    f"    CRON  {uc_id}  {uc['name']}"
                    f"  -> {spec['hour']:02d}:{spec['minute']:02d} {day_label} ({tz})"
                )
            else:  # poll
                mins = spec["interval_minutes"]
                asc_trigger = IntervalTrigger(minutes=mins, timezone=tz)
                log.info(
                    f"    POLL  {uc_id}  {uc['name']}"
                    f"  -> every {mins} min  source={spec.get('source', '?')}"
                )

            scheduler.add_job(
                job_fn,
                asc_trigger,
                id=f"{uc_id}_{user}",
                name=f"{uc_id} — {uc['name']} [{user}]",
                replace_existing=True,
            )
            registered += 1
            total_registered += 1

        log.info(f"    {registered} job(s) registered for {user}")

    log.info("-" * 60)
    log.info(f"Total jobs registered: {total_registered} across {len(skill_files)} user(s)")

    if dry_run:
        log.info("DRY RUN — scheduler not started.")
        _print_next_fires(scheduler)
        return

    log.info("Scheduler running. Press Ctrl+C to stop.")
    log.info("=" * 60)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Trigger Engine stopped.")


def _print_next_fires(scheduler: BlockingScheduler):
    print("\nNext scheduled fires (UTC):")
    print(f"{'Job':<60} Next fire")
    print("-" * 90)
    utc = pytz.utc
    now = datetime.now(utc)
    for job in scheduler.get_jobs():
        try:
            next_run   = job.trigger.get_next_fire_time(None, now)
            time_str   = next_run.astimezone(utc).strftime("%Y-%m-%d %H:%M UTC") if next_run else "(interval poll)"
        except Exception:
            time_str = "(interval poll)"
        print(f"{job.name:<60} {time_str}")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MultiAgent Briefing — Trigger Engine")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print schedule without running")
    args = parser.parse_args()

    start(dry_run=args.dry_run)
