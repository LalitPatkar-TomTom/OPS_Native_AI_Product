"""
UC1 Daily Briefing, per-process-type layout (5 Nov 2026; mock-up stage, not wired into the runs yet).

Why: a baseline is valid only for its own process type. The classic layout leads with scope-wide numbers,
including "actual vs baseline tasks/hr" over all process types against an averaged baseline, which means
nothing to a lead with several process types (user, 4 Nov; OSI-057). This layout answers what a PM or TL
needs first each morning, in this order:

  1. Status + headline (why), then the recommended actions (the existing box).
  2. What changed and why, incl. a note when the overall moved mainly because the work mix moved.
  3. One table of all process types, each against its own baseline (tasks, hours, actual and own baseline
     tasks/hr, hours at baseline, Eff vs own BL, FTA, CoQ), and a Total row built from the rows that adds
     only what can be added (hours, hours at baseline, FTA/CoQ pooled), with its 8-week trend (user, 5 Nov:
     "instead of cumulative can we have such table"). Then a card per process type that needs attention,
     with what the table cannot show: why, work units, notes and its 8-week trend.
  4. Role section: operators past a level (Operational Lead) or planning IDs (Project Manager), and the
     Jira tickets past / close to the SLA.

Weekly data only (the source has no day column); the current week is shown as "so far". Outlook-safe:
tables and inline CSS only. Reuses the classic builders and palette from email_html.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from agents.analytics_agent import MIN_QC_TO_FLAG, TREND_RUN, mix_split, trend_word
from ask_why import links_row
from config import COQ_INVESTIGATE, COQ_MONITOR, FTA_ALERT, FTA_TARGET, YIELD_ALERT, YIELD_TARGET
from email_html import (
    _AMBER, _BORDER, _F, _GREEN, _HDR, _MUTED, _RED, _SEC, _STRIPE, _TEXT, _WHITE,
    _badge, _build_confluence, _build_planning, _dot, _sample_note, action_items,
    _escape_confluence, _escape_jira, _n, _preview_banner, _rag, _section, _sla_word, headline_text, operator_levels_text,
    no_scope_notice, overall_rag, period_label, project_name_of, shown_tickets,
)

MAX_CARDS = 8          # process types with a full card; the rest fold into one line (BA design, 4 Nov)
MAX_ROWS = 12          # process types listed in the table; the rest are one "Other" row
MIN_QC_TO_JUDGE = MIN_QC_TO_FLAG   # fewer QC'd tasks are not judged, as everywhere else
MIX_NOTE_MIN = 3.0     # points: smaller overall moves get no mix note
SUSPECT_WEEKS = 6      # full weeks in a row ...
SUSPECT_LEVEL = 50.0   # ... below this % of its own baseline = the baseline is probably wrong
SLA_LIST_MAX = 15      # SLA tickets listed, oldest first; the rest are counted and stay in Jira

_WORD_STYLE = {"improving": (_GREEN, "&#8599; improving"), "worsening": (_RED, "&#8600; worsening"),
               "steady": (_MUTED, "&#8594; steady"), "": (_MUTED, "")}


# ── Small helpers ──────────────────────────────────────────────────────────────

def _in_progress(week: str, today: date | None = None) -> bool:
    """True when `week` (a Monday) is the current week, so its numbers are "so far"."""
    t = today or date.today()
    return str(week)[:10] == (t - timedelta(days=t.weekday())).isoformat()


def _short(week: str) -> str:
    """'2 Nov' for '2026-11-02'."""
    d = date.fromisoformat(str(week)[:10])
    return f"{d.day} {d.strftime('%b')}"


def _rag_fta(v):
    """FTA colour from config (FTA_TARGET / FTA_ALERT), as the classic breakdown."""
    return "GREEN" if v >= FTA_TARGET else "AMBER" if v >= FTA_ALERT else "RED"


def _rag_eff(v):
    """Efficiency colour: at/above baseline green, 90-100% amber, as the classic _eff_cell."""
    return "GREEN" if v >= 100 else "AMBER" if v >= 90 else "RED"


def _rag_coq(v):
    """CoQ colour: below COQ_MONITOR green, up to COQ_INVESTIGATE amber, as the classic _coq_cell."""
    return "GREEN" if v < COQ_MONITOR else "AMBER" if v < COQ_INVESTIGATE else "RED"


def _rag_yield(v):
    """Yield colour from config (YIELD_TARGET / YIELD_ALERT)."""
    return "GREEN" if v >= YIELD_TARGET else "AMBER" if v >= YIELD_ALERT else "RED"


def _yield_ok(v):
    """The yield, or None when it reads above 100%: Yield counts reworked tasks resolved later on top, so on
    few tasks it can pass 100%, which is not a real yield (same rule as the operator table, 27 Oct)."""
    return v if v is None or v <= 100 else None


_RAG_OF = {"fta": _rag_fta, "eff": _rag_eff, "coq": _rag_coq, "yield": _rag_yield}
_METRIC_NAME = {"fta": "FTA", "eff": "Efficiency vs its own baseline", "coq": "CoQ", "yield": "Yield"}
_PM_KEY = {"fta": "fta", "eff": "efficiency", "coq": "coq", "yield": "yield"}


def _pt_rags(p: dict, pm: set) -> dict[str, str]:
    """{metric: RAG} for this week's FTA / efficiency / CoQ / Yield of one process type, only for metrics in
    the profile (pm) and only when the sample is big enough to judge."""
    if (p.get("total_qc") or 0) < MIN_QC_TO_JUDGE:
        return {}
    out = {}
    vals = {"fta": p.get("fta_pct"), "eff": _own_eff(p), "coq": p.get("coq_pct"), "yield": _yield_ok(p.get("yield_pct"))}
    for m, v in vals.items():
        if v is not None and _PM_KEY[m] in pm:
            out[m] = _RAG_OF[m](v)
    return out


def _own_eff(p: dict) -> float | None:
    """This week's efficiency vs the process type's OWN baseline; None when it has none (never the
    scope-average fallback the classic layout still uses)."""
    return None if p.get("eff_from_scope_average") else p.get("eff_vs_bl")


def _full_weeks(series: list[dict], key: str) -> list:
    """The values of `key` for full weeks only (the in-progress week is left out of trend words)."""
    return [w[key] for w in series if not _in_progress(w["week"])]


def _words(p: dict) -> dict[str, str]:
    """{metric: trend word} over the process type's full weeks."""
    t = p.get("trend") or []
    return {"fta": trend_word(_full_weeks(t, "fta"), "fta"), "eff": trend_word(_full_weeks(t, "eff_vs_bl"), "eff"),
            "coq": trend_word(_full_weeks(t, "coq"), "coq"),
            "yield": trend_word([_yield_ok(v) for v in _full_weeks(t, "yield")], "yield") if t and "yield" in t[0] else ""}


