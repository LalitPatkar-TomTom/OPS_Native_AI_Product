"""
HTML email formatter for UC1 Daily Briefing.
Clean single-column layout: proper tables, no multi-column cards.
Outlook-safe: table-based layout, inline CSS only.
"""
import html as _html
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode


# ── Untrusted text ─────────────────────────────────────────────────────────────
# Jira summaries, names and statuses, and Confluence titles are written by other people. They are
# HTML-escaped once, at the entry of each builder, so no markup or link from Jira can reach an email
# sent from the shared mailbox. _btn() unescapes them again for the plain-text Jira create link.
_TICKET_TEXT = ("key", "summary", "status", "priority", "assignee", "reporter")


def _sla_word(status: str) -> str:
    """Badge text. The status names carry 72H / 48H, but the hours now differ per profile (OSI-006)."""
    return {"BREACH_72H": "BREACH", "WARNING_48H": "WARNING"}.get(status, status.replace("_", " "))


def _escape_jira(jira: dict | None) -> dict:
    """Copy of the Jira agent output with every ticket's text fields HTML-escaped."""
    if not jira:
        return jira or {}
    out = dict(jira)
    for k in ("open_tickets", "sla_breaches", "sla_warnings"):
        if isinstance(jira.get(k), list):
            out[k] = [{**t, **{f: _html.escape(str(t[f])) for f in _TICKET_TEXT if t.get(f) is not None}}
                      if isinstance(t, dict) else t for t in jira[k]]
    return out


def _escape_confluence(confluence: dict | None) -> dict:
    """Copy of the Confluence agent output with page titles and the error text HTML-escaped."""
    if not confluence:
        return confluence or {}
    out = dict(confluence)
    if isinstance(confluence.get("pages"), list):
        out["pages"] = [{**p, "page_title": _html.escape(str(p.get("page_title", "(untitled)")))}
                        if isinstance(p, dict) else p for p in confluence["pages"]]
    if confluence.get("error"):
        out["error"] = _html.escape(str(confluence["error"]))
    return out

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


def week_word(week_label: str, today: "date | None" = None) -> str:
    """'this week', 'last week' or 'latest week with data' for the reported week, seen from today."""
    from datetime import date as _date, timedelta as _td
    try:
        mon = _date.fromisoformat(str(week_label)[:10])
    except ValueError:
        return "this week"
    today = today or _date.today()
    this_mon = today - _td(days=today.weekday())
    if mon >= this_mon:
        return "this week"
    return "last week" if mon == this_mon - _td(days=7) else "latest week with data"


def period_label(week_label: str, today: "date | None" = None, relative: bool = True,
                 fallback_note: "bool | str" = False) -> str:
    """Which days the numbers cover (OSI-031), decided with the user on 26 Oct.

    The data is one row per calendar week. The daily emails report the week of the previous working day:
      Monday         -> last week, full range:            'Mon 19 Oct – Sun 25 Oct 2026 (last week)'
      Tuesday–Sunday -> this week from Monday to today:   'Mon 26 Oct – Tue 27 Oct 2026 (this week so far)'
    The table has no day column, so "so far" ends at today, not at the last day loaded.
    relative=False gives the full Mon–Sun dates only. fallback_note=True (UC4) says why an earlier week is
    shown: alerts use this week and fall back only while it has no QC data. Non-dates come back unchanged.
    """
    from datetime import date as _date, timedelta as _td
    try:
        mon = _date.fromisoformat(str(week_label)[:10])
    except ValueError:
        return str(week_label or "")
    sun = mon + _td(days=6)
    if not relative:
        return f"{mon:%a %d %b} – {sun:%a %d %b %Y}"
    today = today or _date.today()
    word = week_word(week_label, today)
    if word == "this week":
        return f"{mon:%a %d %b} – {min(today, sun):%a %d %b %Y} (this week so far)"
    note = fallback_note if isinstance(fallback_note, str) else (" · no QC data yet this week" if fallback_note else "")
    return f"{mon:%a %d %b} – {sun:%a %d %b %Y} ({word}{note})"


def alert_week_note(analytics: dict | None) -> str:
    """Why a UC4 alert shows last week: this week has no QC data yet, or too little to judge."""
    ew = (analytics or {}).get("early_week")
    if ew:
        return f" · this week too early: {ew['qc']:,} QC&apos;d so far, alerts use it from {ew['needed']:,}"
    return " · no QC data yet this week"


def previous_full_week(analytics: dict) -> dict | None:
    """The week before the one reported, from metrics_4w (newest first), when the current week is row 0.

    The daily emails report the week in progress; early in the week that is a small sample, so the
    previous full week is shown next to it as a reference (decided 26 Oct, OSI-028/032/036).
    """
    m4 = (analytics or {}).get("metrics_4w") or []
    wk = str((analytics or {}).get("week_label", ""))[:10]
    if len(m4) < 2 or str(m4[0].get("week", ""))[:10] != wk:
        return None
    return m4[1]


_REF_FIELDS = {  # metric -> (metrics_4w field, label, format)
    "fta":        ("fta",              "FTA",        "{:.2f}%"),
    "efficiency": ("efficiency_vs_bl", "Eff vs BL",  "{:.1f}%"),
    "coq":        ("coq",              "CoQ",        "{:.2f}%"),
    "yield":      ("yield",            "Yield",      "{:.2f}%"),
}


def _reference_row(analytics: dict, metrics: list[str]) -> tuple | None:
    """('Previous full week', 'Mon 12 Oct – Sun 18 Oct 2026: FTA 97.64% · … (381 QC'd tasks) …', colour)."""
    prev = previous_full_week(analytics)
    if prev is None:
        return None
    parts = []
    for m in metrics:
        field, label, fmt = _REF_FIELDS[m]
        if prev.get(field) is not None:
            parts.append(f"{label} <b>{fmt.format(prev[field])}</b>")
    if not parts:
        return None
    cur_qc = ((analytics.get("metrics_4w") or [{}])[0]).get("qc_tasks")
    text = (f"{period_label(prev['week'], relative=False)}: " + " &nbsp;·&nbsp; ".join(parts)
            + (f" &nbsp;<span style=\"{_F};font-size:11px;color:{_MUTED}\">({prev['qc_tasks']:,} QC&apos;d tasks)</span>"
               if prev.get("qc_tasks") else ""))
    if cur_qc is not None:
        wk = analytics.get("week_label", "")
        shown = ("This week so far" if week_word(wk) == "this week"
                 else f"{week_word(wk).capitalize()} ({period_label(wk, relative=False)})")
        text += (f'<br><span style="{_F};font-size:11px;color:{_MUTED}">{shown}: {cur_qc:,} QC&apos;d tasks'
                 + (" — a small sample, compare with the previous full week" if cur_qc < 50 else "") + "</span>")
    return ("Previous full week (reference)", text, _MUTED)


# ── "Action needed": what to do, and why, from the data ─────────────────────────
# Every item names the action and its likely root cause: which process type / work unit drives the miss,
# how large the sample is, and how the previous full week compares. Shown at the top of UC1 and UC4.

def _n(x) -> str:
    return _html.escape(str(x or ""))


def _worst_wu(p: dict, key: str, reverse: bool) -> str:
    """' (mostly DPU Noida)' — the work unit that drives a process type's value, when there are several."""
    wus = [w for w in p.get("work_units") or [] if w.get(key) is not None and (w.get("total_qc") or w.get("total_hrs"))]
    if len(wus) < 2:
        return ""
    w = sorted(wus, key=lambda w: w[key], reverse=reverse)[0]
    return f", mostly {_n(w.get('work_unit'))}"


def _cause_fta(analytics: dict) -> str:
    bd = [p for p in analytics.get("process_breakdown") or [] if (p.get("total_qc") or 0) > 0]
    rej = sorted(bd, key=lambda p: p["total_qc"] * (100 - (p.get("fta_pct") or 100)), reverse=True)
    top = [p for p in rej if (p.get("fta_pct") or 100) < 100][:2]
    if not top:
        return "No single process type stands out."
    parts = [f"<b>{_n(p['process_type'])}</b> (FTA {p['fta_pct']:.2f}% on {p['total_qc']:,} QC&apos;d{_worst_wu(p, 'fta_pct', False)})"
             for p in top]
    return "Most rejections come from " + " and ".join(parts) + "."


def _cause_eff(analytics: dict) -> str:
    bd = [p for p in analytics.get("process_breakdown") or [] if p.get("eff_vs_bl") is not None and p.get("has_prod", True)]
    low = sorted(bd, key=lambda p: p["eff_vs_bl"])[:2]
    if not low:
        return "No process type has a baseline to compare with."
    parts = [f"<b>{_n(p['process_type'])}</b> ({p['eff_vs_bl']:.1f}% of baseline, {p.get('total_hrs') or 0:,.0f} h)" for p in low]
    return "Lowest against baseline: " + " and ".join(parts) + "."


