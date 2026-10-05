"""
HTML email formatter for UC1 Daily Briefing.
Clean single-column layout: proper tables, no multi-column cards.
Outlook-safe: table-based layout, inline CSS only.
"""
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

# ── Palette ────────────────────────────────────────────────────────────────────
_GREEN  = "#1E8449"; _GREEN_BG  = "#EAF7EF"; _GREEN_BD  = "#A9DFBF"
_AMBER  = "#B7770D"; _AMBER_BG  = "#FEF9E7"; _AMBER_BD  = "#F9E79F"
_RED    = "#922B21"; _RED_BG    = "#FDEDEC"; _RED_BD    = "#F5B7B1"
_BLUE   = "#1A5276"; _BLUE_BG   = "#EBF5FB"; _BLUE_BD   = "#AED6F1"

_HDR    = "#1B2A4A"   # header background
_SEC    = "#F4F6F9"   # section header background
_WHITE  = "#FFFFFF"
_STRIPE = "#F8F9FA"   # alternate table row
_TEXT   = "#1C2B3A"
_MUTED  = "#6B7A8D"
_BORDER = "#D5DBE2"
_F      = "font-family:Arial,Helvetica,sans-serif"

_RAG_PALETTE = {
    "GREEN":    (_GREEN,  _GREEN_BG,  _GREEN_BD),
    "AMBER":    (_AMBER,  _AMBER_BG,  _AMBER_BD),
    "AMBER_P3": (_AMBER,  _AMBER_BG,  _AMBER_BD),
    "AMBER_P2": (_AMBER,  _AMBER_BG,  _AMBER_BD),
    "RED":      (_RED,    _RED_BG,    _RED_BD),
    "RED_P1":   (_RED,    _RED_BG,    _RED_BD),
    "BREACH_72H":  (_RED,   _RED_BG,   _RED_BD),
    "WARNING_48H": (_AMBER, _AMBER_BG, _AMBER_BD),
    "OK":          (_GREEN, _GREEN_BG, _GREEN_BD),
}

def _rag(key):
    return _RAG_PALETTE.get(key, (_MUTED, "#F0F0F0", "#CCCCCC"))


def _badge(rag: str, label: str = "") -> str:
    c, bg, bd = _rag(rag)
    text = label or rag.replace("_", " ")
    return (
        f'<span style="background:{bg};color:{c};border:1px solid {bd};'
        f'padding:1px 7px;border-radius:3px;font-size:11px;font-weight:bold;{_F}">'
        f'{text}</span>'
    )


def _dot(rag: str) -> str:
    c, _, _ = _rag(rag)
    return f'<span style="color:{c}">&#9679;</span>'


def _arrow(trend: str) -> str:
    return {"improving": "&#8593;", "stable": "&#8594;", "declining": "&#8595;"}.get(trend, "&#8594;")


def _eff_str(eff_vs_bl: float | None) -> str:
    if eff_vs_bl is None:
        return "N/A"
    d = eff_vs_bl - 100
    return f"{eff_vs_bl:.1f}% ({'+'if d>=0 else ''}{d:.1f}%)"


# ── Layout helpers ─────────────────────────────────────────────────────────────

def _section(heading: str, body: str, n: int) -> str:
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;border:1px solid {_BORDER};border-radius:4px">
  <tr>
    <td style="background:{_SEC};padding:8px 14px;border-bottom:1px solid {_BORDER};border-radius:4px 4px 0 0">
      <span style="{_F};font-size:12px;font-weight:bold;color:{_HDR};letter-spacing:0.4px">
        {n}.&nbsp; {heading}
      </span>
    </td>
  </tr>
  <tr>
    <td style="background:{_WHITE};padding:14px 16px;border-radius:0 0 4px 4px">
      {body}
    </td>
  </tr>