def baseline_suspect(p: dict) -> bool:
    """True when the process type was below SUSPECT_LEVEL% of its own baseline in each of its last
    SUSPECT_WEEKS full weeks with work. Real work does not stay that far off for that long; the baseline is
    more likely wrong (mock-up 5 Nov: geo-autotx-roadlown2co2g at 10-22% of a 38 tasks/hr baseline for
    8 weeks). The card then asks to check the baseline instead of raising the same alarm every day."""
    vals = [v for v in _full_weeks(p.get("trend") or [], "eff_vs_bl") if v is not None][-SUSPECT_WEEKS:]
    return len(vals) == SUSPECT_WEEKS and all(v < SUSPECT_LEVEL for v in vals)


def needs_attention(p: dict, pm: set) -> bool:
    """A process type gets a full card when one of the profile's metrics is RED/AMBER this week, or has
    been worsening for TREND_RUN full weeks."""
    if any(r in ("RED", "AMBER") for r in _pt_rags(p, pm).values()):
        return True
    return any(w == "worsening" and _PM_KEY[m] in pm for m, w in _words(p).items())


def _fmt(v, kind: str) -> str:
    """'97.6%' / '104%' / '—' for a trend cell."""
    if v is None:
        return "—"
    return f"{v:.0f}%" if kind == "eff" else f"{v:.1f}%"


def _cell(v, kind: str, judge: bool, size: int = 11, bold: bool = False) -> str:
    """A coloured value; grey when not judged (small sample, or not a profile metric)."""
    if v is None:
        return f'<span style="{_F};font-size:{size}px;color:{_MUTED}">—</span>'
    c = _rag(_RAG_OF[kind](v))[0] if judge else _TEXT
    return (f'<span style="{_F};font-size:{size}px;color:{c};font-weight:{"bold" if bold else "600"}">'
            f'{_fmt(v, kind)}</span>')


def _word(w: str) -> str:
    """The trend word, coloured."""
    c, t = _WORD_STYLE.get(w, _WORD_STYLE[""])
    return f'<span style="{_F};font-size:10px;color:{c};font-weight:bold;white-space:nowrap">{t}</span>' if t else ""


# ── Sections ───────────────────────────────────────────────────────────────────

_ITEM_METRIC = (("FTA ", "fta"), ("Efficiency ", "efficiency"), ("CoQ ", "coq"), ("Yield ", "yield"))
ROOT_MAX = 260   # characters of visible text; a longer root cause keeps its first listed item only


def _short_root(text: str) -> str:
    """The root cause in one or two lines: a long list ("A (..); B (..); C (..), 66% of ...") keeps its first
    item and says there are more."""
    visible = re.sub(r"<[^>]+>", "", text or "")
    if len(visible) <= ROOT_MAX or ";" not in text:
        return text
    return text.split(";", 1)[0].rstrip(" ,.") + " (and more, see the process types below)."


def _crisp_actions(jira: dict, analytics: dict, pm: set) -> str:
    """The recommended actions, each as the action and the one root cause it rests on (user, 5 Nov 2026: crisp,
    but with the root cause). Same items and order as the classic box (email_html.action_items); the cause
    comes from root_cause.analyse's "root", else the classic short cause."""
    items = action_items(jira, analytics, pm)
    if not items:
        return ""
    rc_all = (analytics or {}).get("root_cause") or {}
    worst = "RED" if any(r == "RED" for r, _, _ in items) else "AMBER"
    c, bg, bd = _rag(worst)
    rows = ""
    for i, (rag, action, why) in enumerate(items, 1):
        metric = next((m for prefix, m in _ITEM_METRIC if action.startswith(prefix)), None)
        rc = rc_all.get(metric) if metric else None
        root = (rc or {}).get("root") or ""
        note = _sample_note(analytics, metric).strip() if metric and root else ""
        if not root:
            # Jira item, or no driver tree: the classic short cause is one or two sentences (incl. its sample note)
            root = why
        rows += (f'<tr><td style="padding:7px 0;border-top:1px solid {bd}">'
                 f'<div style="{_F};font-size:13px;color:{_TEXT};font-weight:bold">{_dot(rag)} {i}. {action}</div>'
                 f'<div style="{_F};font-size:12px;color:{_TEXT};margin:3px 0 0 18px;line-height:1.5">'
                 f'<span style="color:{_MUTED};font-weight:bold">Root cause: </span>{_short_root(root)}</div>'
                 + (f'<div style="{_F};font-size:11px;color:{_MUTED};margin:2px 0 0 18px">{note}</div>' if note else "")
                 + '</td></tr>')
    return (f'<table width="100%" cellpadding="0" cellspacing="0" style="background:{bg};border:1px solid {bd};'
            f'border-left:5px solid {c};border-radius:4px;margin:0 0 14px"><tr><td style="padding:10px 14px">'
            f'<div style="{_F};font-size:14px;font-weight:bold;color:{c};margin-bottom:4px">&#9888; Recommended actions '
            f'({len(items)})</div><table width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
            f'<div style="{_F};font-size:11px;color:{_MUTED};margin-top:6px">Root causes come from this week&apos;s data '
            f'by work unit, editor and work package, against the previous full week.</div></td></tr></table>')

def _status_box(jira: dict, analytics: dict, pm: set, project_name: str, cards: list, rows: list) -> str:
    """Headline (why) + three short lines: SLA, process types needing attention, data period."""
    overall = overall_rag(jira, analytics, pm)
    oc, obg, obd = _rag(overall)
    br, wa = len(jira.get("sla_breaches") or []), len(jira.get("sla_warnings") or [])
    total = len(cards) + len(rows)
    lines = []
    lines.append(f'<b>Process types:</b> <span style="color:{_RED if cards else _GREEN};font-weight:bold">'
                 f'{len(cards)} of {total} need attention</span>' if total else "<b>Process types:</b> no QC data in this period")
    if br or wa:
        lines.append(f'<b>Jira SLA:</b> <span style="color:{_RED if br else _AMBER};font-weight:bold">'
                     f'{br} past the SLA · {wa} close to it</span>')
    elif jira.get("error"):
        lines.append(f'<b>Jira SLA:</b> <span style="color:{_AMBER};font-weight:bold">Not checked</span>')
    else:
        lines.append(f'<b>Jira SLA:</b> <span style="color:{_GREEN};font-weight:bold">All clear</span>')
    wk = analytics.get("week_label", "")
    if wk:
        so_far = " — week in progress, compared with last full week" if _in_progress(wk) else ""
        lines.append(f'<b>Data:</b> {period_label(wk)}{so_far}')
    li = "".join(f'<li style="{_F};font-size:12px;color:{_TEXT};padding:2px 0;line-height:1.55">{x}</li>' for x in lines)
    return (f'<table width="100%" cellpadding="0" cellspacing="0" style="background:{obg};border:1px solid {obd};'
            f'border-radius:4px;margin-bottom:14px"><tr><td style="padding:12px 16px">'
            f'<div style="{_F};font-size:13px;font-weight:bold;color:{oc};margin-bottom:6px">&#9679;&nbsp; '
            f'{headline_text(project_name, jira, analytics, pm)}</div>'
            f'<ul style="margin:2px 0 0 16px;padding:0">{li}</ul></td></tr></table>')