def _cause_coq(analytics: dict) -> str:
    bd = [p for p in analytics.get("process_breakdown") or [] if (p.get("total_hrs") or 0) > 0]
    # biggest QC-hour share first: CoQ % x hours
    hi = sorted(bd, key=lambda p: (p.get("coq_pct") or 0) * p["total_hrs"], reverse=True)[:2]
    if not hi:
        return "No process type stands out."
    parts = [f"<b>{_n(p['process_type'])}</b> (CoQ {p.get('coq_pct') or 0:.1f}% of {p['total_hrs']:,.0f} h{_worst_wu(p, 'coq_pct', True)})" for p in hi]
    return "Most QC hours go to " + " and ".join(parts) + "."


def _sample_note(analytics: dict, metric: str) -> str:
    """Small sample this week: say so, with the previous full week as the reference."""
    m4 = analytics.get("metrics_4w") or [{}]
    cur_qc = (m4[0] or {}).get("qc_tasks")
    prev = previous_full_week(analytics)
    field = _REF_FIELDS.get(metric, (None,))[0]
    ref = ""
    if prev and field and prev.get(field) is not None:
        ref = f" The previous full week was {_REF_FIELDS[metric][2].format(prev[field])}."
    if cur_qc is not None and cur_qc < 50:
        if week_word(analytics.get("week_label", "")) == "this week":
            return f" Only {cur_qc:,} QC&apos;d tasks so far this week, so this can still move.{ref}"
        return f" Only {cur_qc:,} QC&apos;d tasks in that week, a small sample.{ref}"
    return ref


def action_items(jira: dict, analytics: dict, pm: set, only: str | None = None) -> list[tuple[str, str, str]]:
    """[(rag, action, why)] for everything that needs someone to act; `only` limits it to one metric (UC4)."""
    items = []
    jira = jira or {}
    br = jira.get("sla_breaches") or []
    if br and only is None:
        oldest = max(br, key=lambda t: float(t.get("hours_stale") or 0))
        esc = jira.get("sla_escalation_hours", 72)
        items.append(("RED", f"Follow up on {len(br)} Jira ticket(s) past the SLA, oldest first",
                      f"No update for more than {esc:g} h. Oldest: <b>{_n(oldest.get('key'))}</b> "
                      f"({_n(oldest.get('assignee'))}, {float(oldest.get('hours_stale') or 0):,.0f} h without an update)."))
    want = (lambda m: m == only) if only else (lambda m: m in pm or not pm)
    fr = analytics.get("fta_rag", "GREEN")
    if want("fta") and fr in ("RED", "AMBER") and analytics.get("live", True):
        items.append((fr, f"Review the rejected tasks behind FTA {analytics.get('fta_current', 0):.2f}% with the QC lead "
                          "and brief the editors on the top error types",
                      _cause_fta(analytics) + _sample_note(analytics, "fta")))
    er, ev = analytics.get("efficiency_rag", "GREEN"), analytics.get("efficiency_vs_bl")
    if want("efficiency") and er in ("RED", "AMBER") and ev is not None:
        items.append((er, f"Check the slowest process types for blockers (tools, data, new editors) — efficiency is "
                          f"{ev:.1f}% of baseline",
                      _cause_eff(analytics) + _sample_note(analytics, "efficiency")))
    cr = analytics.get("coq_rag", "GREEN")
    if (want("coq") or (only is None and "copq" in pm)) and cr not in ("GREEN", None):
        items.append(("RED" if cr == "RED" else "AMBER",
                      f"Find where QC and rework time goes — CoQ is {analytics.get('coq_current', 0):.2f}%; "
                      "check for over-sampling or repeated rework",
                      _cause_coq(analytics) + _sample_note(analytics, "coq")))
    yr, yv = analytics.get("yield_rag", "GREEN"), analytics.get("yield_current")
    if want("yield") and yr in ("RED", "AMBER") and yv is not None:
        items.append((yr, f"Check first-pass completion — yield is {yv:.2f}%",
                      "Yield counts tasks finished without going back to production." + _sample_note(analytics, "yield")))
    return items


def _build_action_box(jira: dict, analytics: dict, pm: set, only: str | None = None) -> str:
    """The highlighted box; empty when nothing needs action."""
    items = action_items(jira, analytics, pm, only)
    if not items:
        return ""
    worst = "RED" if any(r == "RED" for r, _, _ in items) else "AMBER"
    c, bg, bd = _rag(worst)
    rows = "".join(
        f'<tr><td style="padding:7px 0;border-top:1px solid {bd}">'
        f'<div style="{_F};font-size:13px;color:{_TEXT};font-weight:bold">{_dot(r)} {i}. {a}</div>'
        f'<div style="{_F};font-size:12px;color:{_TEXT};margin:3px 0 0 18px;line-height:1.5">'
        f'<span style="color:{_MUTED};font-weight:bold">Why: </span>{w}</div></td></tr>'
        for i, (r, a, w) in enumerate(items, 1))
    return (f'<table width="100%" cellpadding="0" cellspacing="0" style="background:{bg};border:1px solid {bd};'
            f'border-left:5px solid {c};border-radius:4px;margin:0 0 14px">'
            f'<tr><td style="padding:10px 14px">'
            f'<div style="{_F};font-size:14px;font-weight:bold;color:{c};margin-bottom:4px">'
            f'&#9888; Recommended actions ({len(items)})</div>'
            f'<table width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
            f'<div style="{_F};font-size:11px;color:{_MUTED};margin-top:6px">Root causes are worked out from this '
            f'week&apos;s data by process type and work unit; details are in the sections below.</div>'
            f'</td></tr></table>')


ONBOARDING_URL = "https://tomtom-ops-hub.bravewave-803863cf.westeurope.azurecontainerapps.io/onboarding"


def no_scope_notice(skill: dict | None) -> str:
    """Shown instead of all quality/efficiency figures when the profile has no Databricks scope."""
    if not (skill or {}).get("no_databricks_scope"):
        return ""
    c, bg, bd = _rag("AMBER")
    return (f'<table width="100%" cellpadding="0" cellspacing="0" style="background:{bg};border:1px solid {bd};'
            f'border-left:5px solid {c};border-radius:4px;margin:0 0 14px"><tr><td style="padding:10px 14px">'
            f'<div style="{_F};font-size:14px;font-weight:bold;color:{c}">&#9888; Add your scope to see quality '
            f'and efficiency</div>'
            f'<div style="{_F};font-size:13px;color:{_TEXT};margin-top:4px;line-height:1.55">Your profile has no '
            f'<b>process types</b> or <b>planning IDs</b>, so FTA, efficiency, CoQ, yield and the breakdowns are '
            f'not shown: they would cover all of Maps Operations, not your work. Jira is not affected. '
            f'Please <a href="{ONBOARDING_URL}" style="color:#2563EB">update your profile in OPS Hub</a> and fill '
            f'in <i>Databricks Process Types</i> and/or <i>Planning IDs</i>; the next email will include them.</div>'
            f'</td></tr></table>')


