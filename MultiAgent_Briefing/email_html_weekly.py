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
    _build_exec_summary, _build_breakdown, _build_actions, _build_operator_breakdown,
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

    if "yield" in pm:
        yv   = analytics.get("yield_current")
        rag  = analytics.get("yield_rag", "GREEN")
        c, bg, bd = _rag(rag)
        m4w  = analytics.get("metrics_4w", [])
        prev_yv = m4w[1].get("yield") if len(m4w) > 1 else yv
        yv_str  = f"{yv:.2f}%" if yv is not None else "N/A"
        if yv is not None and prev_yv is not None:
            d    = yv - prev_yv
            sign = "+" if d >= 0 else ""
            col  = _GREEN if d >= 0 else _RED
            delta = f'<span style="color:{col};font-size:11px;font-weight:bold">{sign}{d:.2f}% vs prior week</span>'
            sub  = f'vs {prev_yv:.2f}% prior week'
        else:
            delta = ""
            sub  = ""
        cells.append((
            "Yield — First Pass",
            f'<span style="{_F};font-size:26px;font-weight:bold;color:{c}">{yv_str}</span>',
            delta,
            sub, bg, bd
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
    if "yield" in pm:
        headers.append("Yield")
    headers.append("Sampling")

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

        if "yield" in pm:
            yv = w.get("yield")
            if yv is None:
                row.append(f'<span style="{_F};font-size:12px;color:{_MUTED}">N/A</span>')
            else:
                yield_rag = "GREEN" if yv >= 95 else "AMBER" if yv >= 94 else "RED"
                c, bg, bd = _rag(yield_rag)
                if i > 0:
                    prev_yv = m4w[i - 1].get("yield", yv)
                    d = yv - prev_yv
                    arr = ("&#8593;" if d > 0.2 else "&#8595;" if d < -0.2 else "&#8594;")
                    col = _GREEN if d > 0 else _RED if d < 0 else _MUTED
                    arrow_html = f'<span style="color:{col}"> {arr}</span>'
                else:
                    arrow_html = ""
                row.append(
                    f'<span style="background:{bg};color:{c};border:1px solid {bd};'
                    f'padding:2px 6px;border-radius:3px;font-weight:bold;font-size:12px;{_F}">'
                    f'{yv:.2f}%</span>{arrow_html}'
                )

        sp = w.get("sampling_pct")
        row.append(
            f'<span style="{_F};font-size:12px;color:{_MUTED}">{sp:.1f}%</span>'
            if sp is not None else
            f'<span style="{_F};font-size:12px;color:{_MUTED}">—</span>'
        )

        rows.append(row)

    src = analytics.get("source", "Databricks")
    return (
        _data_table(headers, rows)
        + f'<p style="{_F};font-size:11px;color:{_MUTED};margin:8px 0 0">Source: {src}</p>'
    )


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

    now        = datetime.now(timezone.utc)
    date_str   = now.strftime("%A, %d %B %Y")
    time_str   = now.strftime("%H:%M UTC")
    week       = analytics.get("week_label", "")
    data_label = analytics.get("data_label", f"week of {week}")

    overall = "GREEN"
    if jira.get("sla_breaches") or analytics.get("fta_rag") == "RED":
        overall = "RED"
    elif jira.get("sla_warnings") or analytics.get("fta_rag") == "AMBER" or analytics.get("coq_rag") in ("AMBER_P2", "RED_P1"):
        overall = "AMBER"
    oc, _, _ = _rag(overall)

    # scope_mode: "defined" when the skill has explicit process types, else "all"
    pts = _s.get("databricks_process_types") or []
    scope_mode = _s.get("scope_mode") or ("defined" if pts else "all")

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
        {proj_label} &nbsp;·&nbsp; Data: {data_label} &nbsp;·&nbsp; {date_str} &nbsp;·&nbsp; {time_str}
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

    {_build_exec_summary(jira, analytics, pm, _s)}

    {_build_kpi_summary(analytics, jira, pm)}

    {sec(f"Process-type Breakdown — Week {week}",
         _build_breakdown(analytics, scope_mode))}

    {sec(f"Operator Breakdown — Week {week}",
         _build_operator_breakdown(analytics)) if analytics.get("operator_breakdown") else ""}

    {sec(f"4-Week Trend — {project_name}",
         _build_trend_table(analytics, pm))}

    {sec(f"{jira_project} Sprint Health" if jira_project else "Sprint Health",
         _build_sprint(jira, jira_project))}

    {sec("Confluence — Weekly Progress",
         _build_confluence(confluence))}

    {sec("Recommended Actions &amp; Conclusion",
         _build_actions(jira, analytics, jira_project, project_name, list(pm)))}

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
