"""
HTML email formatter for UC3 Weekly Operational Report.
Different structure from daily (UC1): trend-first, week-over-week comparison.
Outlook-safe: table-based layout, inline CSS only.
"""
from datetime import datetime, timezone
from typing import Any

from email_html import (
    _rag, _badge, _dot, _arrow, _kv_table, _data_table, _section,
    _alert_row, _build_sprint, _build_confluence, _preview_banner,
    _eff_str, _GREEN, _GREEN_BG, _GREEN_BD,
    _AMBER, _AMBER_BG, _AMBER_BD,
    _RED, _RED_BG, _RED_BD,
    _HDR, _SEC, _WHITE, _STRIPE, _TEXT, _MUTED, _BORDER, _F,
)


# ── Section builders ───────────────────────────────────────────────────────────

def _build_kpi_summary(analytics: dict, jira: dict, pm: set) -> str:
    """3 KPI boxes: current value + delta vs prior week."""
    cells = []

    def delta_str(curr: float, prev: float, higher_is_good: bool = True) -> str:
        d = curr - prev
        good = (d > 0) == higher_is_good
        sign = "+" if d >= 0 else ""
        col  = _GREEN if good else _RED
        return f'<span style="color:{col};font-size:11px;font-weight:bold">{sign}{d:.2f}%</span>'

    if "fta" in pm:
        fta  = analytics.get("fta_current", 0.0)
        prev = analytics.get("fta_prev_week", fta)
        rag  = analytics.get("fta_rag", "GREEN")
        c, bg, bd = _rag(rag)
        cells.append((
            "FTA — First Time Accuracy",
            f'<span style="{_F};font-size:26px;font-weight:bold;color:{c}">{fta:.2f}%</span>',
            delta_str(fta, prev, higher_is_good=True),
            f'vs {prev:.2f}% prior week', bg, bd
        ))

    if "coq" in pm or "copq" in pm:
        coq  = analytics.get("coq_current", 0.0)
        m4w  = analytics.get("metrics_4w", [])
        prev = m4w[1]["coq"] if len(m4w) > 1 else coq
        rag  = analytics.get("coq_rag", "GREEN")
        c, bg, bd = _rag(rag)
        cells.append((
            "CoQ — Cost of Quality",
            f'<span style="{_F};font-size:26px;font-weight:bold;color:{c}">{coq:.2f}%</span>',
            delta_str(coq, prev, higher_is_good=False),
            f'vs {prev:.2f}% prior week', bg, bd
        ))

    if "efficiency" in pm:
        ev  = analytics.get("efficiency_vs_bl")
        rag = analytics.get("efficiency_rag", "GREEN")
        c, bg, bd = _rag(rag)
        m4w = analytics.get("metrics_4w", [])
        prev_eff = m4w[1].get("efficiency_vs_bl") if len(m4w) > 1 else None
        ev_str = _eff_str(ev)
        if ev is not None and prev_eff is not None:
            d    = ev - prev_eff
            sign = "+" if d >= 0 else ""
            col  = _GREEN if d >= 0 else _RED
            delta = f'<span style="color:{col};font-size:11px;font-weight:bold">{sign}{d:.1f}pp vs prior week</span>'
        else:
            delta = ""
        cells.append((
            "Efficiency vs Baseline",
            f'<span style="{_F};font-size:26px;font-weight:bold;color:{c}">{ev_str}</span>',
            delta,
            "", bg, bd
        ))

    if not cells:
        return ""

    col_w = 100 // len(cells)
    tds = ""
    for i, (label, big, delta, sub, bg, bd) in enumerate(cells):
        pad = "padding-left:8px" if i else ""
        tds += (
            f'<td width="{col_w}%" style="{pad}">'
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="background:{bg};border:1px solid {bd};border-radius:4px">'
            f'<tr><td style="padding:14px 16px">'
            f'<div style="{_F};font-size:11px;color:{_MUTED};font-weight:bold;'
            f'text-transform:uppercase;letter-spacing:0.4px;margin-bottom:6px">{label}</div>'
            f'{big}'
            f'<div style="margin-top:6px">{delta}'
            f'{"<br>" if delta and sub else ""}'
            f'<span style="{_F};font-size:11px;color:{_MUTED}">{sub}</span>'
            f'</div>'
            f'</td></tr></table></td>'
        )
    return (
        f'<table width="100%" cellpadding="0" cellspacing="8" style="margin-bottom:18px">'
        f'<tr>{tds}</tr></table>'
    )


