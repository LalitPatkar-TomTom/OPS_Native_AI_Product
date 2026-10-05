"""
Briefing Agent — formats Jira + Analytics data into the UC1 daily briefing.

Follows lalit's style: RAG status first, bullet points, no prose padding,
maximum 3-4 min read time. Every alert names the project and data source.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _rag_emoji(rag: str) -> str:
    mapping = {
        "GREEN": "🟢", "AMBER": "🟡", "AMBER_P3": "🟡",
        "AMBER_P2": "🟠", "RED": "🔴", "RED_P1": "🔴",
        "BREACH_72H": "🔴", "WARNING_48H": "🟡", "OK": "🟢",
    }
    return mapping.get(rag, "⚪")


def _overall_rag(jira: dict, analytics: dict) -> str:
    has_breach  = len(jira.get("sla_breaches", [])) > 0
    has_warning = len(jira.get("sla_warnings", [])) > 0
    fta_rag     = analytics.get("fta_rag", "GREEN")
    eff_rag     = analytics.get("efficiency_rag", "GREEN")

    if has_breach or fta_rag == "RED" or eff_rag == "RED":
        return "RED"
    if has_warning or fta_rag == "AMBER" or eff_rag == "AMBER":
        return "AMBER"
    return "GREEN"


def _trend_arrow(trend: str) -> str:
    return {"improving": "↑", "stable": "→", "declining": "↓"}.get(trend, "→")


def _fta_sparkline(fta_4w: list[dict]) -> str:
    """Build a text sparkline from 4-week FTA history (oldest → newest)."""
    if not fta_4w:
        return ""
    weeks = list(reversed(fta_4w))   # oldest first
    parts = [f"{w['fta']:.2f}% ({w['week']})" for w in weeks]
    return " → ".join(parts)


def _eff_label(eff_vs_bl: float | None) -> str:
    if eff_vs_bl is None:
        return "N/A (no baseline)"
    delta = eff_vs_bl - 100
    sign  = "+" if delta >= 0 else ""
    direction = "above" if delta >= 0 else "below"
    return f"{eff_vs_bl:.1f}% ({sign}{delta:.1f}% {direction} baseline)"


def run(jira: dict[str, Any], analytics: dict[str, Any],
        confluence: dict[str, Any] | None = None,
        skill: dict[str, Any] | None = None) -> str:
    """
    Formats all agent data into a markdown daily briefing string.
    Called by the Orchestrator after both sub-agents complete.
    """
    _skill          = skill or {}
    project_name    = _skill.get("project_name") or "Project"
    jira_project    = _skill.get("jira_project") or ""
    user_first_name = _skill.get("user_first_name") or "you"
    project_label   = f"{project_name} ({jira_project})" if jira_project else project_name

    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%H:%M UTC")

    overall   = _overall_rag(jira, analytics)
    rag_badge = _rag_emoji(overall)

    breaches  = jira.get("sla_breaches", [])
    warnings  = jira.get("sla_warnings", [])
    open_all  = jira.get("open_tickets", [])
    ok_count  = len(open_all) - len(breaches) - len(warnings)

    fta        = analytics.get("fta_current",    0.0)
    fta_prev   = analytics.get("fta_prev_week",  0.0)
    fta_rag    = analytics.get("fta_rag",        "GREEN")
    fta_4w     = analytics.get("fta_4w",         [])
    trend      = analytics.get("fta_trend",      "stable")

    eff_raw    = analytics.get("efficiency_raw",  None)
    eff_vs_bl  = analytics.get("efficiency_vs_bl", None)
    eff_rag    = analytics.get("efficiency_rag",  "GREEN")

    coq        = analytics.get("coq_current",    0.0)
    coq_rag    = analytics.get("coq_rag",        "GREEN")
    copq_hrs   = analytics.get("copq_hrs",       None)
    copq_pct   = analytics.get("copq_pct",       None)
    prod_hrs   = analytics.get("prod_hrs",       None)
    qc_hrs     = analytics.get("qc_hrs",         None)

    breakdown  = analytics.get("process_breakdown", [])
    wk_label   = analytics.get("week_label",     "latest week")
    ana_src    = analytics.get("source",         "Databricks")

    # ── Build briefing ─────────────────────────────────────────────────────────
    lines: list[str] = []

    lines += [
        f"# UC1 — Daily Operational Briefing",
        f"**Project:** {project_label} · **Date:** {date_str} · **Generated:** {time_str}",
        f"**Overall RAG:** {rag_badge} {overall}",
        "",
        "---",
        "",
    ]

    # ── Section 1: Priority Attention ─────────────────────────────────────────
    lines += ["## 1. Priority Attention Today", ""]

    process_amber = [p for p in breakdown if p.get("fta_rag") in ("AMBER", "RED")]
    eff_red_procs = [p for p in breakdown if p.get("eff_vs_bl") is not None and p["eff_vs_bl"] < 90]

    if not breaches and not warnings and fta_rag == "GREEN" and not process_amber and eff_rag == "GREEN":
        lines += ["- No critical items. All metrics on track.", ""]
    else:
        if breaches:
            lines += [
                f"**{_rag_emoji('BREACH_72H')} SLA BREACH — {len(breaches)} ticket(s) exceed 72h without update ({jira_project})**",
                "",
            ]
            for t in breaches:
                days = round(t['hours_stale'] / 24, 1)
                lines.append(
                    f"- [{t['key']}]({t['url']}) — _{t['summary']}_ "
                    f"| Owner: **{t['assignee']}** "
                    f"| Silent for **{days} days ({t['hours_stale']}h)** "
                    f"| Status: {t['status']}"
                )
            lines += [
                "",
                "  > **Action required:** Review and draft a follow-up to owner(s) above for your approval.",
                "",
            ]
        if warnings:
            lines += [
                f"**{_rag_emoji('WARNING_48H')} SLA WARNING — {len(warnings)} ticket(s) approaching 48h ({jira_project})**",
                "",
            ]
            for t in warnings:
                lines.append(
                    f"- [{t['key']}]({t['url']}) — _{t['summary']}_ "
                    f"| Owner: **{t['assignee']}** "
                    f"| Silent for **{t['hours_stale']}h**"
                )
            lines.append("")

        if fta_rag in ("AMBER", "RED"):
            lines += [
                f"**{_rag_emoji(fta_rag)} FTA ALERT — {fta:.2f}% (Target: 95%, Alert: <92%)**",
                f"  Trend: {_trend_arrow(trend)} {trend.capitalize()} vs prev week ({fta_prev:.2f}%)",
                f"  Source: {ana_src}",
                "",
            ]

        if process_amber:
            lines += [f"**{_rag_emoji('AMBER')} Process-level FTA concerns (week {wk_label})**", ""]
            for p in process_amber:
                lines.append(
                    f"- `{p['process_type']}` — FTA {_rag_emoji(p['fta_rag'])} **{p['fta_pct']:.2f}%** "
                    f"| Eff vs BL: {_eff_label(p.get('eff_vs_bl'))} "
                    f"| CoQ: {p['coq_pct']:.1f}%"
                )
            lines.append("")

        if eff_rag == "RED":
            lines += [
                f"**{_rag_emoji('RED')} EFFICIENCY ALERT — {_eff_label(eff_vs_bl)} for week {wk_label}**",
                f"  Raw efficiency: {eff_raw:.4f} tasks/hr" if eff_raw else "",
                "",
            ]

    # ── Section 2: Sprint Health ───────────────────────────────────────────────
    lines += [f"## 2. {jira_project} Sprint Health", ""]
    jira_src = jira.get("source", "Jira MCPET")
    jira_err = jira.get("error")
    if jira_err:
        lines += [f"- ⚠️  Jira data unavailable: {jira_err}", ""]
    else:
        lines += [
            f"- **Open tickets:** {jira.get('total_open', 0)}",
            f"  - {_rag_emoji('BREACH_72H')} SLA Breach (72h+): {len(breaches)}",
            f"  - {_rag_emoji('WARNING_48H')} SLA Warning (48-72h): {len(warnings)}",
            f"  - {_rag_emoji('OK')} On track: {ok_count}",
            f"- Source: _{jira_src}_ · as of {jira.get('as_of', '')[:16]} UTC",
            "",
        ]

    # ── Section 3: Quality (FTA) ───────────────────────────────────────────────
    lines += [f"## 3. Quality — FTA ({project_name})", ""]
    fta_emoji = _rag_emoji(fta_rag)
    sparkline = _fta_sparkline(fta_4w)
    lines += [
        f"- **FTA:** {fta_emoji} **{fta:.2f}%** (Target: 95% | Alert: <92%)",
        f"- **4-week trend:** {sparkline}" if sparkline else f"- **Prev week:** {fta_prev:.2f}%",
        f"- **Trend direction:** {_trend_arrow(trend)} {trend.capitalize()}",
        f"- **Week:** {wk_label} · Source: _{ana_src}_",
        "",
    ]
    if fta_rag == "GREEN":
        lines += ["  > FTA is healthy. No quality escalation needed.", ""]
    elif fta_rag == "AMBER":
        lines += [
            f"  > FTA in amber zone — watch for rework tickets in {jira_project}.",
            "  > Cross-reference with any quality-labelled tickets on the board.",
            "",
        ]
    else:
        lines += [
            "  > **P1 ALERT: FTA below 92% threshold.** Immediate review required.",
            f"  > Cross-reference {jira_project} for quality-labelled tickets and rework spikes.",
            "",
        ]

    # ── Section 4: Efficiency & Cost of Quality ────────────────────────────────
    lines += ["## 4. Efficiency & Cost of Quality", ""]
    eff_emoji = _rag_emoji(eff_rag)
    coq_emoji = _rag_emoji(coq_rag)

    coq_label = (
        "Healthy <5%" if coq < 5 else
        "P3 Monitor 5-7%" if coq < 7 else
        "P2 Investigate 7-10%" if coq < 10 else
        "P1 Escalate >10%"
    )

    lines += [
        f"- **Efficiency:** {eff_emoji} {_eff_label(eff_vs_bl)}"
        + (f"  ·  Raw: {eff_raw:.4f} tasks/hr" if eff_raw else ""),
        f"- **CoQ:** {coq_emoji} **{coq:.2f}%** ({coq_label})",
    ]
    if copq_hrs is not None:
        lines.append(
            f"- **CopQ (rework cost):** {copq_hrs:.1f}h wasted on rejected tasks"
            + (f" · {copq_pct:.2f}% of total hrs" if copq_pct is not None else "")
        )
    if prod_hrs is not None and qc_hrs is not None:
        lines.append(
            f"- **Hours breakdown:** Prod {prod_hrs:.0f}h · QC {qc_hrs:.0f}h"
            + (f" · Total {(prod_hrs + qc_hrs):.0f}h" if prod_hrs and qc_hrs else "")
        )
    lines += [f"- **Week:** {wk_label} · Source: _{ana_src}_", ""]

    # ── Section 5: Process-type breakdown ─────────────────────────────────────
    if breakdown:
        scope_mode  = analytics.get("scope_mode", "defined")
        scope_label = analytics.get("scope_label", "")
        if scope_mode == "all":
            bd_header = f"All Process Types by Volume — Week {wk_label} (top {len(breakdown)} shown)"
        elif scope_mode.startswith("keyword:"):
            kws = scope_mode.replace("keyword:", "").replace(",", " / ").upper()
            bd_header = f"{kws} Process Types by Volume — Week {wk_label} ({len(breakdown)} types)"
        else:
            bd_header = f"Process-type Breakdown — Week {wk_label}"
        lines += [f"## 5. {bd_header}", ""]
        lines += [
            "| Process Type | FTA | Eff vs BL | CoQ | Tasks | Hrs |",
            "|---|---|---|---|---|---|",
        ]
        for p in breakdown:
            fta_cell = f"{_rag_emoji(p['fta_rag'])} {p['fta_pct']:.2f}%"
            evbl     = p.get("eff_vs_bl")
            evbl_rag = (
                "GREEN" if evbl is not None and evbl >= 100 else
                "AMBER" if evbl is not None and evbl >= 90 else
                "RED"   if evbl is not None else "⚪"
            )
            eff_cell = f"{_rag_emoji(evbl_rag)} {evbl:.1f}%" if evbl is not None else "N/A"
            coq_cell = f"{p['coq_pct']:.1f}%"
            lines.append(
                f"| {p['process_type']} "
                f"| {fta_cell} "
                f"| {eff_cell} "
                f"| {coq_cell} "
                f"| {p['prod_tasks']:,} "
                f"| {p['total_hrs']:.0f}h |"
            )
        lines.append("")

    # ── Section 6: All open tickets ────────────────────────────────────────────
    if open_all:
        sec = 6 if breakdown else 5
        lines += [f"## {sec}. All Open {jira_project} Tickets", ""]
        lines += [
            "| Key | Summary | Status | Owner | Stale | SLA |",
            "|-----|---------|--------|-------|-------|-----|",
        ]
        for t in open_all:
            sla_badge = _rag_emoji(t["sla_status"])
            lines.append(
                f"| [{t['key']}]({t['url']}) "
                f"| {t['summary'][:55]} "
                f"| {t['status']} "
                f"| {t['assignee']} "
                f"| {t['hours_stale']}h "
                f"| {sla_badge} {t['sla_status']} |"
            )
        lines.append("")

    # ── Section 7: Confluence Updates ─────────────────────────────────────────
    conf        = confluence or {}
    conf_pages  = conf.get("pages", [])
    conf_err    = conf.get("error")
    sec_base    = (7 if breakdown else 6) if open_all else (6 if breakdown else 5)

    lines += [f"## {sec_base}. Confluence — Weekly Progress Page", ""]
    if conf_err and not conf_pages:
        lines += [f"- ⚠️  Confluence unavailable: {conf_err}", ""]
    elif not conf_pages:
        lines += ["- No Confluence pages configured in skill profile.", ""]
    else:
        for page in conf_pages:
            title   = page.get("page_title", "(untitled)")
            url     = page.get("page_url", "")
            days    = page.get("days_since_update", 999.0)
            updated = page.get("last_updated", "")[:10]
            by_who  = page.get("last_updated_by", "")
            overdue = page.get("update_overdue", False)
            excerpt = page.get("excerpt", "")
            page_err = page.get("error")
            metrics = page.get("metrics", {})

            if page_err:
                lines += [f"- ⚠️  Could not fetch Confluence page: {page_err}", ""]
                continue

            status_icon = "🟡" if overdue else "🟢"
            title_link  = f"[{title}]({url})" if url else title
            lines.append(
                f"- {status_icon} {title_link}"
                + (f" — last updated {updated}" + (f" by {by_who}" if by_who else "")
                   + (f" (**{int(days)} days ago — overdue for update**)" if overdue
                      else f" ({int(days)} days ago)"))
            )
            if metrics:
                metric_parts = []
                if metrics.get("fta_mentioned"):
                    metric_parts.append(f"FTA: {metrics['fta_mentioned']:.1f}%")
                if metrics.get("efficiency_mentioned"):
                    metric_parts.append(f"Eff: {metrics['efficiency_mentioned']:.1f}%")
                if metrics.get("coq_mentioned"):
                    metric_parts.append(f"CoQ: {metrics['coq_mentioned']:.1f}%")
                if metric_parts:
                    lines.append(f"  - Metrics on page: {' | '.join(metric_parts)}")
            if excerpt:
                lines.append(f"  - _{excerpt[:200]}…_")
        lines.append("")

    # ── Section 8: Suggested Actions ──────────────────────────────────────────
    lines += [f"## {sec_base + 1}. Suggested Actions (for {user_first_name}'s review)", ""]
    action_num = 1
    if breaches:
        for t in breaches:
            lines.append(
                f"{action_num}. **Draft follow-up to {t['assignee']}** re [{t['key']}]({t['url']}) "
                f"— stale {t['hours_stale']}h, SLA breached. _(awaiting your approval before send)_"
            )
            action_num += 1
    if warnings:
        for t in warnings:
            lines.append(
                f"{action_num}. **Flag to {t['assignee']}** re [{t['key']}]({t['url']}) "
                f"— {t['hours_stale']}h without update, approaching 48h SLA. _(review recommended)_"
            )
            action_num += 1
    if fta_rag != "GREEN":
        lines.append(
            f"{action_num}. Review FTA data — current {fta:.2f}% ({trend}). "
            f"Cross-check quality-labelled {jira_project} tickets."
        )
        action_num += 1
    for p in process_amber:
        lines.append(
            f"{action_num}. Investigate `{p['process_type']}` — FTA {p['fta_pct']:.2f}% "
            f"(week {wk_label}). Review rejection patterns."
        )
        action_num += 1
    if coq_rag in ("AMBER_P2", "RED_P1"):
        copq_note = f" CopQ: {copq_hrs:.1f}h of rework." if copq_hrs else ""
        lines.append(
            f"{action_num}. CoQ at {coq:.2f}% — review rework patterns for week {wk_label}.{copq_note}"
        )
        action_num += 1
    if eff_rag == "RED" and eff_vs_bl is not None:
        lines.append(
            f"{action_num}. Efficiency at {eff_vs_bl:.1f}% vs baseline — identify bottlenecks "
            f"in low-performing process types."
        )
        action_num += 1
    if action_num == 1:
        lines.append("- No immediate actions required. Day is on track.")
    lines.append("")

    # Footer
    lines += [
        "---",
        "_Briefing generated by UC1 — Daily Operational Briefing Agent_  ",
        f"_Data sources: Jira ({jira_project}) · Databricks (manual_efficiency_quality_all_weekly_tbl) · Confluence_  ",
        f"_All draft communications shown above require {user_first_name}'s explicit approval before sending._",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    mock_jira = {
        "open_tickets": [
            {"key": "MCPET-999", "summary": "Test ticket", "status": "In Progress",
             "priority": "High", "assignee": "Test User", "updated": "2026-08-25T10:00:00+00:00",
             "hours_stale": 200.0, "sla_status": "BREACH_72H", "labels": [],
             "url": "https://tomtom.atlassian.net/browse/MCPET-999"},
        ],
        "sla_breaches": [],
        "sla_warnings": [],
        "total_open": 1,
        "source": "Jira MCPET (mock)",
        "as_of": "2026-09-03T08:30:00+00:00",
        "error": None,
    }
    mock_analytics = {
        "fta_current": 98.63, "fta_prev_week": 98.68, "fta_trend": "stable",
        "fta_rag": "GREEN",
        "fta_4w": [
            {"week": "2026-08-31", "fta": 98.63},
            {"week": "2026-08-24", "fta": 98.68},
            {"week": "2026-08-17", "fta": 98.35},
            {"week": "2026-08-10", "fta": 98.30},
        ],
        "efficiency_raw": 9.2251, "efficiency_vs_bl": 102.8, "efficiency_rag": "GREEN",
        "coq_current": 9.85, "coq_rag": "AMBER_P2",
        "copq_hrs": 10.54, "copq_pct": 0.13,
        "prod_hrs": 7039.83, "qc_hrs": 768.97,
        "process_breakdown": [
            {"process_type": "orbis-update-vehiclerestrictions", "fta_pct": 92.3,
             "fta_rag": "AMBER", "efficiency": 2.8239, "eff_vs_bl": 100.5,
             "coq_pct": 16.38, "copq_hrs": 0.0, "prod_tasks": 2089, "total_hrs": 739.8},
            {"process_type": "attr-update-restrictions", "fta_pct": 100.0,
             "fta_rag": "GREEN", "efficiency": 5.9027, "eff_vs_bl": 112.9,
             "coq_pct": 2.0, "copq_hrs": 0.0, "prod_tasks": 3972, "total_hrs": 672.9},
        ],
        "week_label": "2026-08-31", "source": "Databricks (mock)",
        "as_of": "2026-09-03T08:30:00+00:00", "live": True, "error": None,
    }
    print(run(mock_jira, mock_analytics))