def _changes(analytics: dict, pm: set) -> str:
    """What changed vs the previous week, overall, and whether it came from the process types or the mix.

    Simpson's effect: every process type can hold steady while the overall drops because more hours went
    to a process type that is below its baseline. Leads then look for a problem that is not there."""
    bd = [p for p in analytics.get("process_breakdown") or [] if p.get("trend")]
    ot = analytics.get("overall_trend") or []
    if len(ot) < 2 or not bd:
        return ""
    now_i, prev_i = len(ot) - 1, len(ot) - 2
    items = []
    for key, label, wkey, kind in (("eff_vs_bl", "Efficiency vs baseline", "hrs", "eff"), ("fta", "FTA", "qc", "fta")):
        if _PM_KEY[kind] not in pm:
            continue
        now = {p["process_type"]: (p["trend"][now_i][wkey], p["trend"][now_i][key]) for p in bd}
        prev = {p["process_type"]: (p["trend"][prev_i][wkey], p["trend"][prev_i][key]) for p in bd}
        s = mix_split(now, prev)
        if not s or abs(s["total"]) < (MIX_NOTE_MIN if kind == "eff" else 1.0):
            continue
        down = s["total"] < 0
        text = f'<b>{label}</b> {"down" if down else "up"} <b>{abs(s["total"]):.1f} pts</b> vs last week'
        if abs(s["mix"]) >= abs(s["total"]) / 2 and s["mix"] * s["total"] > 0:
            # mostly the mix: say so first, so nobody hunts for a performance problem that is not there
            text += (f': <b>{abs(s["mix"]):.1f} pts of it is the work mix</b> (hours moved between process types '
                     f'with different results); the process types themselves moved {s["rate"]:+.1f} pts.')
        else:
            # mostly the process types: name the one or two that moved the overall most, same direction
            movers = [x for x in (s["by_pt"] if down else reversed(s["by_pt"])) if x[1] * s["total"] > 0][:2]
            fmt = (lambda v: f"{v:.0f}%") if kind == "eff" else (lambda v: f"{v:.1f}%")
            named = "; ".join(f'<span style="font-family:Consolas,monospace">{pt}</span> {fmt(a)} → {fmt(b)} '
                              f'({v:+.1f} pts)' for pt, v, a, b in movers)
            text += (f'. Mainly {named}' if named else "") + (f'; work mix {s["mix"]:+.1f} pts.' if named else
                                                              f' (work mix {s["mix"]:+.1f} pts).')
        items.append(text)
    if items and _in_progress(analytics.get("week_label", "")):
        # hours are booked as the work happens, tasks count when they are done: early in the week
        # efficiency and CoQ read low/high and catch up (27 Oct finding)
        items.append(f'<span style="color:{_MUTED}">This week is in progress: efficiency and CoQ often catch up '
                     f'once the started tasks are done.</span>')
    if not items:
        return ""
    li = "".join(f'<li style="{_F};font-size:12px;color:{_TEXT};padding:2px 0;line-height:1.55">{x}</li>' for x in items)
    return f'<ul style="margin:0 0 0 16px;padding:0">{li}</ul>'


def _trend_table(series: list[dict], judged: dict[str, bool], words: dict[str, str]) -> str:
    """8-week mini-table: one column per week (current week marked "so far"), rows FTA / Eff vs own
    baseline / CoQ / Yield (when the process type has Yield) / Hours, last column the trend word."""
    th = (f'{_F};font-size:9px;font-weight:bold;color:{_MUTED};padding:3px 4px;text-align:right;'
          f'border-bottom:1px solid {_BORDER};white-space:nowrap')
    td = f'{_F};font-size:10px;padding:3px 4px;text-align:right;border-bottom:1px dotted {_BORDER};white-space:nowrap'
    lab = f'{_F};font-size:10px;color:{_MUTED};padding:3px 4px;border-bottom:1px dotted {_BORDER};white-space:nowrap'
    head = "".join(f'<th style="{th}">{_short(w["week"])}{"<br>so far" if _in_progress(w["week"]) else ""}</th>'
                   for w in series)
    html = (f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-top:6px">'
            f'<tr><th style="{th};text-align:left">Week</th>{head}<th style="{th};text-align:left">Trend</th></tr>')
    metrics = [("fta", "FTA", "fta"), ("eff_vs_bl", "Eff vs own BL", "eff"), ("coq", "CoQ", "coq")]
    if any(w.get("yield") is not None for w in series):
        metrics.append(("yield", "Yield", "yield"))
    for key, label, kind in metrics:
        cells = ""
        for w in series:
            small = (w.get("qc") or 0) < MIN_QC_TO_JUDGE
            v = _yield_ok(w.get(key)) if kind == "yield" else w[key]
            cells += f'<td style="{td}">{_cell(v, kind, judged.get(kind, False) and not small, size=10)}</td>'
        html += f'<tr><td style="{lab}">{label}</td>{cells}<td style="{lab}">{_word(words.get(kind, ""))}</td></tr>'
    hrs = "".join(f'<td style="{td};color:{_MUTED}">{w["hrs"]:,.0f}</td>' for w in series)
    html += f'<tr><td style="{lab}">Hours</td>{hrs}<td style="{lab}"></td></tr></table>'
    return html


def _trend_html(p: dict, judged: dict, words: dict, images: dict | None) -> str:
    """The card's 8-week trend: a line chart (inline image) when the sender can embed images (`images` dict
    given: the PNG is added under a cid), else the numbers table. Trend words stay as text under the chart."""
    if images is None:
        return _trend_table(p["trend"], judged, words)
    import briefing_charts   # matplotlib loads only when charts are drawn
    cid = f"trend{len(images) + 1}"
    images[cid] = briefing_charts.trend_png(p["trend"], _in_progress(p["trend"][-1]["week"]))
    moving = " · ".join(f"{_METRIC_NAME[k]} {_word(w)}" for k, w in words.items() if w in ("improving", "worsening"))
    return (f'<img src="cid:{cid}" width="600" alt="8-week trend of {_n(p["process_type"])}" '
            f'style="display:block;width:100%;max-width:600px;height:auto;margin-top:6px;border:0">'
            + (f'<div style="{_F};font-size:11px;color:{_TEXT};margin-top:3px">{moving}</div>' if moving else ""))


