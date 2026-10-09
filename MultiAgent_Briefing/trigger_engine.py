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
import audit_log


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
    skill = {}
    try:
        skill = load_skill(skill_file)
        result = run_uc1(skill_file=skill_file)
        audit_log.log_uc1(user, skill, result["analytics"], result["jira"], status="sent")
        log.info(f"✓ UC1  Done -> {result['path']}  [{user}]")
    except Exception as exc:
        audit_log.log_error("UC1", user, skill, str(exc))
        raise


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
    from email_html import build_sla_alert
    deliver(content, skill, subject=f"UC2 — Jira SLA Alert ({proj_name})",
            html_body=build_sla_alert(jira, skill=skill),
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

    # The weekly report always shows Yield, even when it isn't one of the
    # user's alert metrics (UC4 keeps using the profile's own selection).
    pm = list(skill.get("primary_metrics") or [])
    if "yield" not in pm:
        skill = {**skill, "primary_metrics": pm + ["yield"]}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            f_jira = pool.submit(jira_agent.run,                         skill)
            f_ana  = pool.submit(analytics_agent.run, skill, "weekly")
            f_conf = pool.submit(run_confluence,                         skill)
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

        # Build Word attachment
        attachment_path = None
        try:
            import tempfile
            from word_report_weekly import build as build_word
            docx_bytes = build_word(jira, ana, conf, skill=skill)
            suffix     = f"{today}_UC3_Weekly_{user}.docx"
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=f"_{suffix}")
            os.close(tmp_fd)
            with open(tmp_path, "wb") as f:
                f.write(docx_bytes)
            attachment_path = tmp_path
            log.info(f"Word report written -> {tmp_path} ({len(docx_bytes):,} bytes)")
        except Exception as exc:
            log.warning(f"Word report generation failed — sending without attachment: {exc}")

        subject = f"UC3 — Weekly Report: {proj_name} (week {week})"
        deliver(content, skill, subject=subject, html_body=html,
                cc_recipients=cc_list or None, attachment_path=attachment_path)

        audit_log.log_uc3(user, skill, ana, jira, status="sent")

        # Clean up temp file after Outlook has sent it
        if attachment_path:
            try:
                os.remove(attachment_path)
            except Exception:
                pass

        log.info(f"✓ UC3  Saved -> {out_path}  [{user}]")

    except Exception as exc:
        audit_log.log_error("UC3", user, skill, str(exc))
        raise