def _eff_actual_vs_baseline(eff_raw: float | None, eff_vs_bl: float | None) -> str:
    """OSI-033: 'Actual 0.852 vs baseline 0.801 tasks/hr' — the % alone hid both numbers."""
    if not eff_raw or not eff_vs_bl:
        return ""
    return f"Actual {eff_raw:.3f} vs baseline {eff_raw * 100 / eff_vs_bl:.3f} tasks/hr"


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
    summary, description = _html.unescape(summary), _html.unescape(description)   # see _escape_jira
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
    """KPI summary at the top: the six headline KPIs (OSI-008) plus Jira SLA, four cells per row.

    Metrics in the profile get their RAG badge; the others say "no alert set" (they never alert).
    """
    cells = []
    neutral = _rag("NONE")

    def metric(label, value_str, rag, key, note=""):
        tracked = key in pm or (key == "coq" and "copq" in pm)
        c, bg, bd = _rag(rag) if tracked and not note else neutral
        sub = (f'<span style="{_F};font-size:11px;color:{_MUTED}">{note}</span>' if note
               else _badge(rag) if tracked else f'<span style="{_F};font-size:11px;color:{_MUTED}">no alert set</span>')
        cells.append((label, f'<span style="{_F};font-size:22px;font-weight:bold;color:{c if tracked else _TEXT}">'
                             f'{value_str}</span>', sub, bg, bd))

    if not analytics.get("no_scope"):
        ev, yv = analytics.get("efficiency_vs_bl"), analytics.get("yield_current")
        metric("FTA", f'{analytics.get("fta_current", 0.0):.2f}%', analytics.get("fta_rag", "GREEN"), "fta")
        metric("Efficiency vs BL", _eff_str(ev), analytics.get("efficiency_rag", "GREEN"), "efficiency")
        metric("Cost of Quality", f'{analytics.get("coq_current", 0.0):.2f}%', analytics.get("coq_rag", "GREEN"), "coq")
        metric("Yield", f"{yv:.2f}%" if yv is not None else "N/A", analytics.get("yield_rag", "GREEN"), "yield",
               note="Orbit SD work only" if yv is None and analytics.get("yield_note") else "")
        ph, qh = analytics.get("prod_hrs") or 0, analytics.get("qc_hrs") or 0
        cells.append(("Hours", f'<span style="{_F};font-size:22px;font-weight:bold;color:{_TEXT}">{ph + qh:,.0f}h</span>',
                      f'<span style="{_F};font-size:11px;color:{_MUTED}">production {ph:,.0f}h · QC {qh:,.0f}h</span>',
                      *neutral[1:]))
        sp = analytics.get("sampling_pct")
        cells.append(("Sampling", f'<span style="{_F};font-size:22px;font-weight:bold;color:{_TEXT}">'
                                  f'{f"{sp:.1f}%" if sp is not None else "N/A"}</span>',
                      f'<span style="{_F};font-size:11px;color:{_MUTED}">{analytics.get("total_qc") or 0:,} QC&apos;d of '
                      f'{analytics.get("prod_tasks") or 0:,} tasks</span>', *neutral[1:]))

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

    rows = ""
    for start in range(0, len(cells), 4):
        chunk = cells[start:start + 4]
        tds = ""
        for i, (label, big, sub, bg, bd) in enumerate(chunk):
            pad = "padding-left:8px" if i else ""
            tds += (
                f'<td width="25%" style="{pad};vertical-align:top">'
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
        tds += '<td width="25%"></td>' * (4 - len(chunk)) if start else ""
        rows += f'<tr>{tds}</tr>'
    return (
        f'<table width="100%" cellpadding="0" cellspacing="8" style="margin-bottom:18px">'
        f'{rows}</table>'
    )


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
                sp = p.get("sampling_pct")
                sp_str = f'{sp:.1f}%' if sp is not None else 'N/A'
                items.append(_alert_row(p["fta_rag"], "FTA CONCERN",
                    f'<b>{p["process_type"]}</b> — FTA <b>{p["fta_pct"]:.2f}%</b> · '
                    f'Eff vs BL <b>{_eff_str(p.get("eff_vs_bl"))}</b> · '
                    f'CoQ <b>{p["coq_pct"]:.1f}%</b> · '
                    f'Sampling <b>{sp_str}</b>{b}', f'Week {wk}'))

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
        """One KPI tile (large value, label) coloured by its RAG status."""
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
        (f"FTA {week_word(wk)}",
         f'{_dot(rag)} <span style="font-size:18px;font-weight:bold;color:{c}">{fta:.2f}%</span>'
         f' &nbsp; {_badge(rag)}', c),
        ("4-week trend",    trend_str, _TEXT),
        ("Trend direction", f'{_arrow(tr)} {tr.capitalize()}', c),
        ("Data period",     period_label(wk), _MUTED),
    ]
    ref = _reference_row(analytics, ["fta"])
    if ref:
        rows.append(ref)
    rows += [
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


def _build_efficiency(analytics, pm=None):
    ev  = analytics.get("efficiency_vs_bl")
    er  = analytics.get("efficiency_raw")
    erg = analytics.get("efficiency_rag", "GREEN")
    cq  = analytics.get("coq_current",   0.0)
    crg = analytics.get("coq_rag",       "GREEN")
    ch  = analytics.get("copq_hrs")
    cp  = analytics.get("copq_pct")
    ph  = analytics.get("prod_hrs")
    qh  = analytics.get("qc_hrs")
    sp  = analytics.get("sampling_pct")
    pt  = analytics.get("prod_tasks")
    tq  = analytics.get("total_qc")
    yv  = analytics.get("yield_current")
    yr  = analytics.get("yield_rag", "GREEN")
    wk  = analytics.get("week_label",    "")
    ec, _, _ = _rag(erg)
    cc, _, _ = _rag(crg)
    _pm = set(pm) if pm is not None else set()

    coq_label = (
        "Healthy &lt;5%"       if cq < 5  else
        "P3 Monitor 5–7%"      if cq < 7  else
        "P2 Investigate 7–10%" if cq < 10 else
        "P1 Escalate &gt;10%"
    )
    eff_sub = (f'<br><span style="{_F};font-size:11px;color:{_MUTED}">{_eff_actual_vs_baseline(er, ev)} '
               f'(baseline = average of the process types in scope)</span>' if er and ev else "")
    copq_sub = ""
    if ch is not None:
        copq_sub = f' &nbsp;·&nbsp; CopQ: {ch:.1f}h rework ({cp:.2f}% of hrs)' if cp else f' &nbsp;·&nbsp; CopQ: {ch:.1f}h rework'

    rows = []
    if _pm & {"efficiency"} or not _pm:
        rows.append(("Efficiency vs Baseline",
             f'{_dot(erg)} <span style="font-size:18px;font-weight:bold;color:{ec}">'
             f'{_eff_str(ev)}</span> &nbsp; {_badge(erg)}{eff_sub}', ec))
    if _pm & {"coq", "copq"} or not _pm:
        rows.append(("Cost of Quality (CoQ)",
             f'{_dot(crg)} <span style="font-size:18px;font-weight:bold;color:{cc}">'
             f'{cq:.2f}%</span> &nbsp; {_badge(crg, coq_label)}{copq_sub}', cc))
    if "yield" in _pm and yv is not None:
        yc, _, _ = _rag(yr)
        rows.append(("Yield (First-Pass)",
             f'{_dot(yr)} <span style="font-size:18px;font-weight:bold;color:{yc}">'
             f'{yv:.2f}%</span> &nbsp; {_badge(yr)}', yc))
    if sp is not None:
        sp_detail = f' &nbsp;<span style="{_F};font-size:11px;color:{_MUTED}">({tq:,} QC&apos;d / {pt:,} produced)</span>' if pt and tq else ""
        rows.append(("Sampling Rate",
                     f'<span style="font-size:18px;font-weight:bold;color:{_TEXT}">'
                     f'{sp:.1f}%</span>{sp_detail}', _TEXT))
    if ph is not None and qh is not None:
        total = ph + qh
        rows.append(("Hours breakdown",
                     f'Production <b>{ph:.0f}h</b> &nbsp;·&nbsp; '
                     f'QC <b>{qh:.0f}h</b> &nbsp;·&nbsp; Total <b>{total:.0f}h</b>', _TEXT))
    rows.append(("Data period", period_label(wk), _MUTED))
    ref = _reference_row(analytics, [m for m in ("efficiency", "coq", "yield")
                                     if m in _pm or (not _pm and m != "yield") or (m == "coq" and "copq" in _pm)])
    if ref:
        rows.append(ref)
    return _kv_table(rows)


def _build_operator_breakdown(analytics):
    """Per-operator metrics table, grouped by process type."""
    ops = analytics.get("operator_breakdown", [])
    wk  = analytics.get("week_label", "")
    if not ops:
        return f'<p style="{_F};font-size:13px;color:{_MUTED}">No operator data available.</p>'

    # group by process type preserving order
    from collections import OrderedDict
    by_pt: OrderedDict = OrderedDict()
    for o in ops:
        pt = o["process_type"]
        by_pt.setdefault(pt, []).append(o)

    th = (f'{_F};font-size:11px;font-weight:bold;color:{_WHITE};background:{_HDR};'
          f'padding:5px 8px;text-align:left;border-bottom:2px solid {_BORDER}')
    td_e = (f'{_F};font-size:11px;color:{_TEXT};padding:5px 8px;'
            f'background:{_WHITE};border-bottom:1px solid {_BORDER}')
    td_o = (f'{_F};font-size:11px;color:{_TEXT};padding:5px 8px;'
            f'background:{_STRIPE};border-bottom:1px solid {_BORDER}')
    sep = (f'{_F};font-size:10px;font-weight:bold;color:{_WHITE};'
           f'background:#374151;padding:4px 8px;letter-spacing:0.3px')

    headers = ["Operator", "FTA", "Eff vs BL", "CoQ", "Sampling", "Tasks", "QC"]
    html = (f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;border:1px solid {_BORDER};border-radius:4px;font-size:11px">'
            f'<tr>' + ''.join(f'<th style="{th}">{h}</th>' for h in headers) + '</tr>')

    for pt, rows in by_pt.items():
        html += f'<tr><td colspan="7" style="{sep}">&#9656;&nbsp; {pt}</td></tr>'
        for i, o in enumerate(rows):
            td = td_e if i % 2 == 0 else td_o
            fta = o["fta_pct"]
            fta_c, _, _ = _rag(o["fta_rag"])
            fta_cell = f'<span style="{_F};font-size:11px;color:{fta_c};font-weight:600">{fta:.2f}%</span>'

            ev = o.get("eff_vs_bl")
            ev_cell = _eff_str(ev) if ev is not None else ("—" if not o.get("has_prod", True) else "N/A")
            if ev is not None:
                ev_rag = "GREEN" if ev >= 100 else "AMBER" if ev >= 90 else "RED"
                ev_c, _, _ = _rag(ev_rag)
                ev_cell = f'<span style="{_F};font-size:11px;color:{ev_c};font-weight:600">{ev_cell}</span>'
            else:
                ev_cell = f'<span style="{_F};font-size:11px;color:{_MUTED}">{ev_cell}</span>'

            coq = o.get("coq_pct", 0)
            coq_rag = "GREEN" if coq < 7 else "AMBER" if coq < 10 else "RED"
            coq_c, _, _ = _rag(coq_rag)
            coq_cell = f'<span style="{_F};font-size:11px;color:{coq_c};font-weight:600">{coq:.1f}%</span>'

            sp = o.get("sampling_pct")
            sp_str = f'{sp:.1f}%' if sp is not None else '—'

            html += ('<tr>'
                + f'<td style="{td};font-family:Consolas,monospace">{o["operator"]}</td>'
                + f'<td style="{td}">{fta_cell}</td>'
                + f'<td style="{td}">{ev_cell}</td>'
                + f'<td style="{td}">{coq_cell}</td>'
                + f'<td style="{td};text-align:right;color:{_MUTED}">{sp_str}</td>'
                + f'<td style="{td};text-align:right">{o["prod_tasks"]:,}</td>'
                + f'<td style="{td};text-align:right;color:{_MUTED}">{o["total_qc"]:,}</td>'
                + '</tr>')

    html += '</table>'
    html += (f'<p style="{_F};font-size:10px;color:{_MUTED};margin:5px 0 0">'
             f'Operator-level metrics (Production_Editor) — {period_label(wk)} — '
             f'Only operators with QC data shown. FTA = first-pass acceptance rate per operator.</p>')
    return html


def _fta_order(p):
    """Worst FTA first; rows too small to judge ("SMALL", < 10 QC'd) go last."""
    return (p.get("fta_rag") == "SMALL", p.get("fta_pct", 100))


def flagged(rows):
    """Rows whose FTA is AMBER or RED (small samples are never flagged)."""
    return [p for p in rows or [] if p.get("fta_rag") in ("AMBER", "RED")]


def _build_breakdown(analytics, scope_mode="defined"):
    bd  = analytics.get("process_breakdown", [])
    wk  = analytics.get("week_label", "")
    sc  = analytics.get("scope_label", "")

    if not bd:
        return f'<p style="{_F};font-size:13px;color:{_MUTED}">No process data for this period.</p>'

    many = len(bd) > 15

    if scope_mode == "all" or (scope_mode.startswith("keyword") and many):
        display_groups = [("Top 10 by Volume", sorted(bd, key=lambda p: p.get("total_hrs", 0), reverse=True)[:10])]
        mode_note = f"Top 10 process types by volume (of {len(bd)} total)"
    elif many:
        by_fta   = sorted(bd, key=_fta_order)
        bottom10 = by_fta[:10]
        top10    = list(reversed(by_fta[-10:]))
        display_groups = [
            ("Needs Attention — Bottom 10 by FTA", bottom10),
            ("Top Performers — Top 10 by FTA",     top10),
        ]
        mode_note = f"Top & bottom 10 of {len(bd)} total"
    else:
        # All configured process types, worst FTA first
        display_groups = [("", sorted(bd, key=_fta_order))]
        mode_note = f"All {len(bd)} process type{'s' if len(bd) != 1 else ''} — sorted by FTA (worst first)"
    if any(p.get("fta_rag") == "SMALL" for p in bd):
        mode_note += " · grey FTA = fewer than 10 QC&apos;d tasks, not flagged"

    headers = ["Process Type", "FTA", "Eff vs BL", "CoQ", "Yield", "Sampling", "Tasks", "Hrs"]
    th = (f'{_F};font-size:11px;font-weight:bold;color:{_WHITE};background:{_HDR};'
          f'padding:6px 8px;text-align:left;border-bottom:2px solid {_BORDER}')
    td_e = (f'{_F};font-size:11px;color:{_TEXT};padding:6px 8px;'
            f'background:{_WHITE};border-bottom:1px solid {_BORDER}')
    td_o = (f'{_F};font-size:11px;color:{_TEXT};padding:6px 8px;'
            f'background:{_STRIPE};border-bottom:1px solid {_BORDER}')
    sep  = (f'{_F};font-size:10px;font-weight:bold;color:{_WHITE};'
            f'background:#374151;padding:4px 8px;letter-spacing:0.3px')

    tbl = (f'<table width="100%" cellpadding="0" cellspacing="0" '
           f'style="border-collapse:collapse;border:1px solid {_BORDER};border-radius:4px;font-size:11px">'
           f'<tr>' + ''.join(f'<th style="{th}">{h}</th>' for h in headers) + '</tr>')

    td_wu = (f'{_F};font-size:10px;color:{_MUTED};padding:3px 8px;'
             f'background:{_WHITE};border-bottom:1px dotted {_BORDER}')

    for group_label, group in display_groups:
        if group_label:
            tbl += f'<tr><td colspan="8" style="{sep}">&#9656;&nbsp; {group_label}</td></tr>'
        for i, p in enumerate(group):
            td = td_e if i % 2 == 0 else td_o
            wus = p.get("work_units") or []
            name = f'<span style="font-family:Consolas,monospace">{p["process_type"]}</span>'
            if len(wus) == 1:
                name += f'<br><span style="font-size:10px;color:{_MUTED}">{wus[0]["name"]}</span>'
            tbl += _metric_row(p, name, td)
            if len(wus) > 1:
                for w in wus:
                    tbl += _metric_row(w, f'&nbsp;&nbsp;&#8627; {w["name"]}', td_wu, small=True)

    tbl += '</table>'
    note = (f'<p style="{_F};font-size:10px;color:{_MUTED};margin:5px 0 0">'
            f'{mode_note}'
            + ' &nbsp;·&nbsp; &#8627; rows split a process type by work unit'
            + (f' &nbsp;·&nbsp; {sc}' if sc else '')
            + (f' &nbsp;·&nbsp; {period_label(wk)}' if wk else '')
            + '</p>')
    return _build_workunits(analytics) + tbl + note + _build_unsampled(analytics)


def _fta_cell(val, rag, size=11):
    c, bg, bd_c = _rag(rag)
    return (f'<span style="background:{bg};color:{c};border:1px solid {bd_c};'
            f'padding:2px 6px;border-radius:3px;font-weight:bold;font-size:{size}px;{_F}">'
            f'{val:.2f}%</span>')


def _eff_cell(ev, has_prod=True, size=11):
    if ev is None:
        # "—" = no production work done this week; "N/A" = work done but baseline lookup failed
        label = "N/A" if has_prod else "—"
        return f'<span style="{_F};font-size:{size}px;color:{_MUTED}">{label}</span>'
    rag = "GREEN" if ev >= 100 else "AMBER" if ev >= 90 else "RED"
    c, _, _ = _rag(rag)
    return f'<span style="{_F};font-size:{size}px;color:{c};font-weight:600">{_eff_str(ev)}</span>'


def _coq_cell(val, size=11):
    rag = "GREEN" if val < 7 else "AMBER" if val < 10 else "RED"
    c, _, _ = _rag(rag)
    return f'<span style="{_F};font-size:{size}px;color:{c};font-weight:600">{val:.1f}%</span>'


def _yield_cell(yp, size=11):
    if yp is None:
        return f'<span style="{_F};font-size:{size}px;color:{_MUTED}">—</span>'
    yr = "GREEN" if yp >= 95 else "AMBER" if yp >= 94 else "RED"
    yc, _, _ = _rag(yr)
    return f'<span style="{_F};font-size:{size}px;color:{yc};font-weight:600">{yp:.1f}%</span>'


def _metric_row(p, name_html, td, small=False):
    """One breakdown row: name, FTA, Eff vs BL, CoQ, Yield, Sampling, Tasks, Hrs."""
    size = 10 if small else 11
    sp = p.get("sampling_pct")
    sp_str = f'{sp:.1f}%' if sp is not None else '—'
    fta = (f'<span style="{_F};font-size:{size}px;color:{_rag(p["fta_rag"])[0]};font-weight:600">{p["fta_pct"]:.2f}%</span>'
           if small else _fta_cell(p["fta_pct"], p["fta_rag"]))
    return ('<tr>'
        + f'<td style="{td}">{name_html}</td>'
        + f'<td style="{td}">{fta}</td>'
        + f'<td style="{td}">{_eff_cell(p.get("eff_vs_bl"), p.get("has_prod", True), size)}</td>'
        + f'<td style="{td}">{_coq_cell(p.get("coq_pct", 0), size)}</td>'
        + f'<td style="{td};text-align:right">{_yield_cell(p.get("yield_pct"), size)}</td>'
        + f'<td style="{td};text-align:right;color:{_MUTED}">{sp_str}</td>'
        + f'<td style="{td};text-align:right">{p["prod_tasks"]:,}</td>'
        + f'<td style="{td};text-align:right">{p["total_hrs"]:.0f}h</td>'
        + '</tr>')


def _workunit_overall(analytics):
    """The scope-wide totals as a row shaped like a work-unit row."""
    hrs = (analytics.get("prod_hrs") or 0) + (analytics.get("qc_hrs") or 0)
    return {
        "fta_pct": analytics.get("fta_current") or 0.0,
        "fta_rag": analytics.get("fta_rag", "GREEN"),
        "eff_vs_bl": analytics.get("efficiency_vs_bl"),
        "coq_pct": analytics.get("coq_current") or 0.0,
        "yield_pct": analytics.get("yield_current"),
        "sampling_pct": analytics.get("sampling_pct"),
        "prod_tasks": int(analytics.get("prod_tasks") or 0),
        "total_hrs": hrs,
    }


def _build_workunits(analytics):
    """Overall + one row per work unit, across every process type in scope."""
    wus = analytics.get("workunit_breakdown") or []
    if not wus:
        return ''
    th = (f'{_F};font-size:11px;font-weight:bold;color:{_WHITE};background:{_HDR};'
          f'padding:6px 8px;text-align:left;border-bottom:2px solid {_BORDER}')
    def td(i):
        """Inline CSS for a table cell in row i (alternate rows striped)."""
        bg = _WHITE if i % 2 == 0 else _STRIPE
        return f'{_F};font-size:11px;color:{_TEXT};padding:6px 8px;background:{bg};border-bottom:1px solid {_BORDER}'
    tbl = (f'<p style="{_F};font-size:12px;font-weight:bold;color:{_TEXT};margin:0 0 6px">By work unit</p>'
           f'<table width="100%" cellpadding="0" cellspacing="0" '
           f'style="border-collapse:collapse;border:1px solid {_BORDER};font-size:11px"><tr>'
           + ''.join(f'<th style="{th}">{h}</th>' for h in
                     ("Work Unit", "FTA", "Eff vs BL", "CoQ", "Yield", "Sampling", "Tasks", "Hrs")) + '</tr>')
    tbl += _metric_row(_workunit_overall(analytics), '<b>Overall</b>', td(0) + ';border-bottom:2px solid ' + _BORDER)
    for i, w in enumerate(wus, start=1):
        tbl += _metric_row(w, w["name"], td(i))
    tbl += '</table>'
    note = (f'<p style="{_F};font-size:10px;color:{_MUTED};margin:5px 0 14px">'
            'All process types in your scope, split by the work unit that did the work. '
            '"Not assigned" = rows with no work unit in Databricks.</p>')
    return tbl + note


def _build_planning(analytics):
    """One row per Planning ID listed in the profile, plus the listed IDs with no data."""
    pl = analytics.get("planning_breakdown") or []
    missing = analytics.get("planning_missing") or []
    if not pl and not missing:
        return ''
    th = (f'{_F};font-size:11px;font-weight:bold;color:{_WHITE};background:{_HDR};'
          f'padding:6px 8px;text-align:left;border-bottom:2px solid {_BORDER}')
    def cell(i):
        """Inline CSS for a table cell in row i (alternate rows striped)."""
        bg = _WHITE if i % 2 == 0 else _STRIPE
        return f'{_F};font-size:11px;color:{_TEXT};padding:6px 8px;background:{bg};border-bottom:1px solid {_BORDER}'
    def coloured(text, rag):
        """Text in a bold span coloured by its RAG status (text is not escaped here)."""
        c, _, _ = _rag(rag)
        return f'<span style="color:{c};font-weight:600">{text}</span>'
    tbl = (f'<table width="100%" cellpadding="0" cellspacing="0" '
           f'style="border-collapse:collapse;border:1px solid {_BORDER};font-size:11px"><tr>'
           + ''.join(f'<th style="{th}">{h}</th>' for h in
                     ("Planning ID", "FTA", "Eff vs BL", "CoQ", "QC sampled", "Tasks", "Hrs")) + '</tr>')
    for i, r in enumerate(pl):
        td = cell(i)
        fta = coloured(f"{r['fta_pct']:.2f}%", r['fta_rag']) if r['fta_pct'] is not None else f'<span style="color:{_MUTED}">no QC</span>'
        ev = r['eff_vs_bl']
        eff = coloured(f'{ev:.1f}%', 'GREEN' if ev >= 100 else 'AMBER' if ev >= 90 else 'RED') if ev is not None else f'<span style="color:{_MUTED}">N/A</span>'
        cq = r['coq_pct']
        coq = coloured(f'{cq:.1f}%', 'GREEN' if cq < 7 else 'AMBER' if cq < 10 else 'RED')
        tbl += ('<tr>'
            + f'<td style="{td};font-family:Consolas,monospace">{r["planning_id"]}</td>'
            + f'<td style="{td}">{fta}</td><td style="{td}">{eff}</td><td style="{td}">{coq}</td>'
            + f'<td style="{td};text-align:right">{r["total_qc"]:,}</td>'
            + f'<td style="{td};text-align:right">{r["prod_tasks"]:,}</td>'
            + f'<td style="{td};text-align:right">{r["total_hrs"]:.0f}h</td></tr>')
    tbl += '</table>'
    note = ''
    if missing:
        note = (f'<p style="{_F};font-size:11px;color:{_MUTED};margin:6px 0 0"><b>No data in this period:</b> '
                + ', '.join(f'<span style="font-family:Consolas,monospace">{m}</span>' for m in missing) + '</p>')
    return (tbl if pl else '') + note


def _build_unsampled(analytics):
    """Process types with production but no QC sample this week (no FTA to show)."""
    un = analytics.get("unsampled_breakdown") or []
    if not un:
        return ''
    items = ' &nbsp;·&nbsp; '.join(
        f'<span style="font-family:Consolas,monospace">{u["process_type"]}</span> — '
        f'{u["prod_tasks"]:,} tasks, {u["total_hrs"]:.0f}h' for u in un)
    return (f'<p style="{_F};font-size:11px;color:{_MUTED};margin:6px 0 0">'
            f'<b>Produced but not QC-sampled in this period</b> (no FTA): {items}</p>')


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
            _badge(t["sla_status"], _sla_word(t["sla_status"])),
        ])
    return _data_table(headers, rows)