def _reasons(p: dict, pm: set) -> list[str]:
    """Why this process type has a card: each profile metric past its level this week, and/or worsening
    for TREND_RUN full weeks in a row."""
    rags, words = _pt_rags(p, pm), _words(p)
    vals = {"fta": p.get("fta_pct"), "eff": _own_eff(p), "coq": p.get("coq_pct"), "yield": _yield_ok(p.get("yield_pct"))}
    out = []
    for m in ("fta", "eff", "coq", "yield"):
        if _PM_KEY[m] not in pm:
            continue
        r, worse = rags.get(m), words.get(m) == "worsening"
        level = "past the alert level" if r == "RED" else "needs watching" if r == "AMBER" else ""
        if level or worse:
            trend = f"worsening for {TREND_RUN} weeks in a row" if worse else ""
            out.append(f'{_METRIC_NAME[m]} {_cell(vals[m], m, True, bold=True)} '
                       + " and ".join(x for x in (level, trend) if x))
    return out


def _card(p: dict, pm: set, images: dict | None = None) -> str:
    """One process type that needs attention: why, work units, notes and the 8-week trend. This week's
    numbers are in the table above, so they are not repeated here."""
    rags = _pt_rags(p, pm)
    worst = "RED" if "RED" in rags.values() else "AMBER"
    words = _words(p)
    c, bg, bd = _rag(worst)
    small = (p.get("total_qc") or 0) < MIN_QC_TO_JUDGE
    lines = _reasons(p, pm)
    if baseline_suspect(p):
        lines.append(f'<span style="color:{_AMBER}">&#9888; Below {SUSPECT_LEVEL:.0f}% of its baseline in every one of '
                     f'the last {SUSPECT_WEEKS} full weeks: the baseline itself may be wrong. Please check it before '
                     f'acting on this number.</span>')
    if p.get("yield_pct") is not None and _yield_ok(p["yield_pct"]) is None:
        lines.append(f'<span style="color:{_MUTED}">Yield not shown: it reads above 100% this week (rework '
                     f'resolved later is counted on top).</span>')
    wus = p.get("work_units") or []
    if len(wus) > 1:
        lines.append(f'<span style="color:{_MUTED}">Work units: '
                     + " · ".join(f'{w["name"]} {w.get("total_hrs", 0):,.0f} h (FTA {w.get("fta_pct", 0):.1f}%)'
                                  for w in sorted(wus, key=lambda w: -(w.get("total_hrs") or 0))) + '</span>')
    elif len(wus) == 1:
        lines.append(f'<span style="color:{_MUTED}">Work unit: {wus[0]["name"]}</span>')
    if small:
        lines.append(f'<span style="color:{_MUTED}">Only {p.get("total_qc", 0)} QC&apos;d this week: too few to '
                     f'judge, shown for information.</span>')
    judged = {"fta": "fta" in pm, "eff": "efficiency" in pm, "coq": "coq" in pm, "yield": "yield" in pm}
    trend = _trend_html(p, judged, words, images) if p.get("trend") else ""
    return (f'<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {bd};border-left:5px solid {c};'
            f'border-radius:4px;margin-bottom:10px;background:{_WHITE}"><tr><td style="padding:9px 12px">'
            f'<div style="{_F};font-size:13px;color:{_TEXT}">{_dot(worst)} <b style="font-family:Consolas,monospace">'
            f'{p["process_type"]}</b></div>'
            f'<div style="{_F};font-size:12px;color:{_TEXT};margin-top:4px;line-height:1.6">{"<br>".join(lines)}</div>'
            f'{trend}</td></tr></table>')


# ── 8-week trend charts in the UC3 Weekly Report and UC4 alerts (OSI-010, 6 Nov 2026) ──────────────
# The trend series come from the same analytics run (analytics_agent adds "trend" to each process type for every
# report type), so these charts cost no extra query. A chart that cannot be drawn is left out with a WARNING;
# the email itself is never stopped by a chart (rule book 7.6).
ALERT_CHARTS_MAX = 4   # process types with a chart in one UC4 alert (most hours first)


def _chart_log():
    """The logger chart failures go to (WARNING, listed in the run report)."""
    import logging
    return logging.getLogger("email_briefing_pt")


def weekly_trend_html(analytics: dict, pm: set, images: dict | None) -> str:
    """UC3 Weekly Report: one 8-week chart row per process type (the daily briefing's card charts), the
    MAX_CARDS process types with the most hours, each named with its trend words. '' when the sender cannot
    embed images (images is None) or no process type has a trend."""
    if images is None:
        return ""
    bd = sorted((p for p in analytics.get("process_breakdown") or [] if p.get("trend")),
                key=lambda p: -(p.get("total_hrs") or 0))
    judged = {"fta": "fta" in pm, "eff": "efficiency" in pm, "coq": "coq" in pm, "yield": "yield" in pm}
    parts = []
    for p in bd[:MAX_CARDS]:
        try:
            chart = _trend_html(p, judged, _words(p), images)
        except Exception as exc:
            _chart_log().warning(f"UC3 trend chart for {p.get('process_type')} left out: {type(exc).__name__}: {exc}")
            continue
        parts.append(f'<div style="{_F};font-size:12px;color:{_TEXT};margin-top:10px"><b style="font-family:'
                     f'Consolas,monospace">{p["process_type"]}</b> &nbsp;<span style="color:{_MUTED}">'
                     f'{p.get("total_hrs") or 0:,.0f} h this week</span></div>{chart}')
    if not parts:
        return ""
    more = len(bd) - MAX_CARDS
    note = (f'<p style="{_F};font-size:10px;color:{_MUTED};margin:6px 0 0">Each process type against its own '
            f'target or baseline; the current week is marked "so far". '
            + (f'{more} smaller process types are not drawn.' if more > 0 else '') + '</p>')
    return "".join(parts) + note


def alert_trend_html(rows: list[dict], metric_key: str, level: float, images: dict | None) -> str:
    """UC4 alert: a small 8-week chart of the alerting metric for each alerting process type (at most
    ALERT_CHARTS_MAX, most hours first), with the profile's alert level as the reference line, two per row.
    '' when images is None, no row has a trend, or the metric has no weekly series (CoPQ)."""
    if images is None or not rows:
        return ""
    try:
        import briefing_charts   # matplotlib loads only when charts are drawn
    except Exception as exc:
        _chart_log().warning(f"UC4 trend charts left out: {type(exc).__name__}: {exc}")
        return ""
    cells = []
    for p in sorted((r for r in rows if r.get("trend")), key=lambda r: -(r.get("total_hrs") or 0))[:ALERT_CHARTS_MAX]:
        try:
            png = briefing_charts.alert_png(p["trend"], metric_key, level, _in_progress(p["trend"][-1]["week"]))
        except Exception as exc:
            _chart_log().warning(f"UC4 trend chart for {p.get('process_type')} left out: {type(exc).__name__}: {exc}")
            continue
        if not png:
            continue
        cid = f"alert{len(images) + 1}"
        images[cid] = png
        cells.append(f'<td width="50%" style="padding:4px 4px 4px 0;vertical-align:top">'
                     f'<div style="{_F};font-size:11px;color:{_TEXT};font-family:Consolas,monospace">'
                     f'{p.get("process_type", "")}</div>'
                     f'<img src="cid:{cid}" width="270" alt="8-week trend of {_n(p.get("process_type", ""))}" '
                     f'style="display:block;width:100%;max-width:270px;height:auto;border:0"></td>')
    if not cells:
        return ""
    rows_html = "".join("<tr>" + "".join(cells[i:i + 2]) + ("<td></td>" if len(cells[i:i + 2]) == 1 else "")
                        + "</tr>" for i in range(0, len(cells), 2))
    return (f'<p style="{_F};font-size:12px;font-weight:bold;color:{_TEXT};margin:12px 0 4px">Last 8 weeks '
            f'(dashed line = your alert level; current week "so far")</p>'
            f'<table width="100%" cellpadding="0" cellspacing="0">{rows_html}</table>')