def _build_trend_table(analytics: dict, pm: set) -> str:
    """4-week trend table — FTA, CoQ, Efficiency per week (oldest → newest)."""
    m4w = list(reversed(analytics.get("metrics_4w", [])))  # oldest first
    if not m4w:
        return f'<p style="{_F};font-size:13px;color:{_MUTED}">No 4-week trend data available.</p>'

    headers = ["Week"]
    if "fta" in pm:
        headers.append("FTA")
    if "coq" in pm or "copq" in pm:
        headers.append("CoQ")
    if "efficiency" in pm:
        headers.append("Efficiency vs BL")

    rows = []
    for i, w in enumerate(m4w):
        is_latest = (i == len(m4w) - 1)
        week_cell = (
            f'<b style="{_F};font-size:12px">{w["week"]}</b>'
            f' <span style="background:{_HDR};color:#fff;font-size:10px;'
            f'padding:1px 5px;border-radius:2px;{_F}">Latest</span>'
            if is_latest else
            f'<span style="{_F};font-size:12px">{w["week"]}</span>'
        )
        row = [week_cell]

        if "fta" in pm:
            fta = w.get("fta", 0.0)
            fta_rag = "GREEN" if fta >= 95 else "AMBER" if fta >= 92 else "RED"
            c, bg, bd = _rag(fta_rag)
            # Arrow vs prior week
            if i > 0:
                prev_fta = m4w[i - 1].get("fta", fta)
                d = fta - prev_fta
                arr = ("&#8593;" if d > 0.5 else "&#8595;" if d < -0.5 else "&#8594;")
                col = _GREEN if d > 0 else _RED if d < 0 else _MUTED
                arrow_html = f'<span style="color:{col}"> {arr}</span>'
            else:
                arrow_html = ""
            row.append(
                f'<span style="background:{bg};color:{c};border:1px solid {bd};'
                f'padding:2px 6px;border-radius:3px;font-weight:bold;font-size:12px;{_F}">'
                f'{fta:.2f}%</span>{arrow_html}'
            )

        if "coq" in pm or "copq" in pm:
            coq = w.get("coq", 0.0)
            coq_rag = "GREEN" if coq < 7 else "AMBER" if coq < 10 else "RED"
            c, bg, bd = _rag(coq_rag)
            if i > 0:
                prev_coq = m4w[i - 1].get("coq", coq)
                d = coq - prev_coq
                # For CoQ, lower is better — up arrow is bad
                arr = ("&#8593;" if d > 0.2 else "&#8595;" if d < -0.2 else "&#8594;")
                col = _RED if d > 0 else _GREEN if d < 0 else _MUTED
                arrow_html = f'<span style="color:{col}"> {arr}</span>'
            else:
                arrow_html = ""
            row.append(
                f'<span style="background:{bg};color:{c};border:1px solid {bd};'
                f'padding:2px 6px;border-radius:3px;font-weight:bold;font-size:12px;{_F}">'
                f'{coq:.2f}%</span>{arrow_html}'
            )

        if "efficiency" in pm:
            ev = w.get("efficiency_vs_bl")
            if ev is None:
                row.append(f'<span style="{_F};font-size:12px;color:{_MUTED}">N/A</span>')
            else:
                eff_rag = "GREEN" if ev >= 100 else "AMBER" if ev >= 90 else "RED"
                c, _, _ = _rag(eff_rag)
                row.append(f'<span style="{_F};font-size:12px;color:{c};font-weight:bold">{ev:.1f}%</span>')

        rows.append(row)

    src = analytics.get("source", "Databricks")
    return (
        _data_table(headers, rows)
        + f'<p style="{_F};font-size:11px;color:{_MUTED};margin:8px 0 0">Source: {src}</p>'
    )