def _build_actions(jira, analytics, jira_project="", project_name="",
                   primary_metrics=None):
    """P0 / P1 / P2 prioritised actions with numbered items and conclusion."""
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

    p0, p1, p2 = [], [], []

    # ── P0: SLA breaches + RED overall FTA ────────────────────────────────────
    for t in br:
        b = _btn(f"SLA Breach: {t['key']} — {t['summary'][:60]}",
                 f"Ticket {t['key']} silent {t['hours_stale']}h. Owner: {t['assignee']}. "
                 f"Status: {t['status']}. Link: {t['url']}", jira_project, "High")
        d = round(t["hours_stale"] / 24, 1)
        p0.append(
            f'Follow up with <b>{t["assignee"]}</b> on '
            f'<a href="{t["url"]}" style="color:#2563EB">{t["key"]}</a>'
            f' — silent {d} days ({t["hours_stale"]}h), SLA breached.{b}'
        )

    if "fta" in pm and fr == "RED":
        b = _btn(f"FTA Alert: {prj} at {fv:.2f}%",
                 f"Overall FTA {fv:.2f}% ({ft}). Week {wk}.", jira_project, "High")
        p0.append(
            f'Overall FTA <b>{fv:.2f}%</b> is RED — investigate quality root causes immediately.{b}'
        )

    if "efficiency" in pm and erg == "RED" and ev is not None:
        b = _btn(f"Efficiency Alert: {prj} at {ev:.1f}% vs baseline",
                 f"Efficiency {ev:.1f}% of baseline, week {wk}.", jira_project, "High")
        p0.append(
            f'Efficiency <b>{_eff_str(ev)}</b> is RED — identify throughput bottlenecks '
            f'in low-performing process types for week {wk}.{b}'
        )

    yv  = analytics.get("yield_current")
    yrg = analytics.get("yield_rag", "GREEN")
    if "yield" in pm and yrg == "RED" and yv is not None:
        b = _btn(f"Yield Alert: {prj} at {yv:.2f}%",
                 f"First-pass yield {yv:.2f}% for week {wk}.", jira_project, "High")
        p0.append(
            f'Yield <b>{yv:.2f}%</b> is RED (target ≥95%) — review rework and resolution '
            f'patterns for week {wk}.{b}'
        )

    # ── P1: RED process types + RED CoQ ───────────────────────────────────────
    if "fta" in pm:
        for p in sorted(bd, key=lambda x: x.get("fta_pct", 100)):
            if p.get("fta_rag") == "RED":
                b = _btn(f"FTA: {p['process_type']} at {p['fta_pct']:.2f}%",
                         f"processType '{p['process_type']}' FTA {p['fta_pct']:.2f}%, "
                         f"CoQ {p['coq_pct']:.1f}%, week {wk}.", jira_project, "High")
                p1.append(
                    f'<span style="font-family:Consolas,monospace;font-size:11px">'
                    f'{p["process_type"]}</span> — FTA <b>{p["fta_pct"]:.2f}%</b> (RED),'
                    f' CoQ <b>{p["coq_pct"]:.1f}%</b>. Review rejection patterns.{b}'
                )

    if "coq" in pm and crg in ("RED_P1", "RED"):
        cn = f' CopQ: {ch:.1f}h rework.' if ch else ''
        b = _btn(f"CoQ: {prj} at {cq:.2f}%",
                 f"CoQ {cq:.2f}% for week {wk}." + (f" Rework: {ch:.1f}h." if ch else ""),
                 jira_project, "High")
        p1.append(
            f'CoQ at <b>{cq:.2f}%</b> (RED) — audit rework root causes for week {wk}.{cn}{b}'
        )

    # ── P2: AMBER metrics + SLA warnings ──────────────────────────────────────
    if "fta" in pm and fr == "AMBER":
        b = _btn(f"FTA Review: {prj} at {fv:.2f}%",
                 f"Overall FTA {fv:.2f}% ({ft}). Week {wk}.", jira_project, "Medium")
        p2.append(
            f'Overall FTA <b>{fv:.2f}%</b> is AMBER — monitor trend; cross-check '
            f'quality-labelled tickets in {jira_project or prj}.{b}'
        )

    if "fta" in pm:
        for p in sorted(bd, key=lambda x: x.get("fta_pct", 100)):
            if p.get("fta_rag") == "AMBER":
                b = _btn(f"FTA: {p['process_type']} at {p['fta_pct']:.2f}%",
                         f"processType '{p['process_type']}' FTA {p['fta_pct']:.2f}%, "
                         f"CoQ {p['coq_pct']:.1f}%, week {wk}.", jira_project, "Medium")
                p2.append(
                    f'<span style="font-family:Consolas,monospace;font-size:11px">'
                    f'{p["process_type"]}</span> — FTA <b>{p["fta_pct"]:.2f}%</b> (AMBER).'
                    f' Monitor next week; intervene if declining.{b}'
                )

    if "coq" in pm and crg in ("AMBER_P2", "AMBER", "AMBER_P3"):
        cn = f' CopQ: {ch:.1f}h rework.' if ch else ''
        b = _btn(f"CoQ: {prj} at {cq:.2f}%",
                 f"CoQ {cq:.2f}% for week {wk}." + (f" Rework: {ch:.1f}h." if ch else ""),
                 jira_project, "Medium")
        p2.append(
            f'CoQ at <b>{cq:.2f}%</b> (AMBER) — investigate rework patterns.{cn}{b}'
        )

    if "efficiency" in pm and erg == "AMBER" and ev is not None:
        p2.append(
            f'Efficiency <b>{_eff_str(ev)}</b> is AMBER — review low-performing '
            f'process types before it reaches RED.'
        )

    if "yield" in pm and yrg == "AMBER" and yv is not None:
        p2.append(
            f'Yield <b>{yv:.2f}%</b> is AMBER — monitor first-pass completion rate; '
            f'intervene if trend continues downward.'
        )

    for t in wa:
        b = _btn(f"SLA Warning: {t['key']}",
                 f"No update for {t['hours_stale']}h. Owner: {t['assignee']}. Link: {t['url']}",
                 jira_project)
        p2.append(
            f'Nudge <b>{t["assignee"]}</b> on '
            f'<a href="{t["url"]}" style="color:#2563EB">{t["key"]}</a>'
            f' — {t["hours_stale"]}h without update, approaching SLA.{b}'
        )

    if not p0 and not p1 and not p2:
        return (
            _alert_row("GREEN", "ALL CLEAR",
                       "No immediate actions required — all metrics are on track.", "")
            + f'<p style="{_F};font-size:12px;color:{_MUTED};margin:8px 0 0;line-height:1.6">'
              f'Continue monitoring. Review process type trends weekly to catch early signals.</p>'
        )

    def _priority_block(tag, label, rag_key, items, idx_start):
        c, bg, bd_c = _rag(rag_key)
        html = (
            f'<div style="background:{bg};border-left:4px solid {c};'
            f'border-radius:0 3px 3px 0;margin-bottom:4px;padding:6px 12px 2px">'
            f'<span style="{_F};font-size:11px;font-weight:bold;color:{c};letter-spacing:0.4px">'
            f'{tag} &mdash; {label}</span></div>'
        )
        for i, item in enumerate(items, idx_start):
            bg_r = _WHITE if i % 2 == 0 else _STRIPE
            html += (
                f'<div style="background:{bg_r};border-left:4px solid {c};'
                f'border-bottom:1px solid {_BORDER};padding:8px 12px;margin-bottom:2px">'
                f'<span style="{_F};font-size:12px;color:{_TEXT}">'
                f'<b style="color:{c}">{i}.</b>&nbsp; {item}'
                f'</span></div>'
            )
        html += f'<div style="margin-bottom:12px"></div>'
        return html, idx_start + len(items)

    html = ""
    idx  = 1
    if p0:
        block, idx = _priority_block("P0", "Immediate Action Required", "RED",   p0, idx)
        html += block
    if p1:
        block, idx = _priority_block("P1", "Fix This Week",             "RED",   p1, idx)
        html += block
    if p2:
        block, idx = _priority_block("P2", "Monitor — Intervene if Trend Continues", "AMBER", p2, idx)
        html += block

    total = len(p0) + len(p1) + len(p2)
    parts = []
    if p0: parts.append(f'{len(p0)} immediate (P0)')
    if p1: parts.append(f'{len(p1)} high priority (P1)')
    if p2: parts.append(f'{len(p2)} to monitor (P2)')

    html += (
        # Human in the loop: the engine only recommends (P0/P1/P2 with Jira links); it never updates,
        # closes or escalates a ticket itself. This sentence states that in every briefing.
        f'<p style="{_F};font-size:12px;color:{_MUTED};margin:4px 0 0;line-height:1.6">'
        f'<b>Summary:</b> {total} action{"s" if total != 1 else ""} — '
        + ', '.join(parts) +
        f'. All actions require your approval before any external communication.</p>'
    )
    return html


