"""
HTML email formatter for UC3 Weekly Operational Report.
Different structure from daily (UC1): trend-first, week-over-week comparison.
Outlook-safe: table-based layout, inline CSS only.
"""
from datetime import datetime, timezone
from html import escape
from typing import Any

from email_html import (
    _rag, _badge, _dot, _arrow, _kv_table, _data_table, _section,
    _alert_row, _build_sprint, _build_confluence, _preview_banner,
    _build_exec_summary, _build_breakdown, _build_actions, _build_operator_breakdown, no_scope_notice,
    _build_action_box, action_items, overall_rag, headline_text,
    period_label, project_name_of,
    _eff_str, _escape_jira, _escape_confluence, _GREEN, _GREEN_BG, _GREEN_BD,
    _AMBER, _AMBER_BG, _AMBER_BD,
    _RED, _RED_BG, _RED_BD,
    _HDR, _SEC, _WHITE, _STRIPE, _TEXT, _MUTED, _BORDER, _F,
)


# ── Section builders ───────────────────────────────────────────────────────────

def _build_kpi_summary(analytics: dict, jira: dict, pm: set) -> str:
    """3 KPI boxes: current value + delta vs prior week."""
    cells = []

    def delta_str(curr: float, prev: float, higher_is_good: bool = True) -> str:
        """Coloured signed difference curr - prev, shown as a percentage; green when it moves the good way."""
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


def _trend_arrow(cur: float, prev: float | None, step: float, up_is_good: bool) -> str:
    """Week-on-week arrow for one cell; empty when the previous week has no value.

    Why: a week can carry the metric key with None (e.g. no Yield data that week). Subtracting it raised
    TypeError and stopped the whole weekly report for that user (found 6 Nov 2026), so no arrow is shown instead.
    """
    if prev is None:
        return ""
    d = cur - prev
    arr = "&#8593;" if d > step else "&#8595;" if d < -step else "&#8594;"
    good, bad = (_GREEN, _RED) if up_is_good else (_RED, _GREEN)
    col = good if d > 0 else bad if d < 0 else _MUTED
    return f'<span style="color:{col}"> {arr}</span>'


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

        if "fta" in pm and w.get("fta") is None:
            row.append(f'<span style="{_F};font-size:12px;color:{_MUTED}">N/A</span>')
        elif "fta" in pm:
            fta = w["fta"]
            fta_rag = "GREEN" if fta >= 95 else "AMBER" if fta >= 92 else "RED"
            c, bg, bd = _rag(fta_rag)
            arrow_html = _trend_arrow(fta, m4w[i - 1].get("fta", fta), 0.5, True) if i > 0 else ""
            row.append(
                f'<span style="background:{bg};color:{c};border:1px solid {bd};'
                f'padding:2px 6px;border-radius:3px;font-weight:bold;font-size:12px;{_F}">'
                f'{fta:.2f}%</span>{arrow_html}'
            )

        if ("coq" in pm or "copq" in pm) and w.get("coq") is None:
            row.append(f'<span style="{_F};font-size:12px;color:{_MUTED}">N/A</span>')
        elif "coq" in pm or "copq" in pm:
            coq = w["coq"]
            coq_rag = "GREEN" if coq < 7 else "AMBER" if coq < 10 else "RED"
            c, bg, bd = _rag(coq_rag)
            arrow_html = _trend_arrow(coq, m4w[i - 1].get("coq", coq), 0.2, False) if i > 0 else ""
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
                arrow_html = _trend_arrow(yv, m4w[i - 1].get("yield", yv), 0.2, True) if i > 0 else ""
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


def _trend_charts(analytics: dict, pm: set, images: dict | None) -> str:
    """The 8-week chart per process type (email_briefing_pt.weekly_trend_html); '' when no images are asked
    for or the charts fail, so the weekly report always goes out (a WARNING is logged)."""
    if images is None:
        return ""
    try:
        from email_briefing_pt import weekly_trend_html
        return weekly_trend_html(analytics, pm, images)
    except Exception as exc:
        import logging
        logging.getLogger("email_html_weekly").warning(f"UC3 trend charts left out: {type(exc).__name__}: {exc}")
        return ""


# ── Entry point ────────────────────────────────────────────────────────────────


# ── Delivery forecast ("Ops Weather", 9 Nov 2026) ─────────────────────────────────

FORECAST_ROWS = 10     # work packages with a forecast
WAITING_ROWS  = 5      # largest work packages nobody worked on
OM_ROWS       = 8