def _build_process_highlights(analytics: dict) -> str:
    """Top performers + process types needing attention."""
    bd  = analytics.get("process_breakdown", [])
    wk  = analytics.get("week_label", "")
    if not bd:
        return f'<p style="{_F};font-size:13px;color:{_MUTED}">No process data available.</p>'

    needs_attention = [p for p in bd if p.get("fta_rag") in ("AMBER", "RED")]
    top = [p for p in bd if p.get("fta_rag") == "GREEN" and (p.get("eff_vs_bl") or 0) >= 100][:5]

    html = ""

    if needs_attention:
        rows = []
        for p in needs_attention:
            c, bg, bd_col = _rag(p["fta_rag"])
            rows.append([
                f'<span style="{_F};font-size:12px;font-family:Consolas,monospace">{p["process_type"]}</span>',
                f'<span style="background:{bg};color:{c};border:1px solid {bd_col};'
                f'padding:2px 6px;border-radius:3px;font-weight:bold;font-size:12px;{_F}">{p["fta_pct"]:.2f}%</span>',
                f'<span style="{_F};font-size:12px">{p["coq_pct"]:.1f}%</span>',
                f'<span style="{_F};font-size:12px">{p["total_hrs"]:.0f}h</span>',
            ])
        html += (
            f'<div style="{_F};font-size:12px;font-weight:bold;color:{_RED};margin-bottom:6px">'
            f'&#9888; Needs Attention</div>'
            + _data_table(["Process Type", "FTA", "CoQ", "Hrs"], rows)
            + '<div style="margin-top:12px"></div>'
        )

    if top:
        rows = []
        for p in top:
            rows.append([
                f'<span style="{_F};font-size:12px;font-family:Consolas,monospace">{p["process_type"]}</span>',
                f'<span style="{_F};font-size:12px;color:{_GREEN};font-weight:bold">{p["fta_pct"]:.2f}%</span>',
                f'<span style="{_F};font-size:12px">{_eff_str(p.get("eff_vs_bl"))}</span>',
                f'<span style="{_F};font-size:12px">{p["total_hrs"]:.0f}h</span>',
            ])
        html += (
            f'<div style="{_F};font-size:12px;font-weight:bold;color:{_GREEN};margin-bottom:6px">'
            f'&#10003; Top Performers</div>'
            + _data_table(["Process Type", "FTA", "Eff vs BL", "Hrs"], rows)
        )

    if not needs_attention and not top:
        html = f'<p style="{_F};font-size:13px;color:{_MUTED}">All process types within normal range.</p>'

    return html + f'<p style="{_F};font-size:11px;color:{_MUTED};margin:8px 0 0">Week: {wk}</p>'


def _build_focus_next_week(analytics: dict, jira: dict, pm: set) -> str:
    """Auto-generate next-week focus items from alert conditions."""
    items = []
    fta  = analytics.get("fta_current", 0.0)
    coq  = analytics.get("coq_current", 0.0)
    erg  = analytics.get("efficiency_rag", "GREEN")
    bd   = analytics.get("process_breakdown", [])
    br   = jira.get("sla_breaches", [])
    wa   = jira.get("sla_warnings", [])

    if "fta" in pm and fta < 95:
        rag = "RED" if fta < 92 else "AMBER"
        items.append((rag, f"FTA at {fta:.2f}% — monitor process types below target and review rejection patterns early in the week."))

    if ("coq" in pm or "copq" in pm) and coq >= 7:
        rag = "RED" if coq >= 10 else "AMBER"
        items.append((rag, f"CoQ at {coq:.2f}% — identify top rework drivers. Target <7% for next week."))

    if "efficiency" in pm and erg == "RED":
        items.append(("RED", "Efficiency below 90% of baseline — review capacity and task distribution."))

    for p in bd:
        if p.get("fta_rag") in ("AMBER", "RED"):
            items.append((p["fta_rag"],
                f'<b>{p["process_type"]}</b> — FTA {p["fta_pct"]:.2f}%: review rejection root cause.'))

    for t in br:
        items.append(("RED", f'Resolve SLA breach on <b>{t["key"]}</b> — stale {t["hours_stale"]}h.'))

    for t in wa:
        items.append(("AMBER", f'Follow up on <b>{t["key"]}</b> approaching 48h SLA.'))

    if not items:
        return _alert_row("GREEN", "ON TRACK",
                          "All metrics healthy — maintain current execution standards.", "")

    return "\n".join(_alert_row(rag, rag.replace("_", " "), text) for rag, text in items)