</table>"""


def _kv_table(rows: list[tuple[str, str, str]]) -> str:
    """Render key-value rows: (label, value_html, value_color)."""
    html = f'<table width="100%" cellpadding="0" cellspacing="0">'
    for label, value, color in rows:
        html += (
            f'<tr>'
            f'<td style="{_F};font-size:12px;color:{_MUTED};padding:4px 0;'
            f'width:200px;vertical-align:top">{label}</td>'
            f'<td style="{_F};font-size:13px;color:{color};padding:4px 0;font-weight:600">'
            f'{value}</td>'
            f'</tr>'
        )
    html += '</table>'
    return html


def _data_table(headers: list[str], rows: list[list[str]]) -> str:
    """Full-width striped data table."""
    th_style = (
        f'{_F};font-size:12px;font-weight:bold;color:{_WHITE};'
        f'background:{_HDR};padding:7px 10px;text-align:left;border-bottom:2px solid {_BORDER}'
    )
    td_style_even = f'{_F};font-size:12px;color:{_TEXT};padding:7px 10px;background:{_WHITE};border-bottom:1px solid {_BORDER}'
    td_style_odd  = f'{_F};font-size:12px;color:{_TEXT};padding:7px 10px;background:{_STRIPE};border-bottom:1px solid {_BORDER}'

    html = (
        f'<table width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;border:1px solid {_BORDER};border-radius:4px">'
        f'<tr>' + ''.join(f'<th style="{th_style}">{h}</th>' for h in headers) + '</tr>'
    )
    for i, row in enumerate(rows):
        td = td_style_even if i % 2 == 0 else td_style_odd
        html += '<tr>' + ''.join(f'<td style="{td}">{cell}</td>' for cell in row) + '</tr>'
    html += '</table>'
    return html


def _alert_row(rag: str, label: str, text: str, detail: str = "") -> str:
    c, bg, bd = _rag(rag)
    detail_html = (
        f'<div style="{_F};font-size:11px;color:{_MUTED};margin-top:3px">{detail}</div>'
        if detail else ""
    )
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:7px">'
        f'<tr><td style="background:{bg};border-left:4px solid {c};'
        f'padding:9px 13px;border-radius:0 3px 3px 0">'
        f'<span style="background:{c};color:#fff;padding:1px 6px;border-radius:2px;'
        f'font-size:10px;font-weight:bold;{_F};margin-right:8px">{label}</span>'
        f'<span style="{_F};font-size:13px;color:{_TEXT}">{text}</span>'
        f'{detail_html}'
        f'</td></tr></table>'
    )


def _divider() -> str:
    return f'<div style="border-top:1px solid {_BORDER};margin:10px 0"></div>'


# ── Jira create button ─────────────────────────────────────────────────────────

def _btn(summary: str, description: str, jira_project: str = "", priority: str = "Medium") -> str:
    import os
    try:
        from config import JIRA_BASE_URL, JIRA_PROJECT_NUMERIC_ID, JIRA_PROJECT as _p
    except ImportError:
        JIRA_BASE_URL, JIRA_PROJECT_NUMERIC_ID, _p = "https://tomtom.atlassian.net", "", ""
    pk  = jira_project or _p
    iid = os.getenv("JIRA_ISSUE_TYPE_ID", "10016")
    pid = {"Highest":"1","High":"2","Medium":"3","Low":"4","Lowest":"5"}.get(priority, "3")
    if JIRA_PROJECT_NUMERIC_ID:
        url = (f"{JIRA_BASE_URL}/secure/CreateIssueDetails!init.jspa?"
               + urlencode({"pid": JIRA_PROJECT_NUMERIC_ID, "issuetype": iid,
                             "priority": pid, "summary": summary[:200],
                             "description": description[:2000]}))
    else:
        url = f"{JIRA_BASE_URL}/jira/software/projects/{pk}/issues/new"
    return (
        f'<a href="{url}" target="_blank" style="display:inline-block;background:#2563EB;'
        f'color:#fff;{_F};font-size:11px;font-weight:bold;padding:2px 8px;'
        f'border-radius:3px;text-decoration:none;margin-left:8px">+ Ticket &#8599;</a>'
    )


# ── KPI Summary row ────────────────────────────────────────────────────────────

def _build_kpi_row(analytics: dict, jira: dict, pm: set) -> str:
    """Single-row KPI summary table at the top — one cell per metric."""
    cells = []

    if "fta" in pm:
        fta  = analytics.get("fta_current", 0.0)
        rag  = analytics.get("fta_rag", "GREEN")
        c, bg, bd = _rag(rag)
        cells.append((
            "FTA",
            f'<span style="{_F};font-size:22px;font-weight:bold;color:{c}">{fta:.2f}%</span>',
            _badge(rag), bg, bd
        ))

    if "efficiency" in pm:
        ev  = analytics.get("efficiency_vs_bl")
        rag = analytics.get("efficiency_rag", "GREEN")
        c, bg, bd = _rag(rag)
        cells.append((
            "Efficiency vs BL",
            f'<span style="{_F};font-size:22px;font-weight:bold;color:{c}">{_eff_str(ev)}</span>',
            _badge(rag), bg, bd
        ))

    if "coq" in pm or "copq" in pm:
        coq = analytics.get("coq_current", 0.0)
        rag = analytics.get("coq_rag", "GREEN")
        c, bg, bd = _rag(rag)
        cells.append((
            "Cost of Quality",
            f'<span style="{_F};font-size:22px;font-weight:bold;color:{c}">{coq:.2f}%</span>',
            _badge(rag), bg, bd
        ))

    br  = len(jira.get("sla_breaches", []))
    wa  = len(jira.get("sla_warnings", []))
    j_rag = "RED" if br else "AMBER" if wa else "GREEN"
    c, bg, bd = _rag(j_rag)
    cells.append((
        "Jira SLA Alerts",
        f'<span style="{_F};font-size:22px;font-weight:bold;color:{c}">{br + wa}</span>',
        f'<span style="{_F};font-size:11px;color:{_MUTED}">{br} breach · {wa} warning</span>',
        bg, bd
    ))

    if not cells:
        return ""

    col_w = 100 // len(cells)
    tds = ""
    for i, (label, big, sub, bg, bd) in enumerate(cells):
        pad = "padding-left:8px" if i else ""
        tds += (
            f'<td width="{col_w}%" style="{pad}">'
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="background:{bg};border:1px solid {bd};border-radius:4px">'
            f'<tr><td style="padding:12px 14px">'
            f'<div style="{_F};font-size:11px;color:{_MUTED};font-weight:bold;'
            f'text-transform:uppercase;letter-spacing:0.4px;margin-bottom:5px">{label}</div>'
            f'{big}'
            f'<div style="margin-top:5px">{sub}</div>'
            f'</td></tr></table>'
            f'</td>'
        )
    return (
        f'<table width="100%" cellpadding="0" cellspacing="8" style="margin-bottom:18px">'
        f'<tr>{tds}</tr></table>'
    )


# ── Section builders ───────────────────────────────────────────────────────────

def _build_priority(jira, analytics, jira_project="", project_name="",
                    primary_metrics=None):
    pm = set(primary_metrics or ["fta", "efficiency", "coq"])
    br = jira.get("sla_breaches", [])
    wa = jira.get("sla_warnings", [])
    bd = analytics.get("process_breakdown", [])
    ev = analytics.get("efficiency_vs_bl")
    er = analytics.get("efficiency_rag", "GREEN")
    fr = analytics.get("fta_rag", "GREEN")
    fv = analytics.get("fta_current", 0.0)
    fp = analytics.get("fta_prev_week", 0.0)
    wk = analytics.get("week_label", "")

    items = []

    for t in br:
        d = round(t["hours_stale"]/24, 1)
        b = _btn(f"SLA Breach: {t['key']} — {t['summary'][:60]}",
                 f"Ticket {t['key']} silent {t['hours_stale']}h. Owner: {t['assignee']}. "
                 f"Status: {t['status']}. Link: {t['url']}",
                 jira_project, "High")
        items.append(_alert_row("BREACH_72H", "SLA BREACH",
            f'<a href="{t["url"]}" style="color:#2563EB;font-weight:bold;'
            f'text-decoration:none">{t["key"]}</a> — {t["summary"][:65]}{b}',
            f'Owner: {t["assignee"]} · Silent {d} days ({t["hours_stale"]}h) · {t["status"]}'))

    for t in wa:
        b = _btn(f"SLA Warning: {t['key']} — {t['summary'][:60]}",
                 f"Ticket {t['key']} no update for {t['hours_stale']}h. Owner: {t['assignee']}. "
                 f"Status: {t['status']}. Link: {t['url']}", jira_project)
        items.append(_alert_row("WARNING_48H", "SLA WARNING",
            f'<a href="{t["url"]}" style="color:#2563EB;font-weight:bold;'
            f'text-decoration:none">{t["key"]}</a> — {t["summary"][:65]}{b}',
            f'Owner: {t["assignee"]} · {t["hours_stale"]}h without update'))

    if "fta" in pm:
        for p in bd:
            if p.get("fta_rag") in ("AMBER", "RED"):
                b = _btn(f"FTA Concern: {p['process_type']} at {p['fta_pct']:.2f}%",
                         f"processType '{p['process_type']}' FTA {p['fta_pct']:.2f}%, "
                         f"CoQ {p['coq_pct']:.1f}%, week {wk}.", jira_project)
                items.append(_alert_row(p["fta_rag"], "FTA CONCERN",
                    f'<b>{p["process_type"]}</b> — FTA <b>{p["fta_pct"]:.2f}%</b> · '
                    f'Eff vs BL <b>{_eff_str(p.get("eff_vs_bl"))}</b> · '
                    f'CoQ <b>{p["coq_pct"]:.1f}%</b>{b}', f'Week {wk}'))

    if "efficiency" in pm and er == "RED":
        items.append(_alert_row("RED", "EFFICIENCY ALERT",
            f'Efficiency <b>{_eff_str(ev)}</b> — below 90% of baseline for week {wk}', ""))

    if "fta" in pm and fr in ("AMBER", "RED"):
        b = _btn(f"FTA Alert: {project_name or jira_project} at {fv:.2f}%",
                 f"FTA {fv:.2f}% ({fr}). Prev week {fp:.2f}%. Week {wk}.",
                 jira_project, "High" if fr == "RED" else "Medium")
        items.append(_alert_row(fr, "FTA ALERT",
            f'Overall FTA <b>{fv:.2f}%</b> (prev week {fp:.2f}%){b}', ""))

    if not items:
        return _alert_row("GREEN", "ALL CLEAR", "No critical items — metrics are on track.", "")

    return "\n".join(items)


def _build_sprint(jira, jira_project=""):
    br    = jira.get("sla_breaches", [])
    wa    = jira.get("sla_warnings", [])
    total = jira.get("total_open", 0)
    ok    = max(total - len(br) - len(wa), 0)
    err   = jira.get("error")
    as_of = jira.get("as_of", "")[:16]

    if err:
        return f'<p style="{_F};font-size:13px;color:{_MUTED}">Jira unavailable: {err}</p>'

    def box(label, val, rag):
        c, bg, bd = _rag(rag)
        return (
            f'<td style="padding-right:12px">'
            f'<table cellpadding="0" cellspacing="0" style="background:{bg};'
            f'border:1px solid {bd};border-radius:4px;text-align:center;min-width:80px">'
            f'<tr><td style="padding:12px 16px">'
            f'<div style="{_F};font-size:26px;font-weight:bold;color:{c}">{val}</div>'
            f'<div style="{_F};font-size:11px;color:{_MUTED};margin-top:2px">{label}</div>'
            f'</td></tr></table></td>'
        )

    b_rag = "RED"   if br    else "GREEN"
    w_rag = "AMBER" if wa    else "GREEN"
    t_rag = "GREEN" if total == 0 else "AMBER"

    return (
        f'<table cellpadding="0" cellspacing="0"><tr>'
        + box("Total Open",  str(total),   t_rag)
        + box("SLA Breach",  str(len(br)), b_rag)
        + box("SLA Warning", str(len(wa)), w_rag)
        + box("On Track",    str(ok),      "GREEN")
        + f'</tr></table>'
        + f'<p style="{_F};font-size:11px;color:{_MUTED};margin:8px 0 0">'
          f'Source: Jira {jira_project} · as of {as_of} UTC</p>'
    )


def _build_fta(analytics, jira_project=""):
    fta = analytics.get("fta_current",  0.0)
    rag = analytics.get("fta_rag",      "GREEN")
    t4w = analytics.get("fta_4w",       [])
    tr  = analytics.get("fta_trend",    "stable")
    wk  = analytics.get("week_label",   "")
    src = analytics.get("source",       "Databricks")
    c, bg, bd = _rag(rag)

    trend_str = " &nbsp;&#8594;&nbsp; ".join(
        f'<b>{w["fta"]:.2f}%</b> <span style="color:{_MUTED};font-size:11px">({w["week"]})</span>'
        for w in reversed(t4w)
    ) if t4w else f"<b>{fta:.2f}%</b>"

    note = {
        "GREEN": "FTA is healthy — no quality escalation needed.",
        "AMBER": f'Amber zone — monitor rework tickets{" in " + jira_project if jira_project else ""}.',
        "RED":   "P1 ALERT — FTA below 92%. Immediate review required.",
    }.get(rag, "")

    rows = [
        ("FTA this week",
         f'{_dot(rag)} <span style="font-size:18px;font-weight:bold;color:{c}">{fta:.2f}%</span>'
         f' &nbsp; {_badge(rag)}', c),
        ("4-week trend",    trend_str, _TEXT),
        ("Trend direction", f'{_arrow(tr)} {tr.capitalize()}', c),
        ("Week",            wk, _MUTED),
        ("Source",          f'<span style="font-size:11px;color:{_MUTED}">{src}</span>', _MUTED),
    ]
    html = _kv_table(rows)
    if note:
        html += (
            f'<div style="background:{bg};border-left:3px solid {c};'
            f'padding:8px 12px;margin-top:10px;border-radius:0 3px 3px 0;'
            f'{_F};font-size:12px;color:{_TEXT}">{note}</div>'
        )
    return html


def _build_efficiency(analytics):
    ev  = analytics.get("efficiency_vs_bl")
    er  = analytics.get("efficiency_raw")
    erg = analytics.get("efficiency_rag", "GREEN")
    cq  = analytics.get("coq_current",   0.0)
    crg = analytics.get("coq_rag",       "GREEN")
    ch  = analytics.get("copq_hrs")
    cp  = analytics.get("copq_pct")
    ph  = analytics.get("prod_hrs")
    qh  = analytics.get("qc_hrs")
    wk  = analytics.get("week_label",    "")
    ec, _, _ = _rag(erg)
    cc, _, _ = _rag(crg)

    coq_label = (
        "Healthy &lt;5%"       if cq < 5  else
        "P3 Monitor 5–7%"      if cq < 7  else
        "P2 Investigate 7–10%" if cq < 10 else
        "P1 Escalate &gt;10%"
    )
    eff_sub = f'<br><span style="{_F};font-size:11px;color:{_MUTED}">Raw: {er:.4f} tasks/hr</span>' if er else ""
    copq_sub = ""
    if ch is not None:
        copq_sub = f' &nbsp;·&nbsp; CopQ: {ch:.1f}h rework ({cp:.2f}% of hrs)' if cp else f' &nbsp;·&nbsp; CopQ: {ch:.1f}h rework'

    rows = [
        ("Efficiency vs Baseline",
         f'{_dot(erg)} <span style="font-size:18px;font-weight:bold;color:{ec}">'
         f'{_eff_str(ev)}</span> &nbsp; {_badge(erg)}{eff_sub}', ec),
        ("Cost of Quality (CoQ)",
         f'{_dot(crg)} <span style="font-size:18px;font-weight:bold;color:{cc}">'
         f'{cq:.2f}%</span> &nbsp; {_badge(crg, coq_label)}{copq_sub}', cc),
    ]
    if ph is not None and qh is not None:
        total = ph + qh
        rows.append(("Hours breakdown",
                     f'Production <b>{ph:.0f}h</b> &nbsp;·&nbsp; '
                     f'QC <b>{qh:.0f}h</b> &nbsp;·&nbsp; Total <b>{total:.0f}h</b>', _TEXT))
    rows.append(("Week", wk, _MUTED))
    return _kv_table(rows)


def _build_breakdown(analytics):
    bd  = analytics.get("process_breakdown", [])
    wk  = analytics.get("week_label",        "")
    sc  = analytics.get("scope_label",       "")

    if not bd:
        return f'<p style="{_F};font-size:13px;color:{_MUTED}">No process data for this week.</p>'

    def fta_cell(val, rag):
        c, bg, bd = _rag(rag)
        return (
            f'<span style="background:{bg};color:{c};border:1px solid {bd};'
            f'padding:2px 7px;border-radius:3px;font-weight:bold;font-size:12px;{_F}">'
            f'{val:.2f}%</span>'
        )

    def eff_cell(ev):
        if ev is None:
            return f'<span style="{_F};font-size:12px;color:{_MUTED}">N/A</span>'
        rag = "GREEN" if ev >= 100 else "AMBER" if ev >= 90 else "RED"
        c, _, _ = _rag(rag)
        d = ev - 100
        return f'<span style="{_F};font-size:12px;color:{c};font-weight:600">{_eff_str(ev)}</span>'

    headers = ["Process Type", "FTA", "Eff vs Baseline", "CoQ", "Tasks", "Hrs"]
    rows = []
    for p in bd:
        rows.append([
            f'<span style="{_F};font-family:Consolas,Courier New,monospace;font-size:12px">'
            f'{p["process_type"]}</span>',
            fta_cell(p["fta_pct"], p["fta_rag"]),
            eff_cell(p.get("eff_vs_bl")),
            f'<span style="{_F};font-size:12px">{p["coq_pct"]:.1f}%</span>',
            f'<span style="{_F};font-size:12px">{p["prod_tasks"]:,}</span>',
            f'<span style="{_F};font-size:12px">{p["total_hrs"]:.0f}h</span>',
        ])

    note = ""
    if sc or wk:
        note = (
            f'<p style="{_F};font-size:11px;color:{_MUTED};margin:8px 0 0">'
            + (f'Scope: {sc} &nbsp;·&nbsp; ' if sc else '')
            + (f'Week: {wk}' if wk else '')
            + '</p>'
        )
    return _data_table(headers, rows) + note


def _build_tickets(jira):
    ts = jira.get("open_tickets", [])
    if not ts:
        return f'<p style="{_F};font-size:13px;color:{_MUTED}">No open tickets in scope.</p>'

    headers = ["Ticket", "Summary", "Status", "Owner", "Stale", "SLA"]
    rows = []
    for t in ts:
        rows.append([
            f'<a href="{t["url"]}" style="color:#2563EB;font-weight:bold;'
            f'text-decoration:none;{_F};font-size:12px">{t["key"]}</a>',
            f'<span style="{_F};font-size:12px">{t["summary"][:55]}</span>',
            f'<span style="{_F};font-size:12px">{t["status"]}</span>',
            f'<span style="{_F};font-size:12px">{t["assignee"]}</span>',
            f'<span style="{_F};font-size:12px">{t["hours_stale"]}h</span>',
            _badge(t["sla_status"], t["sla_status"].replace("_", " ")),
        ])
    return _data_table(headers, rows)


def _build_actions(jira, analytics, jira_project="", project_name="",
                   primary_metrics=None):
    pm  = set(primary_metrics or ["fta", "efficiency", "coq"])
    br  = jira.get("sla_breaches", [])
    wa  = jira.get("sla_warnings", [])
    bd  = analytics.get("process_breakdown", [])
    fr  = analytics.get("fta_rag",          "GREEN")
    fv  = analytics.get("fta_current",      0.0)
    ft  = analytics.get("fta_trend",        "stable")
    cq  = analytics.get("coq_current",      0.0)
    crg = analytics.get("coq_rag",          "GREEN")
    ch  = analytics.get("copq_hrs")
    ev  = analytics.get("efficiency_vs_bl")
    erg = analytics.get("efficiency_rag",   "GREEN")
    wk  = analytics.get("week_label",       "")
    prj = project_name or jira_project or "Project"

    actions = []

    for t in br:
        b = _btn(f"SLA Breach: {t['key']} — {t['summary'][:60]}",
                 f"Ticket {t['key']} silent {t['hours_stale']}h. Owner: {t['assignee']}. "
                 f"Status: {t['status']}. Link: {t['url']}", jira_project)
        actions.append(("BREACH_72H",
            f'Follow up with <b>{t["assignee"]}</b> on '
            f'<a href="{t["url"]}" style="color:#2563EB">{t["key"]}</a>'
            f' — stale {t["hours_stale"]}h, SLA breached. '
            f'<span style="color:{_MUTED}">(draft ready, awaiting approval)</span>{b}'))

    for t in wa:
        b = _btn(f"SLA Warning: {t['key']}",
                 f"No update for {t['hours_stale']}h. Owner: {t['assignee']}. Link: {t['url']}",
                 jira_project)
        actions.append(("WARNING_48H",
            f'Nudge <b>{t["assignee"]}</b> on '
            f'<a href="{t["url"]}" style="color:#2563EB">{t["key"]}</a>'
            f' — {t["hours_stale"]}h without update, approaching 48h SLA.{b}'))

    if "fta" in pm:
        for p in bd:
            if p.get("fta_rag") in ("AMBER", "RED"):
                b = _btn(f"FTA: {p['process_type']} at {p['fta_pct']:.2f}%",
                         f"processType '{p['process_type']}' FTA {p['fta_pct']:.2f}%, "
                         f"CoQ {p['coq_pct']:.1f}%, week {wk}.", jira_project,
                         "High" if p["fta_rag"] == "RED" else "Medium")
                actions.append((p["fta_rag"],
                    f'Investigate <b>{p["process_type"]}</b> — FTA {p["fta_pct"]:.2f}%,'
                    f' week {wk}. Review rejection patterns.{b}'))

    if "fta" in pm and fr != "GREEN":
        b = _btn(f"FTA Review: {prj} at {fv:.2f}%",
                 f"Overall FTA {fv:.2f}% ({ft}). Week {wk}.",
                 jira_project, "High" if fr == "RED" else "Medium")
        actions.append((fr,
            f'Review overall FTA <b>{fv:.2f}%</b> ({ft}) for {prj}. '
            f'Cross-check quality-labelled tickets.{b}'))

    if "coq" in pm and crg in ("AMBER_P2", "RED_P1"):
        cn = f' — CopQ: {ch:.1f}h of rework.' if ch else ''
        b  = _btn(f"CoQ: {prj} at {cq:.2f}%",
                  f"CoQ {cq:.2f}% for week {wk}." + (f" Rework: {ch:.1f}h." if ch else ""),
                  jira_project, "High" if crg == "RED_P1" else "Medium")
        actions.append((crg,
            f'CoQ at <b>{cq:.2f}%</b> — review rework patterns for week {wk}.{cn}{b}'))

    if "efficiency" in pm and erg == "RED" and ev is not None:
        b = _btn(f"Efficiency Alert: {prj} at {ev:.1f}% vs baseline",
                 f"Efficiency {ev:.1f}% of baseline, week {wk}.", jira_project, "High")
        actions.append(("RED",
            f'Efficiency at <b>{_eff_str(ev)}</b> — identify bottlenecks in '
            f'low-performing process types.{b}'))

    if not actions:
        return _alert_row("GREEN", "ALL CLEAR",
                          "No immediate actions required. Day is on track.", "")

    items = ""
    for idx, (rag, text) in enumerate(actions, 1):
        c, bg, bd = _rag(rag)
        items += (
            f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:7px">'
            f'<tr><td style="background:{bg};border-left:4px solid {c};'
            f'padding:9px 13px;border-radius:0 3px 3px 0">'
            f'<span style="{_F};font-size:13px;color:{_TEXT}">'
            f'<b style="color:{c}">{idx}.</b>&nbsp; {text}'
            f'</span></td></tr></table>'
        )
    return items


def _build_confluence(confluence):
    pages = confluence.get("pages", [])
    err   = confluence.get("error")
    if err and not pages:
        return f'<p style="{_F};font-size:13px;color:{_MUTED}">Confluence unavailable: {err}</p>'
    if not pages:
        return f'<p style="{_F};font-size:13px;color:{_MUTED}">No Confluence pages configured.</p>'

    out = ""
    for page in pages:
        title   = page.get("page_title", "(untitled)")
        url     = page.get("page_url", "#")
        days    = page.get("days_since_update", 999.0)
        updated = page.get("last_updated", "")[:10]
        by_who  = page.get("last_updated_by", "")
        overdue = page.get("update_overdue", False)
        excerpt = page.get("excerpt", "")
        perr    = page.get("error")

        if perr:
            out += _alert_row("AMBER", "ERROR", f"Could not fetch page — {perr}", "")
            continue

        rag = "AMBER" if overdue else "GREEN"
        det = f'Last updated: <b>{updated}</b>' + (f' by {by_who}' if by_who else '')
        if excerpt:
            det += f' &nbsp;·&nbsp; {excerpt[:200]}...'
        out += _alert_row(rag,
                          f"Stale {int(days)}d" if overdue else f"Updated {int(days)}d ago",
                          f'<a href="{url}" style="color:#2563EB;text-decoration:none;'
                          f'font-weight:bold">{title}</a>', det)
    return out


# ── Preview banner ─────────────────────────────────────────────────────────────

def _preview_banner(note: str) -> str:
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:14px">'
        f'<tr><td style="background:#FEF3CD;border:1px solid #F0C040;border-left:5px solid #D4A017;'
        f'padding:12px 16px;border-radius:4px">'
        f'<span style="{_F};font-size:13px;font-weight:bold;color:#7D5A00">&#128203; Preview</span>'
        f'<span style="{_F};font-size:12px;color:#5D4200;display:block;margin-top:4px">{note}</span>'
        f'</td></tr></table>'
    )


# ── Entry point ────────────────────────────────────────────────────────────────

def build(jira: dict[str, Any], analytics: dict[str, Any],
          confluence: dict[str, Any] | None = None,
          skill: dict[str, Any] | None = None,
          preview_note: str | None = None) -> str:
    confluence      = confluence or {}
    _s              = skill or {}
    project_name    = _s.get("project_name") or "Project"
    jira_project    = _s.get("jira_project") or ""
    user_first_name = _s.get("user_first_name") or "you"
    project_label   = f"{project_name} ({jira_project})" if jira_project else project_name
    pm              = set(_s.get("primary_metrics") or ["fta", "efficiency", "coq"])

    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%H:%M UTC")

    overall = "GREEN"
    if jira.get("sla_breaches") or analytics.get("fta_rag") == "RED" or analytics.get("efficiency_rag") == "RED":
        overall = "RED"
    elif jira.get("sla_warnings") or analytics.get("fta_rag") == "AMBER" or analytics.get("efficiency_rag") == "AMBER":
        overall = "AMBER"
    oc, obg, obd = _rag(overall)
    show_efficiency = bool(pm & {"efficiency", "coq", "copq"})

    # auto-numbering
    n = [0]
    def sec(title, content, accent="#1B2A4A"):
        if not content or not content.strip():
            return ""
        n[0] += 1
        return _section(title, content, n[0])

    return f"""<html>