def _fc_num(v: float | int | None, nd: int = 0) -> str:
    """Thousands-separated number, "–" for missing."""
    return "–" if v is None else f"{v:,.{nd}f}"


def _forecast_howto(fc: dict, work_days: int, cap_days: int, trickle: int) -> str:
    """"How to read this" box: the rule in plain words plus one real row worked through, an OM-pace row when there
    is one (the case PMs found hardest to read, 9 Nov 2026), so nobody takes a forecast for a commitment."""
    items = [it for it in fc["items"] if it["days"] is not None]
    ex = next((it for it in items if it["basis"] == "om"), items[0] if items else None)
    rule = (f"<b>How to read this.</b> Work days left = pending tasks &divide; tasks done per work day in the last "
            f"4 full weeks ({work_days} work days). Editors and tasks/h show the team and pace behind it. A work "
            f"package with fewer than {trickle} tasks of its own in 4 weeks is forecast to finish <i>with its OM "
            f"ticket</i>: all of the OM&#39;s pending tasks at the OM&#39;s pace. Beyond {cap_days} work days the "
            f"email shows &ldquo;&gt; 1 year&rdquo;. It is today&#39;s pace, not a plan: more editors make it "
            f"shorter.")
    if ex and ex["basis"] == "om":
        per_day = ex["om_tasks_4w"] / work_days
        example = (f"<br><b>Example:</b> {escape(ex['wp'])} had no work of its own in 4 weeks. Its OM "
                   f"{escape(ex['om'])} did {ex['om_tasks_4w']:,} tasks ({per_day:,.1f} a day, {ex['editors']:,} "
                   f"editors) and has {ex['om_pending']:,} pending tasks in {ex['om_wps']:,} work packages: "
                   f"{ex['om_pending']:,} &divide; {per_day:,.1f} = {ex['days']:,.0f} work days"
                   + (" (shown as &ldquo;&gt; 1 year&rdquo;)." if ex["days"] > cap_days else "."))
    elif ex:
        per_day = ex["tasks_4w"] / work_days
        example = (f"<br><b>Example:</b> {escape(ex['wp'])} did {ex['tasks_4w']:,} tasks in 4 weeks "
                   f"({per_day:,.1f} a day, {ex['editors']:,} editors): {ex['pending']:,} pending &divide; "
                   f"{per_day:,.1f} = {ex['days']:,.0f} work days.")
    else:
        example = ""
    return (f'<div style="{_F};font-size:11px;color:{_TEXT};background:{_STRIPE};border:1px solid {_BORDER};'
            f'padding:8px 10px;margin-bottom:10px">{rule}{example}</div>')


def _build_forecast(fc: dict | None) -> str:
    """Delivery forecast section: band totals, the WPs being worked on with their work days left, the largest
    waiting WPs and the OM roll-up. Empty (section left out) when there is no forecast or nothing pending.

    Work package names come from Databricks and are escaped. Rows are ordered by pending tasks, largest first,
    because size is what a manager plans around; the band shows the timing.
    """
    from delivery_forecast import BANDS, WORK_DAYS, CAP_DAYS, TRICKLE_TASKS, days_text, basis_text
    if not fc or fc.get("error") or fc.get("off") or not fc.get("items"):
        return ""
    sym = lambda b: BANDS[b][0]
    tot = fc["totals"]
    summary = " &nbsp;·&nbsp; ".join(
        f'{sym(b)} {BANDS[b][1]}: <b>{tot[b]["wps"]:,}</b> WPs, {tot[b]["pending"]:,} tasks'
        for b in BANDS if tot[b]["wps"])
    intro = (f'<div style="{_F};font-size:12px;color:{_TEXT};margin-bottom:10px">'
             f'<b>{fc["pending_total"]:,}</b> pending tasks in {len(fc["items"]):,} work packages. '
             f'Work days left = pending tasks &divide; tasks done per work day, at the pace of '
             f'{fc["pace_from"]} to {fc["pace_to"]} (tasks/h &times; editors&#39; hours).<br>{summary}</div>')

    worked = [it for it in fc["items"] if it["days"] is not None][:FORECAST_ROWS]
    rows = [[sym(it["band"]), escape(it["wp"]), escape(it["om"]) or "–", _fc_num(it["pending"]),
             _fc_num(it["editors"]), _fc_num(it["tph"], 1), days_text(it["days"]), basis_text(it)]
            for it in worked]
    out = intro + _forecast_howto(fc, WORK_DAYS, CAP_DAYS, TRICKLE_TASKS)
    if rows:
        out += _data_table(["", "Work package", "OM", "Pending", "Editors", "Tasks/h", "Work days", "Basis"], rows)
    waiting = [it for it in fc["items"] if it["days"] is None][:WAITING_ROWS]
    if waiting:
        out += (f'<div style="{_F};font-size:12px;font-weight:bold;color:{_TEXT};margin:12px 0 6px">'
                f'Largest work packages waiting — no forecast possible</div>')
        out += _data_table(["", "Work package", "OM", "Pending", "Why"],
                           [[sym(it["band"]), escape(it["wp"]), escape(it["om"]) or "–", _fc_num(it["pending"]),
                             BANDS[it["band"]][1]] for it in waiting])
    oms = fc.get("oms", [])[:OM_ROWS]
    if oms:
        out += (f'<div style="{_F};font-size:12px;font-weight:bold;color:{_TEXT};margin:12px 0 6px">'
                f'By OM ticket (whole OM at its own pace)</div>')
        out += _data_table(["", "OM", "Work packages", "Pending", "Work days"],
                           [[sym(g["band"]), escape(g["om"]), _fc_num(g["wps"]), _fc_num(g["pending"]),
                             days_text(g["days"]) if g["days"] is not None else BANDS[g["band"]][1]]
                            for g in oms])
    out += (f'<div style="{_F};font-size:11px;color:{_MUTED};margin-top:8px">Source: project_pending_task_tbl '
            f'(snapshot) and the weekly KPI table. {fc["excluded"]} are left out.</div>')
    return out