# ── Entry point ────────────────────────────────────────────────────────────────

def build(
    jira: dict[str, Any],
    analytics: dict[str, Any],
    confluence: dict[str, Any] | None = None,
    skill: dict[str, Any] | None = None,
    preview_note: str | None = None,
) -> str:
    confluence   = confluence or {}
    _s           = skill or {}
    project_name = _s.get("project_name") or "Project"
    jira_project = _s.get("jira_project") or ""
    user_name    = _s.get("user_first_name") or "you"
    proj_label   = f"{project_name} ({jira_project})" if jira_project else project_name
    pm           = set(_s.get("primary_metrics") or ["fta", "efficiency", "coq"])
    show_eff     = bool(pm & {"efficiency", "coq", "copq"})

    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%H:%M UTC")
    week     = analytics.get("week_label", "")

    overall = "GREEN"
    if jira.get("sla_breaches") or analytics.get("fta_rag") == "RED":
        overall = "RED"
    elif jira.get("sla_warnings") or analytics.get("fta_rag") == "AMBER" or analytics.get("coq_rag") in ("AMBER_P2", "RED_P1"):
        overall = "AMBER"
    oc, _, _ = _rag(overall)

    # Auto-number sections
    n = [0]
    def sec(title, body):
        if not body or not body.strip():
            return ""
        n[0] += 1
        return _section(title, body, n[0])

    return f"""<html>
<body style="margin:0;padding:0;background:#DDE3EA">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#DDE3EA">
<tr><td align="center" style="padding:20px 10px">
<table width="660" cellpadding="0" cellspacing="0"
       style="background:{_WHITE};border-radius:6px;border:1px solid {_BORDER}">
<tr><td>

  <!-- Header -->
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td style="background:{_HDR};padding:20px 22px 14px">
      <span style="{_F};font-size:18px;font-weight:bold;color:#fff">Weekly Operational Report</span><br>
      <span style="{_F};font-size:12px;color:#8FA3C0;display:block;margin-top:3px">
        {proj_label} &nbsp;·&nbsp; Week of {week} &nbsp;·&nbsp; {date_str} &nbsp;·&nbsp; {time_str}
      </span>
    </td>
    <td style="background:{_HDR};padding:20px 22px;text-align:right;white-space:nowrap;vertical-align:middle">
      <span style="{_F};font-size:11px;color:#8FA3C0">Overall</span><br>
      <span style="{_F};font-size:15px;font-weight:bold;color:{oc}">&#9679; {overall}</span>
    </td>
  </tr>
  </table>

  <!-- Body -->
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="padding:18px 20px">

    {"<div>" + _preview_banner(preview_note) + "</div>" if preview_note else ""}

    {_build_kpi_summary(analytics, jira, pm)}

    {sec(f"4-Week Trend — {project_name}",
         _build_trend_table(analytics, pm))}

    {sec("Process Type Highlights",
         _build_process_highlights(analytics))}

    {sec(f"{jira_project} Sprint Health" if jira_project else "Sprint Health",
         _build_sprint(jira, jira_project))}

    {sec("Confluence — Weekly Progress",
         _build_confluence(confluence))}

    {sec(f"Focus for Next Week — {user_name}'s Review",
         _build_focus_next_week(analytics, jira, pm))}

  </td></tr>
  </table>

  <!-- Footer -->
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="background:{_SEC};border-top:1px solid {_BORDER};
                 padding:10px 20px;border-radius:0 0 6px 6px">
    <span style="{_F};font-size:11px;color:{_MUTED}">
      UC3 Weekly Report &nbsp;·&nbsp; Jira {jira_project} · Databricks · Confluence
      &nbsp;&nbsp;—&nbsp;&nbsp;
      <b>Draft for {user_name}'s review before any distribution.</b>
    </span>
  </td></tr>
  </table>

</td></tr>
</table>
</td></tr>
</table>
</body></html>"""