def _row_numbers(p: dict) -> dict:
    """One process type's table numbers. Baseline = the one its efficiency was scored against (its own only);
    hours at baseline = the hours its tasks would take at that baseline = hours x efficiency %."""
    eff, hrs = _own_eff(p), float(p.get("total_hrs") or 0)
    bl = p["efficiency"] * 100 / eff if eff and p.get("efficiency") else (
        None if p.get("eff_from_scope_average") else p.get("own_baseline"))
    earned = hrs * eff / 100 if eff is not None else (0.0 if bl and hrs > 0 else None)
    qc = float(p.get("total_qc") or 0)
    # Yield: this week's numerator / denominator from the trend (so the Total can pool it), else the value only
    last = (p.get("trend") or [{}])[-1]
    y_num, y_den = float(last.get("y_num") or 0), float(last.get("y_den") or 0)
    y = round(y_num * 100 / y_den, 2) if y_den > 0 else p.get("yield_pct")
    return {"tasks": int(p.get("prod_tasks") or 0), "hrs": hrs, "actual": p.get("efficiency") or None, "bl": bl,
            "earned": earned, "eff": eff, "fta": p.get("fta_pct"), "coq": p.get("coq_pct"), "qc": qc,
            "acc": qc * float(p.get("fta_pct") or 0) / 100, "qc_hrs": hrs * float(p.get("coq_pct") or 0) / 100,
            "yield": y, "y_num": y_num, "y_den": y_den}


def _sum_numbers(nums: list[dict]) -> dict:
    """Total of table rows, adding only what can be added: hours, hours at baseline, QC'd / accepted tasks and
    QC hours, Yield numerator / denominator. Efficiency = hours at baseline / hours booked on process types with a
    baseline; FTA, CoQ and Yield pooled.
    Tasks and tasks/hr stay empty: a task of one process type is not the same work as one of another."""
    booked = sum(n["hrs"] for n in nums if n["earned"] is not None)
    earned = sum(n["earned"] for n in nums if n["earned"] is not None)
    hrs, qc = sum(n["hrs"] for n in nums), sum(n["qc"] for n in nums)
    y_num, y_den = sum(n["y_num"] for n in nums), sum(n["y_den"] for n in nums)
    return {"yield": round(y_num * 100 / y_den, 2) if y_den > 0 else None, "y_num": y_num, "y_den": y_den,
            "tasks": None, "hrs": hrs, "actual": None, "bl": None, "earned": earned if booked else None,
            "eff": earned * 100 / booked if booked else None,
            "fta": sum(n["acc"] for n in nums) * 100 / qc if qc else None,
            "coq": sum(n["qc_hrs"] for n in nums) * 100 / hrs if hrs else None, "qc": qc,
            "acc": sum(n["acc"] for n in nums), "qc_hrs": sum(n["qc_hrs"] for n in nums), "booked": booked}


def _pt_table(bd: list[dict], attention: list[dict], pm: set) -> str:
    """All process types this week (most hours first, MAX_ROWS shown, the rest as one 'Other' row), each against
    its own baseline, and a Total row built from the rows above so it always adds up. No combined trend under
    it: each process type has its own (user, 5 Nov). Process types that need attention are marked."""
    th = (f'{_F};font-size:10px;font-weight:bold;color:{_WHITE};background:{_HDR};padding:5px 5px;text-align:right;'
          f'white-space:nowrap')
    heads = ("Process type", "Tasks", "Hours", "Actual<br>tasks/hr", "Own baseline<br>tasks/hr", "Hours at<br>baseline",
             "Eff vs<br>own BL", "FTA", "CoQ", "Yield")
    html = (f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid {_BORDER}">'
            f'<tr>' + "".join(f'<th style="{th}{";text-align:left" if i == 0 else ""}">{h}</th>'
                              for i, h in enumerate(heads)) + '</tr>')
    mark_rag = {id(p): ("RED" if "RED" in _pt_rags(p, pm).values() else "AMBER") for p in attention}

    def row(name_html, n, td, judge, bold=False):
        """One table row from _row_numbers / _sum_numbers values."""
        num = lambda v, f: "" if v is None else f.format(v)
        b = "font-weight:bold;" if bold else ""
        if n["eff"] is not None:
            eff = _cell(n["eff"], "eff", judge and "efficiency" in pm, bold=bold)
        else:
            eff = "" if bold else f'<span style="color:{_MUTED}">no baseline</span>'
        fta = _cell(n["fta"], "fta", judge and "fta" in pm, bold=bold) if n["fta"] is not None else ""
        coq = _cell(n["coq"], "coq", judge and "coq" in pm, bold=bold) if n["coq"] is not None else ""
        yv = _yield_ok(n["yield"])
        yld = (_cell(yv, "yield", judge and "yield" in pm, bold=bold) if yv is not None else
               f'<span style="color:{_MUTED}">&gt;100%*</span>' if n["yield"] is not None else "")
        return ('<tr>'
                + f'<td style="{td};text-align:left">{name_html}</td>'
                + f'<td style="{td};{b}">{num(n["tasks"], "{:,}")}</td>'
                + f'<td style="{td};{b}">{num(n["hrs"], "{:,.0f}")}</td>'
                + f'<td style="{td}">{num(n["actual"], "{:.3f}")}</td>'
                + f'<td style="{td}">{num(n["bl"], "{:.3f}")}</td>'
                + f'<td style="{td};{b}">{num(n["earned"], "{:,.0f}")}</td>'
                + f'<td style="{td}">{eff}</td><td style="{td}">{fta}</td><td style="{td}">{coq}</td>'
                + f'<td style="{td}">{yld}</td></tr>')

    nums = [_row_numbers(p) for p in bd]
    shown, rest = list(zip(bd, nums))[:MAX_ROWS], nums[MAX_ROWS:]
    for i, (p, n) in enumerate(shown):
        td = (f'{_F};font-size:11px;color:{_TEXT};padding:4px 5px;text-align:right;white-space:nowrap;'
              f'background:{_WHITE if i % 2 == 0 else _STRIPE};border-bottom:1px solid {_BORDER}')
        mark = f'{_dot(mark_rag[id(p)])} ' if id(p) in mark_rag else ""
        name = (f'{mark}<span style="font-family:Consolas,monospace;font-size:10px;white-space:normal">'
                f'{p["process_type"]}</span>')
        html += row(name, n, td, (p.get("total_qc") or 0) >= MIN_QC_TO_JUDGE)
    if rest:
        td = (f'{_F};font-size:11px;color:{_MUTED};padding:4px 5px;text-align:right;white-space:nowrap;'
              f'border-bottom:1px solid {_BORDER}')
        html += row(f'Other {len(rest)} process types', _sum_numbers(rest), td, False)
    total = _sum_numbers(nums)
    td = (f'{_F};font-size:11px;color:{_TEXT};padding:6px 5px;text-align:right;white-space:nowrap;'
          f'background:#EEF2F7;border-top:2px solid {_HDR}')
    html += row('<b>Total</b>', total, td, True, bold=True) + '</table>'

    note = ("Total adds only what can be added: hours, hours at baseline (each process type at its own baseline), "
            "and FTA / CoQ / Yield pooled over all tasks and hours. Tasks and tasks/hr are not added up: a task of "
            "one process type is not the same work as a task of another. Eff vs own BL total = hours at baseline "
            "&divide; hours booked.")
    no_bl = total["hrs"] - total["booked"]
    if no_bl >= 1:
        note += f" {no_bl:,.0f} h on process types without a baseline are not in the efficiency total."
    if any(n["yield"] is not None and _yield_ok(n["yield"]) is None for n in nums):
        note += " *Yield above 100% (rework resolved later counted on top) is not a real yield and is not shown."
    if not any(n["yield"] is not None for n in nums):
        note += " Yield exists for Orbit SD work only; none of these process types has Yield data."
    html += f'<p style="{_F};font-size:10px;color:{_MUTED};margin:5px 0 8px">{note}</p>'
    return html


