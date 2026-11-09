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

from skill_registry import load_all_skills, load_skill, split_rules  # noqa: F401  (split_rules used in UC4)
from email_html import project_name_of
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
        sent = (result.get("delivery") or {}).get("email", True)
        audit_log.log_uc1(user, skill, result["analytics"], result["jira"],
                          status="sent" if sent else "send_failed")
        log.info(f"✓ UC1  Done -> {result['path']}  [{user}]")
    except Exception as exc:
        audit_log.log_error("UC1", user, skill, str(exc))
        raise


def _run_uc2(skill: dict, user: str):
    """UC2: Jira SLA follow-up for one profile — email the open tickets past the profile's levels."""
    from agents import jira_agent
    from delivery import deliver

    from skill_registry import jira_label

    proj_name    = project_name_of(skill)
    user_first   = skill.get("user_first_name") or "you"
    cc_list      = skill.get("cc_recipients") or []

    log.info(f"▶ UC2  Jira SLA poll starting … [{user}]")
    try:
        jira = jira_agent.run(skill)
    except Exception as exc:
        audit_log.log_error("UC2", user, skill, str(exc))
        raise

    if jira.get("error"):
        # The Jira query itself failed (bad project key, invalid JQL, auth): not "no issues"
        audit_log.log_error("UC2", user, skill, f"Jira query failed: {jira['error']}"[:500])
        log.error(f"UC2  Jira query failed — SLA not checked  [{user}]: {str(jira['error'])[:200]}")
        return
    if jira.get("key_warning"):
        # OSI-061: one of several keys is wrong; the others were checked, so the run goes on
        log.warning(f"UC2  {jira['key_warning']}  [{user}]")

    jira_project = jira_label(skill, jira)          # every key checked, e.g. "OM, MCPET" (OSI-061)
    proj_label   = f"{proj_name} / {jira_project}" if jira_project else proj_name
    breaches = jira.get("sla_breaches", [])
    warnings = jira.get("sla_warnings", [])
    unassigned = jira.get("unassigned", [])

    # The "Not assigned" list (OSI-056) rides along with an SLA alert; on its own it sends no email, so a
    # healthy profile gets no new daily mail.
    if not breaches and not warnings:
        audit_log.log_uc2(user, skill, jira, status="healthy")
        log.info(f"✓ UC2  No SLA issues detected  [{user}]")
        return

    sla_lines = [
        f"# UC2 — Jira SLA Alert ({proj_label})",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    if breaches:
        sla_lines.append(f"## 🔴 SLA BREACH — {len(breaches)} ticket(s) over {jira.get('sla_escalation_hours', 72):g}h without update\n")
        for t in breaches:
            sla_lines.append(
                f"- [{t['key']}]({t['url']}) — {t['summary']}  "
                f"| Owner: **{t['assignee']}** | Silent: **{t['hours_stale']}h**"
            )
        sla_lines.append(f"\n> Draft follow-up ready for {user_first}'s approval.")
    if warnings:
        sla_lines.append(f"\n## 🟡 SLA WARNING — {len(warnings)} ticket(s) over {jira.get('sla_warning_hours', 48):g}h without update\n")
        for t in warnings:
            sla_lines.append(
                f"- [{t['key']}]({t['url']}) — {t['summary']}  "
                f"| Owner: **{t['assignee']}** | Silent: **{t['hours_stale']}h**"
            )
    if unassigned:
        from email_html import UNASSIGNED_MAX
        sla_lines.append(f"\n## Not assigned — {len(unassigned)} open ticket(s) with no owner\n")
        for t in unassigned[:UNASSIGNED_MAX]:
            sla_lines.append(f"- [{t['key']}]({t['url']}) — {t['summary']}  | Status: {t['status']}"
                             + (f" | Open: **{t['age_days']} days**" if t.get("age_days") is not None else ""))
    if jira.get("key_warning"):
        sla_lines.append(f"\n> {jira['key_warning']}")

    content    = "\n".join(sla_lines)
    date_stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_path   = OUTPUT_DIR / f"{date_stamp}_UC2_{user}_SLA_Alert.md"
    out_path.write_text(content, encoding="utf-8")
    from email_html import build_sla_alert
    res = deliver(content, skill, subject=f"UC2 — Jira SLA Alert ({proj_name})",
                  html_body=build_sla_alert(jira, skill=skill),
                  cc_recipients=cc_list or None)
    audit_log.log_uc2(user, skill, jira, status="sent" if res.get("email") else "send_failed")
    log.info(f"✓ UC2  SLA alert saved -> {out_path}  [{user}]")


def _run_uc3(skill: dict, skill_file: Path, user: str):
    """Weekly Report — full analytics + Jira, formatted as a weekly HTML email."""
    import concurrent.futures
    import os
    from agents import jira_agent, analytics_agent
    from agents.confluence_agent import run as run_confluence
    from delivery import deliver

    proj_name    = project_name_of(skill)
    jira_project = skill.get("jira_project") or ""
    cc_list      = skill.get("cc_recipients") or []

    if audit_log.sent_today("UC3", user):
        audit_log.log_skipped("UC3", user, skill, reason="weekly report already sent today")
        log.info(f"  UC3 [{user}] already sent today — skipped")
        return

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

        import ask_why
        ask_why.snapshot(ana, skill, "UC3")            # "Ask why" links (ADR-015)
        from email_html_weekly import build as build_weekly
        _preview_note = None
        if os.getenv("PREVIEW_MODE"):
            _preview_note = (
                "This is a preview of your weekly operational report. Once live, "
                "you will receive this every Friday at 16:00. If you have feedback, "
                "please reach out to the OPS Native AI team."
            )
        images: dict[str, bytes] = {}      # 8-week charts per process type (OSI-010), inline in the email
        html = build_weekly(jira, ana, conf, skill=skill, preview_note=_preview_note, images=images)
        log.info(f"  UC3 {len(images)} trend chart(s)  [{user}]")

        week = ana.get("week_label") or datetime.now().strftime("%Y-%m-%d")
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

        from email_html import period_label
        subject = (f"UC3 — Weekly Report: {proj_name} — "
                   + (period_label(ana["week_label"]) if ana.get("week_label") else f"week {week}"))
        # inline_images only when there are charts: a run without charts calls deliver() exactly as before
        res = deliver(content, skill, subject=subject, html_body=html,
                      cc_recipients=cc_list or None, attachment_path=attachment_path,
                      **({"inline_images": images} if images else {}))

        audit_log.log_uc3(user, skill, ana, jira,
                          status="sent" if res.get("email") else "send_failed")

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
    Every metric that fires in one run goes out in ONE email, worst first (OSI-043, 6 Nov 2026);
    UC4_COMBINED_ALERT=0 goes back to one email per metric.
    Set FORCE_UC4_ALERT=1 to bypass suppression and thresholds (testing only).
    """
    import os
    from agents import analytics_agent
    from agents.uc4_state import already_alerted_today
    from email_html import alert_week_note, period_label

    force        = bool(os.getenv("FORCE_UC4_ALERT"))
    pm           = set(skill.get("primary_metrics") or ["fta", "efficiency", "coq"])
    met_thr      = skill.get("metric_thresholds") or {}
    proj_name    = project_name_of(skill)
    jira_project = skill.get("jira_project") or ""
    cc_list      = skill.get("cc_recipients") or []

    log.info(f"UC4  Quality poll [{user}]  metrics={sorted(pm)}")
    if skill.get("no_databricks_scope"):
        # no process types / planning IDs: the values would be company-wide, so no alert is evaluated
        audit_log.log_skipped("UC4", user, skill, reason="no process types or planning IDs in the profile")
        log.info(f"UC4  skipped — no process types or planning IDs in the profile  [{user}]")
        return

    try:
        analytics = analytics_agent.run(skill, report_type="alert")
    except Exception as exc:
        audit_log.log_error("UC4", user, skill, str(exc))
        raise

    # No live Databricks data: the fallback values are placeholders, so evaluating them could
    # send a false alert. Skip and record the reason instead.
    if not analytics.get("live", True):
        audit_log.log_error("UC4", user, skill, f"metrics unavailable: {analytics.get('error', '')}"[:300])
        log.warning(f"UC4  metrics unavailable — no alert evaluated  [{user}]: {analytics.get('error', '')}")
        return

    week  = analytics.get("week_label", "")
    bd    = analytics.get("process_breakdown", [])
    wk_note = alert_week_note(analytics).replace("&apos;", "'")   # subjects are plain text
    trend = analytics.get("fta_trend", "stable")

    # Map canonical metric key → (current_value, email_metric_id, email headline)
    _METRIC_VALUES = {
        "fta":        (analytics.get("fta_current",    0.0), "fta", "FTA — First Time Accuracy"),
        "efficiency": (analytics.get("efficiency_vs_bl"),    "fta", "Efficiency vs Baseline"),
        "coq":        (analytics.get("coq_current",    0.0), "coq", "CoQ — Cost of Quality"),
        "copq":       (analytics.get("copq_pct"),            "coq", "CoPQ — Cost of Poor Quality"),
        "yield":      (analytics.get("yield_current"),       "fta", "Yield"),
    }

    pending: list[dict] = []   # alerts of this run, sent together after the loop (OSI-043)

    for metric_key in sorted(pm):          # deterministic order
        if metric_key not in _METRIC_VALUES:
            continue

        current, email_type, label = _METRIC_VALUES[metric_key]
        overall_rules, scoped_rules = split_rules(skill, metric_key)

        # OSI-030: alert levels set for named process types / planning IDs, checked on each of them
        hits = scoped_breaches(analytics, scoped_rules, metric_key)
        if hits:
            skey = f"{metric_key}:scoped"
            rise = hits[0][0]["direction"] == "rise"
            worst = max(hits, key=lambda h: h[2]) if rise else min(hits, key=lambda h: h[2])
            what = "planning ID" if worst[0]["level"] == "planning" else "process type"
            names = [str(h[1].get("planning_id") or h[1].get("process_type")) for h in hits]
            if force or not already_alerted_today(user, skey):
                rows = [{**h[1], "process_type": n} for h, n in zip(hits, names)]
                alert_kw = dict(
                    metric=email_type, rag="RED", current_value=worst[2], threshold=worst[0]["alert"],
                    direction="declining" if rise else "stable", week_label=week, process_breakdown=rows,
                    skill=skill, label=f"{label} — {len(hits)} {what}{'s' if len(hits) > 1 else ''} past "
                                       f"the level set for {'them' if len(hits) > 1 else 'it'}",
                    alert_on=worst[0]["direction"], analytics=analytics, metric_key=metric_key,
                    trend_rows=rows,
                )
                subj = (f"UC4 Alert RED — {metric_key.upper()} {worst[2]:.2f}% vs threshold {worst[0]['alert']}% — "
                        f"{', '.join(names[:2])}{' …' if len(names) > 2 else ''} — {proj_name}"
                        + (f" — {period_label(week, fallback_note=wk_note)}" if week else ""))
                content = f"UC4 {metric_key.upper()} scoped alert: " + "; ".join(
                    f"{n} {h[2]:.2f}% (level {h[0]['alert']}%)" for h, n in zip(hits, names))
                pending.append({
                    "state_key": skey, "metric_key": metric_key, "label": alert_kw["label"],
                    "short": f"{metric_key.upper()} {worst[2]:.2f}% ({', '.join(names[:2])}{' …' if len(names) > 2 else ''})",
                    "value": worst[2], "level": worst[0]["alert"], "direction": worst[0]["direction"],
                    "alert_kw": alert_kw, "subject": subj, "content": content,
                    "file": f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_UC4_{user}_{metric_key.upper()}_scoped_Alert.md",
                    "log": f"UC4  {metric_key.upper()} scoped — {len(hits)} {what}(s) past their level — alert sent  [{user}]",
                })
            else:
                log.info(f"  UC4  {metric_key.upper()} scoped — suppressed (already alerted today)")
        if scoped_rules and not overall_rules:
            log.info(f"  UC4  {metric_key} — alert levels are set per {scoped_rules[0]['level']} only; no overall check")
            continue

        if current is None:
            why = analytics.get("yield_note") if metric_key == "yield" else ""
            log.info(f"  UC4  {metric_key} — no data, skipping" + (f" ({why})" if why else ""))
            continue

        thr       = ({"alert": overall_rules[0]["alert"], "target": overall_rules[0]["target"],
                      "direction": overall_rules[0]["direction"]} if overall_rules else met_thr.get(metric_key, {}))
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
                alert_kw = dict(
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
                    operator_breakdown=([o for o in analytics.get("operator_breakdown") or []
                                         if metric_key in o.get("breaches", [])
                                         or (metric_key == "copq" and "coq" in o.get("breaches", []))]
                                        if skill.get("operator_view") else None),
                    analytics=analytics, metric_key=metric_key,
                    trend_rows=alerting_rows(analytics, metric_key, alert_val, direction),
                )
                subj    = (f"UC4 Alert {rag} — {metric_key.upper()} {current:.2f}% vs threshold {alert_val}% — {proj_name}"
                           + (f" — {period_label(week, fallback_note=wk_note)}" if week else ""))
                content = f"UC4 {metric_key.upper()} Alert {rag}: {current:.2f}% (threshold {alert_val}%)"
                pending.append({
                    "state_key": metric_key, "metric_key": metric_key, "label": label,
                    "short": f"{metric_key.upper()} {current:.2f}%",
                    "value": current, "level": alert_val, "direction": direction,
                    "alert_kw": alert_kw, "subject": subj, "content": content,
                    "file": f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_UC4_{user}_{metric_key.upper()}_Alert.md",
                    "log": f"UC4  {metric_key.upper()} {current:.2f}% {rag} — alert sent  [{user}]",
                })
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

    tail = f" — {proj_name}" + (f" — {period_label(week, fallback_note=wk_note)}" if week else "")
    if pending:
        import ask_why
        ask_why.snapshot(analytics, skill, "UC4")   # "See why" link per metric (ADR-015)
    alerts_sent = _send_uc4_alerts(pending, skill, user, analytics, force, tail, cc_list)
    if alerts_sent == 0 and not force:
        log.info(f"UC4  All metrics healthy — no alerts  [{user}]")


def _alert_gap(p: dict) -> float:
    """How far an alert is past its level, relative to the level, so FTA 85 vs 92 and CoQ 12 vs 7 compare."""
    return abs(p["value"] - p["level"]) / max(abs(p["level"]), 1.0)


def _send_uc4_alerts(pending: list[dict], skill: dict, user: str, analytics: dict, force: bool,
                     tail: str, cc_list: list) -> int:
    """Send this run's UC4 alerts and record them; returns how many metric alerts went out.

    One alert: exactly the email of before. Several: one combined email, worst first (OSI-043), because users
    asked for one consolidated alert instead of several emails in the same minute. Each metric keeps its own
    once-a-day state and audit row, so suppression and the analytics count work as before; a failed send marks
    nothing, so every metric is retried at the next slot. UC4_COMBINED_ALERT=0 sends one email per metric."""
    import os
    from agents.uc4_state import mark_alerted
    from delivery import deliver
    from email_html import build_alert, build_combined_alert

    if not pending:
        return 0
    combined = len(pending) > 1 and os.getenv("UC4_COMBINED_ALERT", "1").strip().lower() not in ("0", "false", "off")
    groups = [sorted(pending, key=_alert_gap, reverse=True)] if combined else [[p] for p in pending]
    for group in groups:
        images: dict[str, bytes] = {}   # OSI-010 charts of every section; cids stay unique across sections
        if len(group) == 1:
            p = group[0]
            html = build_alert(**p["alert_kw"], images=images)
            subj, content, name = p["subject"], p["content"], p["file"]
        else:
            bodies = [build_alert(**p["alert_kw"], images=images, body_only=True) for p in group]
            html = build_combined_alert(group, bodies, skill)
            subj = (f"UC4 Alert RED — {len(group)} metrics past their level: "
                    + ", ".join(p["short"] for p in group) + tail)
            content = "UC4 combined alert:\n" + "\n".join(p["content"] for p in group)
            name = group[0]["file"].rsplit("_UC4_", 1)[0] + f"_UC4_{user}_Combined_Alert.md"
        (OUTPUT_DIR / name).write_text(content, encoding="utf-8")
        res = deliver(content, skill, subject=subj, html_body=html, cc_recipients=cc_list or None,
                      **({"inline_images": images} if images else {}))
        for p in group:
            if not force and res.get("email"):     # failed send: retry at the next slot
                mark_alerted(user, p["state_key"])
            audit_log.log_uc4(user, skill, analytics, metric_key=p["metric_key"], alert_value=p["value"],
                              threshold_value=p["level"], direction=p["direction"],
                              status="sent" if res.get("email") else "send_failed")
            log.warning(p["log"] + (f" (one email with {len(group) - 1} more)" if len(group) > 1 else ""))
    return len(pending)


_ROW_FIELD = {"fta": "fta_pct", "efficiency": "eff_vs_bl", "coq": "coq_pct", "copq": "coq_pct", "yield": "yield_pct"}


def scoped_breaches(analytics: dict, rules: list[dict], metric_key: str) -> list[tuple[dict, dict, float]]:
    """[(rule, breakdown row, value)] for each named process type / planning ID past its own alert level.

    Names match exactly (case-insensitive); a profile name cut at "|" still matches the full process type.
    Rows too small to judge (fewer than 10 QC'd tasks for FTA, no hours otherwise) are skipped.
    """
    field = _ROW_FIELD[metric_key]
    found = []
    for r in rules:
        rows = (analytics.get("planning_breakdown") if r["level"] == "planning" else analytics.get("process_breakdown")) or []
        key = "planning_id" if r["level"] == "planning" else "process_type"
        names = {n.lower() for n in r["scope"]}
        for row in rows:
            name = str(row.get(key, "")).lower()
            if name not in names and name.split("|")[0] not in names:
                continue
            v = row.get(field)
            if v is None or (metric_key == "fta" and row.get("fta_rag") in ("SMALL", None)) \
                    or (metric_key != "fta" and not (row.get("total_hrs") or 0)):
                continue
            if (v > r["alert"]) if r["direction"] == "rise" else (v < r["alert"]):
                found.append((r, row, float(v)))
    return found


def alerting_rows(analytics: dict, metric_key: str, alert: float, direction: str) -> list[dict]:
    """The process types that are themselves past the overall alert level for this metric (same rules as
    scoped_breaches: names exact, too-small rows skipped). Their 8-week chart goes into the UC4 alert (OSI-010);
    an overall breach that no single process type causes has no chart."""
    names = [str(p.get("process_type", "")) for p in analytics.get("process_breakdown") or []]
    if metric_key not in _ROW_FIELD or not names:
        return []
    rule = {"level": "process", "scope": names, "alert": alert, "direction": direction}
    return [row for _, row, _ in scoped_breaches(analytics, [rule], metric_key)]


def _run_uc5(user: str):
    log.info(f"▶ UC5  Plan vs Actual placeholder  [{user}]")


# ── Job factory ────────────────────────────────────────────────────────────────

def _make_job(uc_id: str, skill: dict, skill_file: Path):
    """Return a zero-argument callable for APScheduler — one closure per user+UC."""
    quiet = skill.get("quiet_hours")
    tz    = skill.get("timezone", "Asia/Kolkata")
    user  = skill.get("user", "unknown")

    def job() -> bool:
        """Run one use case for one user. Returns False when it raised (already logged)."""
        audit_log.set_uc(uc_id)
        is_p0 = uc_id == "UC4"   # FTA P1 can break quiet hours
        if not is_p0 and _in_quiet_hours(quiet, tz):
            audit_log.log_skipped(uc_id, user, skill, reason=f"quiet hours {quiet}")
            log.info(f"  {uc_id} [{user}] suppressed — quiet hours {quiet}")
            return True
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
            return False
        return True

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