def _build_exec_summary(jira, analytics, pm, skill=None):
    """Bulleted executive summary — first thing the reader sees."""
    _s = skill or {}
    project_name = project_name_of(_s)

    br  = jira.get("sla_breaches", [])
    wa  = jira.get("sla_warnings", [])
    fta = analytics.get("fta_current",  0.0)
    frag= analytics.get("fta_rag",      "GREEN")
    ft  = analytics.get("fta_trend",    "stable")
    ev  = analytics.get("efficiency_vs_bl")
    erg = analytics.get("efficiency_rag","GREEN")
    cq  = analytics.get("coq_current",  0.0)
    crg = analytics.get("coq_rag",      "GREEN")
    bd  = analytics.get("process_breakdown", [])
    wk  = analytics.get("week_label",   "")

    overall = "GREEN"
    if br or frag == "RED" or erg == "RED":
        overall = "RED"
    elif wa or frag == "AMBER" or erg == "AMBER":
        overall = "AMBER"
    oc, obg, obd = _rag(overall)

    headline = {
        "RED":   f"Immediate attention required — {project_name} quality metrics are below threshold.",
        "AMBER": f"{project_name} is performing with caution — some metrics need monitoring this week.",
        "GREEN": f"{project_name} is on track — all key metrics within healthy range.",
    }[overall]

    bullets = []

    if "fta" in pm:
        fc, _, _ = _rag(frag)
        bullets.append(
            f'<b>FTA:</b> <span style="color:{fc};font-weight:bold">{fta:.2f}%</span>'
            f' &nbsp;{_badge(frag)}&nbsp; trend {_arrow(ft)} {ft}'
        )

    if "efficiency" in pm:
        ec, _, _ = _rag(erg)
        bullets.append(
            f'<b>Efficiency vs Baseline:</b> <span style="color:{ec};font-weight:bold">'
            f'{_eff_str(ev)}</span> &nbsp;{_badge(erg)}'
            + (f' <span style="color:{_MUTED};font-size:12px">— {_eff_actual_vs_baseline(analytics.get("efficiency_raw"), ev)}</span>'
               if analytics.get("efficiency_raw") and ev else "")
        )

    if "coq" in pm or "copq" in pm:
        cc, _, _ = _rag(crg)
        bullets.append(
            f'<b>Cost of Quality:</b> <span style="color:{cc};font-weight:bold">{cq:.2f}%</span>'
            f' &nbsp;{_badge(crg)}'
        )

    if "yield" in pm:
        yv  = analytics.get("yield_current")
        yr  = analytics.get("yield_rag", "GREEN")
        yc, _, _ = _rag(yr)
        if yv is None and analytics.get("yield_note"):
            bullets.append(f'<b>Yield:</b> <span style="color:{_MUTED}">{analytics["yield_note"]}</span>')
        else:
            yv_str = f"{yv:.2f}%" if yv is not None else "N/A"
            bullets.append(
                f'<b>Yield:</b> <span style="color:{yc};font-weight:bold">{yv_str}</span>'
                f' &nbsp;{_badge(yr)}'
            )

    if flagged(bd):
        worst = min(flagged(bd), key=lambda p: p.get("fta_pct", 100))
        wc, _, _ = _rag(worst["fta_rag"])
        bullets.append(
            f'<b>Lowest FTA:</b> '
            f'<span style="font-family:Consolas,monospace;font-size:11px">{worst["process_type"]}</span>'
            f' at <span style="color:{wc};font-weight:bold">{worst["fta_pct"]:.2f}%</span>'
        )

    if br:
        extra = f' + {len(wa)} warning{"s" if len(wa)>1 else ""}' if wa else ''
        bullets.append(
            f'<b>Jira SLA:</b> <span style="color:{_RED};font-weight:bold">'
            f'{len(br)} breach{"es" if len(br)>1 else ""}</span> requiring immediate follow-up{extra}'
        )
    elif wa:
        bullets.append(
            f'<b>Jira SLA:</b> <span style="color:{_AMBER};font-weight:bold">'
            f'{len(wa)} warning{"s" if len(wa)>1 else ""}</span> approaching breach threshold'
        )
    else:
        bullets.append(
            f'<b>Jira SLA:</b> <span style="color:{_GREEN};font-weight:bold">All clear</span>'
            f' — no breaches or warnings'
        )

    if wk:
        bullets.append(f'<b>Data period:</b> {period_label(wk)}')

    bullets_html = "".join(
        f'<li style="{_F};font-size:12px;color:{_TEXT};padding:3px 0;line-height:1.6">{b}</li>'
        for b in bullets
    )
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{obg};border:1px solid {obd};border-radius:4px;margin-bottom:14px">'
        f'<tr><td style="padding:13px 16px">'
        f'<div style="{_F};font-size:13px;font-weight:bold;color:{oc};margin-bottom:8px">'
        f'&#9679;&nbsp; {headline}</div>'
        f'<ul style="margin:2px 0 0 16px;padding:0">{bullets_html}</ul>'
        f'</td></tr></table>'
    )


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