def _process_types(analytics: dict, pm: set, images: dict | None = None) -> tuple[str, list, list]:
    """The main body: the table of all process types with its Total row, then a card for each process type
    that needs attention (most hours first, up to MAX_CARDS). Returns (html, attention rows, other rows)."""
    bd = sorted(analytics.get("process_breakdown") or [], key=lambda p: -(p.get("total_hrs") or 0))
    attention = [p for p in bd if needs_attention(p, pm)]
    cards, over = attention[:MAX_CARDS], attention[MAX_CARDS:]
    rows = [p for p in bd if p not in attention]
    html = _pt_table(bd, attention, pm)
    if cards:
        html += (f'<p style="{_F};font-size:12px;font-weight:bold;color:{_TEXT};margin:10px 0 6px">Needs attention '
                 f'({len(attention)})</p>' + "".join(_card(p, pm, images) for p in cards))
    else:
        html += f'<p style="{_F};font-size:13px;color:{_GREEN};margin:8px 0 6px">No process type needs attention.</p>'
    if over:
        html += (f'<p style="{_F};font-size:11px;color:{_MUTED};margin:0 0 8px">{len(over)} more process types need '
                 f'attention (marked in the table); the {MAX_CARDS} with the most hours have a card.</p>')
    html += (f'<p style="{_F};font-size:10px;color:{_MUTED};margin:6px 0 0">Colours use your profile&apos;s metrics; '
             f'fewer than {MIN_QC_TO_JUDGE} QC&apos;d tasks are not judged. Trend = the last {TREND_RUN} full weeks '
             f'moving the same way.</p>')
    return html, attention, rows


# ── Operators: worst and best, only with enough work (user, 5 Nov 2026) ─────────
# "TL should see at least the top 25 worst performing operators, and the top 5 best with a remark for
# appreciation; worst and best based on a logical count of tasks" (one task done well is not "best").
OP_MIN_PROD_HOURS = 8.0  # production hours in the week (a working day): the only volume bar (user, 5 Nov:
                         # "only focus on prod hrs"); QC hours and task counts do not decide who is judged
OP_MIN_QC = 10           # QC'd tasks before FTA counts (as OP_MIN_TASKS in mark_operator_breaches)
WORST_MAX = 25
BEST_MAX = 5
BEST_EFF_MAX = 200.0     # above this the hours are more likely mis-booked than the work fast: not "best"


def _prod_hrs(o: dict) -> float:
    """An operator's production hours (older rows without the field: all hours)."""
    return float(o.get("prod_hrs") if o.get("prod_hrs") is not None else o.get("total_hrs") or 0)


def enough_work(ops: list[dict]) -> list[dict]:
    """The operators with enough work this week to be judged: at least OP_MIN_PROD_HOURS production hours.
    One task done well, or a few hours, is not a basis for "worst" or "best"."""
    return [o for o in ops if _prod_hrs(o) >= OP_MIN_PROD_HOURS]


def operator_lists(ops: list[dict]) -> tuple[list[dict], list[dict], int]:
    """(worst, best, number judged), both among operators with enough work (enough_work).

    Worst = past one of the profile's levels (breaches from mark_operator_breaches), most levels missed first,
    then most production hours; up to WORST_MAX.
    Best = the team's top performers this week, relative, for appreciation: not in the worst list, past no FTA or
    yield level, efficiency against their own baseline known (up to BEST_EFF_MAX, above is more likely mis-booked),
    fastest first; up to BEST_MAX. Relative on purpose: in a week where the whole team is below baseline (Lanes,
    5 Nov: median 75%), an absolute bar would leave nobody to thank. praise() says how they stand."""
    judged = enough_work(ops)
    worst = sorted((o for o in judged if o.get("breaches")),
                   key=lambda o: (-len(o["breaches"]), -_prod_hrs(o)))[:WORST_MAX]
    listed = {id(o) for o in worst}
    best = sorted((o for o in judged if id(o) not in listed and not set(o.get("breaches") or []) & {"fta", "yield"}
                   and o.get("eff_vs_bl") is not None and o["eff_vs_bl"] <= BEST_EFF_MAX),
                  key=lambda o: (-o["eff_vs_bl"], -float(o.get("fta_pct") or 0)))[:BEST_MAX]
    return worst, best, len(judged)