def _run_uc4(skill: dict, user: str):
    """
    Quality Early Warning — direction-aware per-metric alerts driven entirely
    by the user's onboarding thresholds (metric_thresholds from skill profile).

    Alert logic per metric:
      direction='drop'  → alert when current < alert_value  (FTA, Efficiency)
      direction='rise'  → alert when current > alert_value  (CoQ, CopQ)

    One alert per metric per user per day (suppressed on repeat polls).
    Set FORCE_UC4_ALERT=1 to bypass suppression and thresholds (testing only).
    """
    import os
    from agents import analytics_agent
    from agents.uc4_state import already_alerted_today, mark_alerted
    from delivery import deliver
    from email_html import build_alert

    force        = bool(os.getenv("FORCE_UC4_ALERT"))
    pm           = set(skill.get("primary_metrics") or ["fta", "efficiency", "coq"])
    met_thr      = skill.get("metric_thresholds") or {}
    proj_name    = skill.get("project_name") or "Project"
    jira_project = skill.get("jira_project") or ""
    cc_list      = skill.get("cc_recipients") or []

    log.info(f"UC4  Quality poll [{user}]  metrics={sorted(pm)}")

    try:
        analytics = analytics_agent.run(skill, report_type="daily")
    except Exception as exc:
        audit_log.log_error("UC4", user, skill, str(exc))
        raise

    week  = analytics.get("week_label", "")
    bd    = analytics.get("process_breakdown", [])
    trend = analytics.get("fta_trend", "stable")

    # Map canonical metric key → (current_value, email_metric_id, email headline)
    _METRIC_VALUES = {
        "fta":        (analytics.get("fta_current",    0.0), "fta", "FTA — First Time Accuracy"),
        "efficiency": (analytics.get("efficiency_vs_bl"),    "fta", "Efficiency vs Baseline"),
        "coq":        (analytics.get("coq_current",    0.0), "coq", "CoQ — Cost of Quality"),
        "copq":       (analytics.get("copq_pct"),            "coq", "CoPQ — Cost of Poor Quality"),
        "yield":      (analytics.get("yield_current"),       "fta", "Yield"),
    }

    alerts_sent = 0

    for metric_key in sorted(pm):          # deterministic order
        if metric_key not in _METRIC_VALUES:
            continue

        current, email_type, label = _METRIC_VALUES[metric_key]
        if current is None:
            log.info(f"  UC4  {metric_key} — no data, skipping")
            continue

        thr       = met_thr.get(metric_key, {})
        alert_val = thr.get("alert")
        target    = thr.get("target")
        direction = thr.get("direction", "drop")

        if alert_val is None:
            log.info(f"  UC4  {metric_key} — no alert threshold configured, skipping")
            continue

        # Evaluate breach: direction-aware from onboarding
        if direction == "rise":
            breached = current > alert_val
            watch    = target is not None and current > target
            log.info(f"  UC4  {metric_key} {current:.2f} (alert>'{alert_val}', direction=rise)"
                     f"  breached={breached}")
        else:                              # "drop"
            breached = current < alert_val
            watch    = target is not None and current < target
            log.info(f"  UC4  {metric_key} {current:.2f} (alert<'{alert_val}', direction=drop)"
                     f"  breached={breached}")

        if force or breached:
            rag = "RED"
            if force or not already_alerted_today(user, metric_key):
                html = build_alert(
                    metric=email_type, rag=rag,
                    current_value=current,
                    threshold=alert_val,
                    direction=trend if metric_key == "fta" else (
                        "declining" if direction == "rise" else "stable"
                    ),
                    week_label=week,
                    process_breakdown=bd,
                    skill=skill,
                    label=label,
                    alert_on=direction,
                    operator_breakdown=(analytics.get("operator_breakdown")
                                        if skill.get("include_operator_breakdown") else None),
                )
                subj    = f"UC4 Alert {rag} — {metric_key.upper()} {current:.2f}% vs threshold {alert_val}% — {proj_name}"
                content = f"UC4 {metric_key.upper()} Alert {rag}: {current:.2f}% (threshold {alert_val}%)"
                out     = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_UC4_{user}_{metric_key.upper()}_Alert.md"
                out.write_text(content, encoding="utf-8")
                deliver(content, skill, subject=subj, html_body=html, cc_recipients=cc_list or None)
                if not force:
                    mark_alerted(user, metric_key)
                audit_log.log_uc4(
                    user, skill, analytics,
                    metric_key=metric_key, alert_value=current,
                    threshold_value=alert_val, direction=direction,
                    status="sent",
                )
                alerts_sent += 1
                log.warning(f"UC4  {metric_key.upper()} {current:.2f}% {rag} — alert sent  [{user}]")
            else:
                audit_log.log_uc4(
                    user, skill, analytics,
                    metric_key=metric_key, alert_value=current,
                    threshold_value=alert_val, direction=direction,
                    status="suppressed",
                )
                log.info(f"  UC4  {metric_key.upper()} {current:.2f}% — suppressed (already alerted today)")
        elif watch:
            audit_log.log_uc4(
                user, skill, analytics,
                metric_key=metric_key, alert_value=current,
                threshold_value=alert_val, direction=direction,
                status="healthy",
            )
            log.info(f"  UC4  {metric_key.upper()} {current:.2f}% — AMBER watch (in UC1 briefing)")
        else:
            audit_log.log_uc4(
                user, skill, analytics,
                metric_key=metric_key, alert_value=current,
                threshold_value=alert_val, direction=direction,
                status="healthy",
            )
            log.info(f"  UC4  {metric_key.upper()} {current:.2f}% — healthy")

    if alerts_sent == 0 and not force:
        log.info(f"UC4  All metrics healthy — no alerts  [{user}]")


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
    parser.add_argument("--test-uc3", action="store_true",
                        help="Run UC3 weekly report immediately for all users and exit")
    parser.add_argument("--user", default=None,
                        help="Limit --test-uc3 to a specific user email")
    args = parser.parse_args()

    if args.test_uc3:
        skill_files = [f for f in sorted(SKILLS_DIR.glob("*_skill.md")) if "@" in f.name]
        if not skill_files:
            log.error(f"No skill files found in {SKILLS_DIR}")
        else:
            for skill_file in skill_files:
                try:
                    skill = load_skill(skill_file)
                except Exception as exc:
                    log.error(f"Failed to load {skill_file.name}: {exc}")
                    continue
                user = skill.get("user", "")
                if args.user and args.user.lower() not in user.lower():
                    continue
                log.info(f"=== TEST UC3 — firing now for {user} ===")
                try:
                    _run_uc3(skill, skill_file, user)
                except Exception as exc:
                    log.error(f"UC3 test failed for {user}: {exc}", exc_info=True)
    else:
        start(dry_run=args.dry_run)