<body style="margin:0;padding:0;background:#DDE3EA">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#DDE3EA">
<tr><td align="center" style="padding:20px 10px">
<table width="640" cellpadding="0" cellspacing="0"
       style="background:{_WHITE};border-radius:6px;border:1px solid {_BORDER}">
<tr><td>

  <!-- Header -->
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="background:{_HDR};padding:20px 22px 14px">
        <span style="{_F};font-size:18px;font-weight:bold;color:#fff">Daily Operational Briefing</span><br>
        <span style="{_F};font-size:12px;color:#8FA3C0;display:block;margin-top:3px">
          {project_label} &nbsp;·&nbsp; {date_str} &nbsp;·&nbsp; {time_str}
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

    {_preview_banner(preview_note) if preview_note else ""}

    {_build_kpi_row(analytics, jira, pm)}

    {sec("Priority Attention",
         _build_priority(jira, analytics, jira_project, project_name, list(pm)))}

    {sec(f"{jira_project} Sprint Health" if jira_project else "Sprint Health",
         _build_sprint(jira, jira_project))}

    {sec(f"Quality — FTA ({project_name})",
         _build_fta(analytics, jira_project)) if "fta" in pm else ""}

    {sec("Efficiency &amp; Cost of Quality",
         _build_efficiency(analytics)) if show_efficiency else ""}

    {sec(f"Process-type Breakdown — Week {analytics.get('week_label','')}",
         _build_breakdown(analytics))}

    {sec(f"Open {jira_project} Tickets" if jira_project else "Open Tickets",
         _build_tickets(jira))}

    {sec("Confluence — Progress Page",
         _build_confluence(confluence))}

    {sec("Suggested Actions",
         _build_actions(jira, analytics, jira_project, project_name, list(pm)))}

  </td></tr>
  </table>

  <!-- Footer -->
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="background:{_SEC};border-top:1px solid {_BORDER};
                 padding:10px 20px;border-radius:0 0 6px 6px">
    <span style="{_F};font-size:11px;color:{_MUTED}">
      UC1 Daily Briefing Agent &nbsp;·&nbsp; Jira {jira_project} · Databricks · Confluence
      &nbsp;&nbsp;—&nbsp;&nbsp;
      <b>All draft actions require {user_first_name}'s approval before sending.</b>
    </span>
  </td></tr>
  </table>