def praise(o: dict) -> str:
    """A short, factual appreciation line for one of the best operators (fixed wording, no AI)."""
    eff = float(o.get("eff_vs_bl") or 0)
    fta_known = int(o.get("total_qc") or 0) >= OP_MIN_QC
    fta = float(o.get("fta_pct") or 0)
    work = f"{o.get('prod_tasks', 0):,} tasks in {_prod_hrs(o):,.0f} production h"
    if eff >= 100 and fta_known and fta >= FTA_TARGET:
        head = ("Top quality at high speed" if fta >= 99.5 and eff >= 120 else "Near-perfect quality" if fta >= 99.5
                else "Well above baseline with quality on target" if eff >= 120 else "On target on every metric")
        return f"{head}: {work}. Worth a thank-you."
    if eff >= 100:
        return f"Above baseline ({eff:.0f}%): {work}. Worth a thank-you."
    return f"Best in your team this week at {eff:.0f}% of baseline: {work}. Worth recognising."


def _op_rows(rows: list[dict], best: bool) -> str:
    """Operator table rows; past-level cells in red (worst) or the remark column (best)."""
    out = ""
    for i, o in enumerate(rows, 1):
        td = (f'{_F};font-size:10px;color:{_TEXT};padding:4px 5px;background:{_WHITE if i % 2 else _STRIPE};'
              f'border-bottom:1px solid {_BORDER};vertical-align:top')
        hit = set(o.get("breaches") or [])

        def val(m, text):
            """A value, red and bold when past the level."""
            return f'<span style="color:{_RED};font-weight:bold">{text}</span>' if m in hit else text
        yv = _yield_ok(o.get("yield_pct"))
        fta_s = "{:.1f}%".format(float(o.get("fta_pct") or 0))
        coq_s = "{:.1f}%".format(float(o.get("coq_pct") or 0))
        out += ('<tr>'
                + f'<td style="{td}">{i}</td><td style="{td}">{_n(o.get("operator"))}</td>'
                + f'<td style="{td};color:{_MUTED}">{_n(o.get("work_unit"))}</td>'
                + f'<td style="{td};color:{_MUTED};font-family:Consolas,monospace;font-size:9px">{_n(o.get("process_type"))}</td>'
                + f'<td style="{td};text-align:right">{o.get("prod_tasks", 0):,}</td>'
                + f'<td style="{td};text-align:right">{_prod_hrs(o):,.0f}</td>'
                + f'<td style="{td};text-align:right">{val("fta", fta_s)}</td>'
                + f'<td style="{td};text-align:right">{val("efficiency", _fmt(o.get("eff_vs_bl"), "eff"))}</td>')
        if best:
            out += f'<td style="{td};color:{_GREEN}">{praise(o)}</td></tr>'
        else:
            out += (f'<td style="{td};text-align:right">{val("coq", coq_s)}</td>'
                    f'<td style="{td};text-align:right">{val("yield", _fmt(yv, "yield"))}</td></tr>')
    return out


def _operators_section(analytics: dict) -> str:
    """Worst (up to WORST_MAX) and best (up to BEST_MAX) operators, among those with enough work."""
    ops = analytics.get("operator_breakdown") or []
    if not ops:
        return ""
    worst, best, n_judged = operator_lists(ops)
    th = f'{_F};font-size:10px;font-weight:bold;color:{_WHITE};background:{_HDR};padding:4px 5px;text-align:left'
    table = (f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;'
             f'border:1px solid {_BORDER}"><tr>')
    common = ("#", "Operator", "Work unit", "Process type", "Tasks", "Prod hrs", "FTA", "Eff vs own BL")
    levels = analytics.get("operator_levels") or {}
    html = ""
    if worst:
        html += (f'<p style="{_F};font-size:12px;font-weight:bold;color:{_RED};margin:0 0 4px">Needs support — the '
                 f'{len(worst)} operators furthest off your levels</p>' + table
                 + "".join(f'<th style="{th}">{h}</th>' for h in common + ("CoQ", "Yield")) + '</tr>'
                 + _op_rows(worst, best=False) + '</table>')
    elif levels:
        html += (f'<p style="{_F};font-size:12px;color:{_GREEN};margin:0 0 4px">No operator with enough work is past '
                 f'your levels.</p>')
    if best:
        html += (f'<p style="{_F};font-size:12px;font-weight:bold;color:{_GREEN};margin:12px 0 4px">Doing well — top '
                 f'{len(best)} in your team to recognise</p>' + table
                 + "".join(f'<th style="{th}">{h}</th>' for h in common + ("Remark",)) + '</tr>'
                 + _op_rows(best, best=True) + '</table>')
    rule = operator_levels_text(levels) or "your profile has no operator alert levels"
    html += (f'<p style="{_F};font-size:10px;color:{_MUTED};margin:5px 0 0">Only operators with enough work this week '
             f'are judged: at least {OP_MIN_PROD_HOURS:g} production hours ({n_judged} of {len(ops)} operators); FTA '
             f'counts from {OP_MIN_QC} QC&apos;d tasks. Worst = most levels missed, then most production hours; '
             f'levels: {rule}. Best = the fastest against their own baseline among the '
             f'others, with no FTA or yield problem (relative: the best of your team this week). Efficiency always '
             f'against the operator&apos;s own process type baseline.</p>')
    return html


def _sla_tickets(jira: dict) -> str:
    """Only the tickets past or close to the SLA; the full list stays in Jira."""
    from email_html import key_warning_note
    ts = (jira.get("sla_breaches") or []) + (jira.get("sla_warnings") or [])
    total = jira.get("total_open") or len(jira.get("open_tickets") or [])
    if not ts:
        return ((f'<p style="{_F};font-size:12px;color:{_GREEN};margin:0">No ticket past or close to the SLA '
                 f'({total:,} open in Jira).</p>') + key_warning_note(jira)) if not jira.get("error") else ""
    th = f'{_F};font-size:10px;font-weight:bold;color:{_WHITE};background:{_HDR};padding:4px 6px;text-align:left'
    html = (f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid {_BORDER}">'
            f'<tr>' + "".join(f'<th style="{th}">{h}</th>' for h in ("Ticket", "Summary", "Owner", "No update", "SLA")) + '</tr>')
    for i, t in enumerate(shown_tickets(ts)[:SLA_LIST_MAX]):
        td = (f'{_F};font-size:11px;color:{_TEXT};padding:4px 6px;background:{_WHITE if i % 2 == 0 else _STRIPE};'
              f'border-bottom:1px solid {_BORDER}')
        html += (f'<tr><td style="{td}"><a href="{t.get("url", "#")}" style="color:#2563EB;font-weight:bold;'
                 f'text-decoration:none">{t["key"]}</a></td><td style="{td}">{str(t.get("summary", ""))[:60]}</td>'
                 f'<td style="{td}">{t.get("assignee", "")}</td><td style="{td};text-align:right">{t.get("hours_stale", "")}h</td>'
                 f'<td style="{td}">{_badge(t["sla_status"], _sla_word(t["sla_status"]))}</td></tr>')
    extra = len(ts) - SLA_LIST_MAX
    more = (f'<p style="{_F};font-size:12px;color:{_MUTED};margin:6px 0 0">… and <b>{extra:,} more</b> past or close '
            f'to the SLA in Jira (the {SLA_LIST_MAX} with the longest time without an update are shown).</p>'
            if extra > 0 else "")
    return html + '</table>' + more + (
        f'<p style="{_F};font-size:10px;color:{_MUTED};margin:4px 0 0">{total:,} open tickets in scope; only those '
        f'past or close to the SLA are listed.</p>') + key_warning_note(jira)