def build(
    jira: dict[str, Any],
    analytics: dict[str, Any],
    confluence: dict[str, Any] | None = None,
    skill: dict[str, Any] | None = None,
    preview_note: str | None = None,
    images: dict[str, bytes] | None = None,
    forecast: dict[str, Any] | None = None,
) -> str:
    """Render the UC3 Weekly Operational Report as an HTML email string.

    Jira/Confluence text is HTML-escaped first; sections are numbered and empty ones are left out.
    images: given by the sender that can embed pictures; the 8-week chart per process type is added to it as
    {cid: png} (OSI-010, 6 Nov 2026). Without it (Word report, previews) the report is as before.
    forecast: delivery_forecast.run() output; the "Delivery Forecast" section is left out without it.
    """
    from skill_registry import jira_label
    jira         = _escape_jira(jira)              # untrusted Jira / Confluence text
    confluence   = _escape_confluence(confluence)
    _s           = skill or {}
    project_name = project_name_of(_s)
    jira_project = jira_label(_s, jira)            # every key checked, e.g. "OM, MCPET" (OSI-061)
    user_name    = _s.get("user_first_name") or "you"
    proj_label   = f"{project_name} ({jira_project})" if jira_project else project_name
    pm           = set(_s.get("primary_metrics") or ["fta", "efficiency", "coq"])
    show_eff     = bool(pm & {"efficiency", "coq", "copq"})

    now        = datetime.now(timezone.utc)
    date_str   = now.strftime("%A, %d %B %Y")
    time_str   = now.strftime("%H:%M UTC")
    week       = analytics.get("week_label", "")
    data_label = period_label(week) if week else "no scope in your profile"

    overall = overall_rag(jira, analytics, pm)   # one rule for UC1, UC3 and Word (30 Oct)
    oc, _, _ = _rag(overall)

    # scope_mode: "defined" when the skill has explicit process types, else "all"
    pts = _s.get("databricks_process_types") or []
    scope_mode = _s.get("scope_mode") or ("defined" if pts else "all")

    # Auto-number sections
    n = [0]
    def sec(title, body):
        """Number and render a section; returns "" when body is empty."""
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

    {no_scope_notice(_s)}

    {_build_action_box(jira, analytics, set(pm or [])) if not analytics.get("no_scope") else ""}

    {_build_kpi_summary(analytics, jira, pm)}

    {sec(f"Work Unit &amp; Process-type Breakdown — {period_label(week)}",
         _build_breakdown(analytics, scope_mode)) if not analytics.get("no_scope") else ""}

    {sec(f"Operators past an alert level — {period_label(week)}",
         _build_operator_breakdown(analytics)) if analytics.get("operator_breakdown") else ""}

    {sec(f"4-Week Trend — {project_name}",
         _build_trend_table(analytics, pm)) if not analytics.get("no_scope") else ""}

    {sec(f"8-Week Trend per Process Type — {project_name}", _trend_charts(analytics, pm, images))
     if not analytics.get("no_scope") else ""}

    {sec("Delivery Forecast — pending work packages and OM tickets", _build_forecast(forecast))}

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