</td></tr>
</table>
</td></tr>
</table>
</body></html>"""


# ── UC4 compact alert email ────────────────────────────────────────────────────

def build_alert(
    metric: str,                   # "fta" | "coq"
    rag: str,                      # "RED" | "AMBER"
    current_value: float,
    threshold: float,
    direction: str,                # "improving" | "stable" | "declining"
    week_label: str,
    process_breakdown: list[dict],
    skill: dict[str, Any] | None = None,
    preview_note: str | None = None,
) -> str:
    """Compact HTML email for UC4 real-time quality alerts."""
    _s           = skill or {}
    project_name = _s.get("project_name") or "Project"
    jira_project = _s.get("jira_project") or ""
    user_name    = _s.get("user_first_name") or "you"
    proj_label   = f"{project_name} ({jira_project})" if jira_project else project_name

    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %d %B %Y · %H:%M UTC")

    c, bg, bd = _rag(rag)

    is_fta = metric == "fta"
    metric_label  = "FTA — First Time Accuracy" if is_fta else "CoQ — Cost of Quality"
    value_str     = f"{current_value:.2f}%"
    thr_label     = f"Below {threshold:.0f}%" if is_fta else f"Above {threshold:.0f}%"
    direction_bad = direction == "declining" if is_fta else direction == "improving"
    dir_note      = f"{_arrow(direction)} {direction.capitalize()}"
    if direction_bad:
        dir_note += " ⚠️"

    # Suggested action based on metric
    if is_fta:
        action = (
            f"Review process types with low FTA below. "
            f"Cross-reference {jira_project} Jira for quality-labelled tickets and rework spikes."
            if jira_project else
            "Review process type breakdown for rejection patterns and rework spikes."
        )
    else:
        action = (
            f"Review rework patterns for week {week_label}. "
            f"Identify which process types are driving high CoQ and whether FTA is also declining."
        )

    # Flagged process types for this alert
    if is_fta:
        flagged = [p for p in process_breakdown if p.get("fta_rag") in ("AMBER", "RED")][:5]
        if not flagged and process_breakdown:
            # No AMBER/RED rows (e.g. force mode) — show worst 5 by lowest FTA
            flagged = sorted(process_breakdown, key=lambda p: p.get("fta_pct", 100))[:5]
    else:
        flagged = sorted(process_breakdown, key=lambda p: p.get("coq_pct", 0), reverse=True)[:5]

    # Build flagged process table
    if flagged:
        if is_fta:
            proc_rows = [
                [f'<span style="{_F};font-size:12px;font-family:Consolas,monospace">{p["process_type"]}</span>',
                 f'<span style="{_F};font-size:12px;color:{_rag(p["fta_rag"])[0]};font-weight:bold">{p["fta_pct"]:.2f}%</span>',
                 f'<span style="{_F};font-size:12px">{p["coq_pct"]:.1f}%</span>',
                 f'<span style="{_F};font-size:12px">{p["total_hrs"]:.0f}h</span>']
                for p in flagged
            ]
            proc_table = _data_table(["Process Type", "FTA", "CoQ", "Hrs"], proc_rows)
        else:
            proc_rows = [
                [f'<span style="{_F};font-size:12px;font-family:Consolas,monospace">{p["process_type"]}</span>',
                 f'<span style="{_F};font-size:12px;color:{_rag(p["fta_rag"])[0]};font-weight:bold">{p["fta_pct"]:.2f}%</span>',
                 f'<span style="{_F};font-size:12px;font-weight:bold;color:#922B21">{p["coq_pct"]:.1f}%</span>',
                 f'<span style="{_F};font-size:12px">{p["total_hrs"]:.0f}h</span>']
                for p in flagged
            ]
            proc_table = _data_table(["Process Type", "FTA", "CoQ", "Hrs"], proc_rows)
    else:
        proc_table = f'<p style="{_F};font-size:12px;color:{_MUTED}">No process-type breakdown available.</p>'

    preview_html = _preview_banner(preview_note) if preview_note else ""

    return f"""<html>