# ── Entry point ────────────────────────────────────────────────────────────────

LAYOUT_ENV = "BRIEFING_LAYOUT"   # "classic" switches every UC1 email back to email_html.build, no release needed


def build_daily(jira: dict, analytics: dict, confluence: dict | None, skill: dict | None,
                preview_note: str | None = None) -> tuple[str, dict[str, bytes], str]:
    """The UC1 daily briefing for one user: (html, inline images {cid: png}, layout used).

    Default is this per-process-type layout (user, 5 Nov 2026: "keep this as daily briefing", for everyone).
    BRIEFING_LAYOUT=classic on the job switches back to the classic layout without a release. If this layout
    fails for a user, that user gets the classic layout and the failure is logged as a WARNING (the run report
    lists it); one user's problem never stops their email (rule book 7.6, "nothing should break")."""
    import logging
    import os
    import email_html
    if os.getenv(LAYOUT_ENV, "").strip().lower() != "classic":
        try:
            images: dict[str, bytes] = {}
            html = build(jira, analytics, confluence, skill, preview_note=preview_note, images=images)
            return html, images, "per_pt"
        except Exception as exc:
            logging.getLogger("email_briefing_pt").warning(
                f"UC1 per-process-type layout failed for {(skill or {}).get('user', '?')}, sent the classic layout: "
                f"{type(exc).__name__}: {exc}")
    try:
        return email_html.build(jira, analytics, confluence, skill=skill, preview_note=preview_note), {}, "classic"
    except Exception as exc:
        # as before 5 Nov: no HTML, deliver() then sends the plain-text briefing
        logging.getLogger("email_briefing_pt").warning(f"UC1 classic layout failed too, plain text sent: {exc}")
        return "", {}, "plain"


def own_baselines_only(analytics: dict) -> dict:
    """A copy of the analytics where no process type carries an efficiency scored against the scope-average
    baseline, so the shared sections (recommended actions) agree with the cards ("no baseline")."""
    a = dict(analytics or {})
    a["process_breakdown"] = [{**p, "eff_vs_bl": None} if p.get("eff_from_scope_average") else p
                              for p in a.get("process_breakdown") or []]
    return a


def build(jira: dict[str, Any], analytics: dict[str, Any], confluence: dict[str, Any] | None = None,
          skill: dict[str, Any] | None = None, preview_note: str | None = None,
          images: dict[str, bytes] | None = None) -> str:
    """Render the UC1 Daily Briefing in the per-process-type layout as an HTML email string."""
    from skill_registry import jira_label
    analytics = own_baselines_only(analytics)
    s = skill or {}
    jp = jira_label(s, jira)          # every key checked, e.g. "OM, MCPET" (OSI-061); one key: as before
    jira = _escape_jira(jira) or {}
    confluence = _escape_confluence(confluence)
    project_name = project_name_of(s)
    label = f"{project_name} ({jp})" if jp and jp != project_name else project_name
    pm = set(s.get("primary_metrics") or ["fta", "efficiency", "coq"])
    lead = "operational lead" in (s.get("domain") or "").lower()
    now = datetime.now(timezone.utc)
    overall = overall_rag(jira, analytics, pm)
    oc, _, _ = _rag(overall)
    wk = analytics.get("week_label", "")

    n = [0]

    def sec(title, body):
        """Number and render a section; '' for empty content."""
        if not body or not body.strip():
            return ""
        n[0] += 1
        return _section(title, body, n[0])

    no_scope = bool(analytics.get("no_scope"))
    pt_html, cards, rows = _process_types(analytics, pm, images) if not no_scope else ("", [], [])
    role = ""
    if not no_scope:
        if lead and analytics.get("operator_breakdown"):
            role = sec(f"Operators — {period_label(wk)}", _operators_section(analytics))
        if analytics.get("planning_breakdown") or analytics.get("planning_missing"):
            role += sec(f"Planning IDs — {period_label(wk)}", _build_planning(analytics))
        if not lead and analytics.get("operator_breakdown"):
            role += sec(f"Operators — {period_label(wk)}", _operators_section(analytics))
    conf = _build_confluence(confluence) if (confluence or {}).get("pages") else ""

    return f"""<html>
<body style="margin:0;padding:0;background:#DDE3EA">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#DDE3EA">
<tr><td align="center" style="padding:20px 10px">
<table width="640" cellpadding="0" cellspacing="0" style="background:{_WHITE};border-radius:6px;border:1px solid {_BORDER}">
<tr><td>
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="background:{_HDR};padding:20px 22px 14px">
      <span style="{_F};font-size:18px;font-weight:bold;color:#fff">Daily Operational Briefing</span><br>
      <span style="{_F};font-size:12px;color:#8FA3C0;display:block;margin-top:3px">
        {label} &nbsp;·&nbsp; {("Data: " + period_label(wk) + " &nbsp;·&nbsp; ") if wk else ""}{now.strftime("%A, %d %B %Y")}</span>
    </td>
    <td style="background:{_HDR};padding:20px 22px;text-align:right;white-space:nowrap;vertical-align:middle">
      <span style="{_F};font-size:11px;color:#8FA3C0">Overall</span><br>
      <span style="{_F};font-size:15px;font-weight:bold;color:{oc}">&#9679; {overall}</span>
    </td></tr></table>
  <table width="100%" cellpadding="0" cellspacing="0"><tr><td style="padding:18px 20px">
    {_preview_banner(preview_note) if preview_note else ""}
    {_status_box(jira, analytics, pm, project_name, cards, rows)}{links_row(analytics)}
    {no_scope_notice(s)}
    {_crisp_actions(jira, analytics, pm)}
    {sec("What changed since last week", _changes(analytics, pm)) if not no_scope else ""}
    {sec(f"Your process types — {period_label(wk)}", pt_html) if not no_scope else ""}
    {role}
    {sec(f"Jira — tickets past or close to the SLA ({jp})" if jp else "Jira — tickets past or close to the SLA", _sla_tickets(jira))}
    {sec("Confluence — progress page", conf)}
  </td></tr></table>
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="background:{_SEC};border-top:1px solid {_BORDER};padding:10px 20px;border-radius:0 0 6px 6px">
      <span style="{_F};font-size:11px;color:{_MUTED}">UC1 Daily Briefing &nbsp;·&nbsp; Jira {jp} · Databricks (weekly data) · Confluence
      &nbsp;—&nbsp; detail stays in Power BI and Jira.</span>
    </td></tr></table>
</td></tr></table>
</td></tr></table>
</body></html>"""