def project_name_of(skill: dict | None) -> str:
    """Project name from the profile; without one, the Jira key (e.g. "OM") rather than the word "Project"."""
    s = skill or {}
    return s.get("project_name") or s.get("jira_project") or "Project"


def overall_rag(jira: dict, analytics: dict) -> str:
    """The UC1 "Overall" status; the subject uses the same one, so the two never disagree."""
    if jira.get("sla_breaches") or analytics.get("fta_rag") == "RED" or analytics.get("efficiency_rag") == "RED":
        return "RED"
    if jira.get("sla_warnings") or analytics.get("fta_rag") == "AMBER" or analytics.get("efficiency_rag") == "AMBER":
        return "AMBER"
    return "GREEN"


def build(jira: dict[str, Any], analytics: dict[str, Any],
          confluence: dict[str, Any] | None = None,
          skill: dict[str, Any] | None = None,
          preview_note: str | None = None) -> str:
    """Render the UC1 Daily Operational Briefing as an HTML email string.

    Jira/Confluence text is HTML-escaped first. Overall RAG comes from SLA breaches/warnings and the
    FTA/efficiency RAG; sections are numbered and empty ones are left out.
    """
    jira            = _escape_jira(jira)
    confluence      = _escape_confluence(confluence)
    _s              = skill or {}
    project_name    = project_name_of(_s)
    jira_project    = _s.get("jira_project") or ""
    user_first_name = _s.get("user_first_name") or "you"
    project_label   = (f"{project_name} ({jira_project})"
                       if jira_project and jira_project != project_name else project_name)
    pm              = set(_s.get("primary_metrics") or ["fta", "efficiency", "coq"])

    now        = datetime.now(timezone.utc)
    date_str   = now.strftime("%A, %d %B %Y")
    time_str   = now.strftime("%H:%M UTC")
    data_label = analytics.get("data_label", "")

    overall = overall_rag(jira, analytics)
    oc, obg, obd = _rag(overall)
    show_efficiency = bool(pm & {"efficiency", "coq", "copq", "yield"})

    # scope_mode: "defined" when the skill has explicit process types, else "all"
    pts = _s.get("databricks_process_types") or []
    scope_mode = _s.get("scope_mode") or ("defined" if pts else "all")

    # auto-numbering
    n = [0]
    def sec(title, content, accent="#1B2A4A"):
        """Number and render a section; returns "" for empty content (accent is not used)."""
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
          {project_label} &nbsp;·&nbsp; {("Data: " + (period_label(analytics.get("week_label", "")) if analytics.get("week_label") else data_label) + " &nbsp;·&nbsp; ") if (data_label or analytics.get("week_label")) else ""}{date_str} &nbsp;·&nbsp; {time_str}
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

    {_build_exec_summary(jira, analytics, pm, _s)}

    {no_scope_notice(_s)}

    {_build_action_box(jira, analytics, set(pm or []))}

    {_build_kpi_row(analytics, jira, pm)}

    {sec(f"Work Unit &amp; Process-type Breakdown — {period_label(analytics.get('week_label',''))}",
         _build_breakdown(analytics, scope_mode)) if not analytics.get("no_scope") else ""}

    {sec(f"Planning ID Breakdown — {period_label(analytics.get('week_label',''))}",
         _build_planning(analytics))
     if analytics.get("planning_breakdown") or analytics.get("planning_missing") else ""}

    {sec(f"Operator Breakdown — {period_label(analytics.get('week_label',''))}",
         _build_operator_breakdown(analytics))
     if analytics.get("operator_breakdown") else ""}

    {sec(f"Quality — FTA ({project_name})",
         _build_fta(analytics, jira_project)) if "fta" in pm else ""}

    {sec("Efficiency &amp; Cost of Quality",
         _build_efficiency(analytics, pm)) if show_efficiency else ""}

    {sec(f"{jira_project} Sprint Health" if jira_project else "Sprint Health",
         _build_sprint(jira, jira_project))}

    {sec(f"Open {jira_project} Tickets" if jira_project else "Open Tickets",
         _build_tickets(jira))}

    {sec("Confluence — Progress Page",
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

_OP_MIN_TASKS = 10   # min production tasks for an operator to be ranked in UC4 alerts


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
    label: str | None = None,      # override headline, e.g. "Efficiency vs Baseline"
    alert_on: str | None = None,   # "drop" | "rise" — override threshold wording
    operator_breakdown: list[dict] | None = None,   # set when the skill opts into operator level
    analytics: dict[str, Any] | None = None,        # full analytics result, for the work-unit split
) -> str:
    """Compact HTML email for UC4 real-time quality alerts."""
    _s           = skill or {}
    project_name = project_name_of(_s)
    jira_project = _s.get("jira_project") or ""
    user_name    = _s.get("user_first_name") or "you"
    proj_label   = f"{project_name} ({jira_project})" if jira_project else project_name

    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%A, %d %B %Y · %H:%M UTC")

    c, bg, bd = _rag(rag)

    is_fta = metric == "fta"
    metric_label  = label or ("FTA — First Time Accuracy" if is_fta else "CoQ — Cost of Quality")
    value_str     = f"{current_value:.2f}%"
    below         = (alert_on == "drop") if alert_on else is_fta
    thr_label     = f"Below {threshold:g}%" if below else f"Above {threshold:g}%"
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
        def _sp(p):
            sp = p.get("sampling_pct")
            return f'{sp:.1f}%' if sp is not None else '—'

        def _wu_rows(p):
            wus = p.get("work_units") or []
            if len(wus) < 2:
                return []
            m = f'{_F};font-size:11px;color:{_MUTED}'
            return [[f'<span style="{m}">&nbsp;&nbsp;&#8627; {w["name"]}</span>',
                     f'<span style="{m};color:{_rag(w["fta_rag"])[0]}">{w["fta_pct"]:.2f}%</span>',
                     f'<span style="{m}">{w["coq_pct"]:.1f}%</span>',
                     f'<span style="{m}">{_sp(w)}</span>',
                     f'<span style="{m}">{w["total_hrs"]:.0f}h</span>'] for w in wus]

        def _pt_name(p):
            wus = p.get("work_units") or []
            name = f'<span style="{_F};font-size:12px;font-family:Consolas,monospace">{p["process_type"]}</span>'
            if len(wus) == 1:
                name += f'<br><span style="{_F};font-size:10px;color:{_MUTED}">{wus[0]["name"]}</span>'
            return name

        coq_style = "" if is_fta else ";font-weight:bold;color:#922B21"
        proc_rows = []
        for p in flagged:
            proc_rows.append(
                [_pt_name(p),
                 f'<span style="{_F};font-size:12px;color:{_rag(p["fta_rag"])[0]};font-weight:bold">{p["fta_pct"]:.2f}%</span>',
                 f'<span style="{_F};font-size:12px{coq_style}">{p["coq_pct"]:.1f}%</span>',
                 f'<span style="{_F};font-size:12px;color:{_MUTED}">{_sp(p)}</span>',
                 f'<span style="{_F};font-size:12px">{p["total_hrs"]:.0f}h</span>'])
            proc_rows += _wu_rows(p)
        proc_table = _data_table(["Process Type / Work Unit", "FTA", "CoQ", "Sampling", "Hrs"], proc_rows)
    else:
        proc_table = f'<p style="{_F};font-size:12px;color:{_MUTED}">No process-type breakdown available.</p>'

    preview_html = _preview_banner(preview_note) if preview_note else ""

    # Operators driving this metric — worst 10 for the alerted metric
    op_section = ""
    if operator_breakdown:
        # QC-only rows (0 tasks) show 100% CoQ / 0% FTA, and 1-2 task operators
        # swing to extremes on a single rejection — rank only real contributors.
        producing = [o for o in operator_breakdown if (o.get("prod_tasks") or 0) >= _OP_MIN_TASKS]
        if "efficien" in metric_label.lower():
            worst = sorted((o for o in producing if o.get("eff_vs_bl") is not None),
                           key=lambda o: o["eff_vs_bl"])
            sort_note = "lowest efficiency vs baseline first"
        elif is_fta:
            worst = sorted(producing, key=lambda o: o.get("fta_pct", 100))
            sort_note = "lowest FTA first"
        else:
            worst = sorted(producing, key=lambda o: o.get("coq_pct", 0), reverse=True)
            sort_note = "highest CoQ first"
        op_rows = [
            [f'<span style="{_F};font-size:11px;font-family:Consolas,monospace">{o["operator"]}</span>',
             f'<span style="{_F};font-size:11px;color:{_MUTED}">{o["process_type"]}</span>',
             f'<span style="{_F};font-size:11px;color:{_rag(o.get("fta_rag", "GREEN"))[0]};font-weight:bold">{o.get("fta_pct", 0):.2f}%</span>',
             f'<span style="{_F};font-size:11px">{_eff_str(o.get("eff_vs_bl"))}</span>',
             f'<span style="{_F};font-size:11px">{o.get("coq_pct", 0):.1f}%</span>',
             f'<span style="{_F};font-size:11px">{o.get("prod_tasks", 0):,}</span>']
            for o in worst[:10]
        ]
        if op_rows:
            op_section = _section(
                f"Contributing Operators ({sort_note}, top {len(op_rows)} of {len(worst)} "
                f"with {_OP_MIN_TASKS}+ tasks)",
                _data_table(["Operator", "Process Type", "FTA", "Eff vs BL", "CoQ", "Tasks"], op_rows), 3)

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
      &nbsp;·&nbsp; Data: <b>{period_label(week_label, fallback_note=alert_week_note(analytics))}</b>
    </div>
  </td></tr>
  </table>

  <!-- Body -->
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="padding:16px 20px">

    {preview_html}

    {_build_action_box({}, analytics, set(), only=metric) if analytics else ""}

    <!-- Key facts -->
    {_section("Alert Details", _kv_table([
        ("Metric",      metric_label,                                 _TEXT),
        ("Current",     f'<b style="color:{c}">{value_str}</b>',     c),
        ("Threshold",   thr_label,                                    _MUTED),
        ("Trend",       dir_note,                                     c if direction_bad else _GREEN),
        ("Data period", period_label(week_label, fallback_note=alert_week_note(analytics)), _MUTED),
        *([_reference_row(analytics, [metric])] if analytics and metric in _REF_FIELDS
          and _reference_row(analytics, [metric]) else []),
    ]), 1)}

    <!-- Flagged process types -->
    {_section("Contributing Process Types", (_build_workunits(analytics) if analytics else "") + proc_table, 2)}

    {op_section}

    <!-- Action -->
    {_section("Suggested Action", f'''
      <div style="{_F};font-size:13px;color:{_TEXT};line-height:1.6">
        {action}
      </div>
      <div style="{_F};font-size:11px;color:{_MUTED};margin-top:10px">
        All actions require {user_name}'s explicit approval before sending to others.
      </div>
    ''',4 if op_section else 3)}

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


def build_sla_alert(
    jira: dict[str, Any],
    skill: dict[str, Any] | None = None,
    preview_note: str | None = None,
) -> str:
    """HTML email for UC2 Jira SLA alerts — same shell as the UC4 quality alert."""
    from config import SLA_WARNING_HOURS, SLA_ESCALATION_HOURS
    warn_h = f"{(jira or {}).get('sla_warning_hours', SLA_WARNING_HOURS):g}"          # this profile's levels (OSI-006)
    esc_h  = f"{(jira or {}).get('sla_escalation_hours', SLA_ESCALATION_HOURS):g}"
    window = (jira or {}).get("created_window") or "created in the last 12 months"

    jira         = _escape_jira(jira)
    _s           = skill or {}
    project_name = project_name_of(_s)
    jira_project = _s.get("jira_project") or ""
    user_name    = _s.get("user_first_name") or "you"
    proj_label   = f"{project_name} ({jira_project})" if jira_project else project_name
    date_str     = datetime.now(timezone.utc).strftime("%A, %d %B %Y · %H:%M UTC")

    breaches = jira.get("sla_breaches", [])
    warnings = jira.get("sla_warnings", [])
    rag      = "RED" if breaches else "AMBER"
    c, bg, _ = _rag(rag)

    def _ticket_table(tickets: list[dict]) -> str:
        rows = [[
            f'<a href="{t.get("url", "")}" style="color:#2563EB;font-weight:bold;'
            f'text-decoration:none;{_F};font-size:12px">{t.get("key", "")}</a>',
            f'<span style="{_F};font-size:12px">{t.get("summary", "")[:60]}</span>',
            f'<span style="{_F};font-size:12px">{t.get("status", "")}</span>',
            f'<span style="{_F};font-size:12px">{t.get("assignee", "")}</span>',
            f'<span style="{_F};font-size:12px;font-weight:bold">{t.get("hours_stale", "")}h</span>',
            _badge(t.get("sla_status", ""), _sla_word(t.get("sla_status", ""))),
        ] for t in sorted(tickets, key=lambda t: -float(t.get("hours_stale") or 0))]
        return _data_table(["Ticket", "Summary", "Status", "Owner", "Silent", "SLA"], rows)

    sections, n = [], 1
    sections.append(_section("Summary", _kv_table([
        ("SLA breaches",  f'<b style="color:{_RED}">{len(breaches)}</b> ticket(s) silent &gt; {esc_h}h', _RED),
        ("SLA warnings",  f'<b style="color:{_AMBER}">{len(warnings)}</b> ticket(s) silent &gt; {warn_h}h', _AMBER),
        ("Open tickets",  str(jira.get("total_open", len(breaches) + len(warnings))), _TEXT),
        ("Source",        jira.get("source") or "Jira", _MUTED),
        # OSI-034: say how the SLA is measured
        ("SLA rule",      f"Open tickets {window}. A ticket is flagged when it has had no update for "
                          f"{warn_h} h (warning) or {esc_h} h (breach), counted in calendar hours since its last "
                          f"update. Your profile can set other levels, in hours or days.", _MUTED),
    ]), n)); n += 1
    if breaches:
        sections.append(_section(f"SLA Breaches — over {esc_h}h without update",
                                 _ticket_table(breaches), n)); n += 1
    if warnings:
        sections.append(_section(f"SLA Warnings — over {warn_h}h without update",
                                 _ticket_table(warnings), n)); n += 1
    sections.append(_section("Suggested Action", f'''
      <div style="{_F};font-size:13px;color:{_TEXT};line-height:1.6">
        Follow up with the owners of the breached tickets first, oldest first.
        Draft follow-up messages are ready for {user_name}'s approval.
      </div>
      <div style="{_F};font-size:11px;color:{_MUTED};margin-top:10px">
        All actions require {user_name}'s explicit approval before sending to others.
      </div>''', n))

    preview_html = _preview_banner(preview_note) if preview_note else ""
    headline = (f"{len(breaches)} SLA breach(es)" if breaches else "") + \
               (" · " if breaches and warnings else "") + \
               (f"{len(warnings)} warning(s)" if warnings else "")

    return f"""<html>
<body style="margin:0;padding:0;background:#DDE3EA">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#DDE3EA">
<tr><td align="center" style="padding:20px 10px">
<table width="600" cellpadding="0" cellspacing="0"
       style="background:{_WHITE};border-radius:6px;border:1px solid {_BORDER}">
<tr><td>

  <table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td style="background:{_HDR};padding:16px 22px 12px">
      <span style="{_F};font-size:15px;font-weight:bold;color:#fff">&#9201; UC2 — Jira SLA Alert</span><br>
      <span style="{_F};font-size:11px;color:#8FA3C0;margin-top:3px;display:block">
        {proj_label} &nbsp;·&nbsp; {date_str}
      </span>
    </td>
    <td style="background:{_HDR};padding:16px 22px;text-align:right;vertical-align:middle">
      <span style="{_F};font-size:20px;font-weight:bold;color:{c}">&#9679; {rag}</span>
    </td>
  </tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="background:{bg};border-bottom:3px solid {c};padding:18px 22px">
    <div style="{_F};font-size:13px;font-weight:bold;color:{_MUTED};text-transform:uppercase;
                letter-spacing:0.5px;margin-bottom:6px">Tickets without update</div>
    <div style="{_F};font-size:28px;font-weight:bold;color:{c};line-height:1.1">{headline}</div>
  </td></tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="padding:16px 20px">
    {preview_html}
    {''.join(sections)}
  </td></tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td style="background:{_SEC};border-top:1px solid {_BORDER};
                 padding:8px 20px;border-radius:0 0 6px 6px">
    <span style="{_F};font-size:11px;color:{_MUTED}">
      UC2 Jira SLA Alert · Jira live data · Checked at 09:00, 13:00, 17:00 IST
    </span>
  </td></tr>
  </table>

</td></tr>
</table>
</td></tr>
</table>
</body></html>"""