<body style="margin:0;padding:0;background:#DDE3EA">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#DDE3EA">
<tr><td align="center" style="padding:20px 10px">
<table width="600" cellpadding="0" cellspacing="0"
       style="background:{_WHITE};border-radius:6px;border:1px solid {_BORDER}">
<tr><td>

  <!-- Header -->
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td style="background:{_HDR};padding:16px 22px 12px">
      <span style="{_F};font-size:15px;font-weight:bold;color:#fff">&#9888; UC4 — Quality Alert</span><br>
      <span style="{_F};font-size:11px;color:#8FA3C0;margin-top:3px;display:block">
        {proj_label} &nbsp;·&nbsp; {date_str}
      </span>
    </td>
    <td style="background:{_HDR};padding:16px 22px;text-align:right;vertical-align:middle">
      <span style="{_F};font-size:20px;font-weight:bold;color:{c}">&#9679; {rag.replace('_',' ')}</span>
    </td>
  </tr>
  </table>

  <!-- Alert banner -->
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="background:{bg};border-bottom:3px solid {c};padding:18px 22px">
    <div style="{_F};font-size:13px;font-weight:bold;color:{_MUTED};text-transform:uppercase;
                letter-spacing:0.5px;margin-bottom:6px">{metric_label}</div>
    <div style="{_F};font-size:36px;font-weight:bold;color:{c};line-height:1">{value_str}</div>
    <div style="{_F};font-size:13px;color:{_TEXT};margin-top:6px">
      Threshold: <b>{thr_label}</b> &nbsp;·&nbsp; Trend: <b>{dir_note}</b>
      &nbsp;·&nbsp; Week: <b>{week_label}</b>
    </div>
  </td></tr>
  </table>

  <!-- Body -->
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="padding:16px 20px">

    {preview_html}

    <!-- Key facts -->
    {_section("Alert Details", _kv_table([
        ("Metric",      metric_label,                                 _TEXT),
        ("Current",     f'<b style="color:{c}">{value_str}</b>',     c),
        ("Threshold",   thr_label,                                    _MUTED),
        ("Trend",       dir_note,                                     c if direction_bad else _GREEN),
        ("Data week",   week_label,                                   _MUTED),
    ]), 1)}

    <!-- Flagged process types -->
    {_section("Contributing Process Types", proc_table, 2)}

    <!-- Action -->
    {_section("Suggested Action", f'''
      <div style="{_F};font-size:13px;color:{_TEXT};line-height:1.6">
        {action}
      </div>
      <div style="{_F};font-size:11px;color:{_MUTED};margin-top:10px">
        All actions require {user_name}'s explicit approval before sending to others.
      </div>
    ''', 3)}

  </td></tr>
  </table>

  <!-- Footer -->
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="background:{_SEC};border-top:1px solid {_BORDER};
                 padding:8px 20px;border-radius:0 0 6px 6px">
    <span style="{_F};font-size:11px;color:{_MUTED}">
      UC4 Quality Alert · Databricks live data · Polling every 30 min during working hours
    </span>
  </td></tr>
  </table>

</td></tr>
</table>
</td></tr>
</table>
</body></html>"""
