"""PROTOTYPE future-state lead mail (27 Oct 2026): root cause + actions on the user's own RM Lanes scope.

Scratchpad only: nothing in OPS Hub or OPS Native AI is changed. Reads the read-only extracts made by
explore.py / explore3.py (data.json, data3.json), computes every number in code, draws the trend charts
(matplotlib PNG, inline by content id), writes preview.html, and with --send sends it from the user's own
Outlook to the user only.
"""
import html
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
TO = "lalit.patkar@tomtom.com"          # the only recipient, by the user's request
OPSHUB = "https://tomtom-ops-hub.bravewave-803863cf.westeurope.azurecontainerapps.io"
WEEK, PREV = "2026-10-19", "2026-10-12"
BASE_WEEKS = ("2026-08-24", "2026-08-31", "2026-09-07", "2026-09-14")
PTS = ["attr-cc-orbisconnectivity", "attr-create-orbisconnectivity", "orbis-create-lanesgaps"]
PT_SHORT = {"attr-cc-orbisconnectivity": "Attr-CC Connectivity", "attr-create-orbisconnectivity": "Attr-Create Connectivity",
            "orbis-create-lanesgaps": "Lanes Gaps"}
WU_NAME = {"dpu globallogic": "DPU GlobalLogic", "dpu hyderabad": "DPU Hyderabad", "dpu noida": "DPU Noida", "occ": "OCC"}
TARGET = {"fta": 95, "coq": 7, "eff": 100}
ALERT = {"fta": 92, "coq": 10, "eff": 90}

d = json.load(open(HERE / "data.json", encoding="utf-8"))
d3 = json.load(open(HERE / "data3.json", encoding="utf-8"))


def n(v):
    """Number or 0."""
    return float(v or 0)


def agg(rows):
    """FTA, CoQ, efficiency and the CoQ drivers for a set of rows (same formulas as the engine)."""
    t, q, r, ph, qh = (sum(n(x[k]) for x in rows) for k in ("tasks", "qc", "rej", "prod_h", "qc_h"))
    return {"tasks": t, "qc": q, "rej": r, "prod_h": ph, "qc_h": qh,
            "fta": 100 * (q - r) / q if q else None, "coq": 100 * qh / (ph + qh) if ph + qh else None,
            "eff": t / (ph + qh) if ph + qh else None, "samp": q / t if t else None,
            "qc_min": 60 * qh / q if q else None, "prod_min": 60 * ph / t if t else None}


BL = {r["processType"].lower(): n(r["bl"]) for r in d["weekly_pt"] if n(r["bl"])}
weeks = sorted({r["week_start"] for r in d["weekly_all"] if r["week_start"] <= WEEK})
ALL = {w: agg([r for r in d["weekly_all"] if r["week_start"] == w]) for w in weeks}
PTW = {(w, pt): agg([r for r in d["weekly_pt"] if r["week_start"] == w and r["processType"].lower() == pt])
       for w in weeks for pt in PTS}


def eff_bl(w, pt):
    """Efficiency as % of the process type's baseline, or None."""
    a = PTW[(w, pt)]
    return 100 * a["eff"] / BL[pt] if a["eff"] and a["tasks"] else None


# ── Finding 1: CoQ decomposition (sampling x QC minutes / production minutes) ──────────────────────
base = agg([r for r in d["weekly_all"] if r["week_start"] in BASE_WEEKS])
now, prev = ALL[WEEK], ALL[PREV]
ls, lq, lp = math.log(now["samp"] / base["samp"]), math.log(now["qc_min"] / base["qc_min"]), -math.log(now["prod_min"] / base["prod_min"])
tot = ls + lq + lp
share = {"samp": 100 * ls / tot, "qcmin": 100 * lq / tot, "prod": 100 * lp / tot}
weeks_above = 0
for w in reversed(weeks):
    if ALL[w]["coq"] > ALERT["coq"]:
        weeks_above += 1
    else:
        break

wu_rows = []
for r in d["wu"]:
    if r["week_start"] == WEEK and n(r["tasks"]) >= 50 and n(r["qc"]) >= 10:
        a = agg([r]); a["pt"] = r["processType"].lower(); a["wu"] = r["work_unit"]; wu_rows.append(a)
wu_rows.sort(key=lambda a: -a["qc_h"])
excess = [(a, a["qc_h"] * (1 - 0.12 / a["samp"])) for a in wu_rows if a["fta"] >= 97 and a["samp"] > 0.15]
excess_h = sum(e for _, e in excess)
backlog = [r for r in d["wu"] if r["week_start"] == PREV and n(r["qc"]) > n(r["tasks"]) > 0 and n(r["qc"]) > 500]

# editors under 92% FTA over 4 weeks (>= 10 QC'd), their QC hours last week
E = defaultdict(lambda: {"tasks": 0, "qc": 0, "rej": 0, "qc_h": 0, "last_qc_h": 0, "low_weeks": 0, "weeks": 0})
for r in d["editor"]:
    if r["week_start"] > WEEK:
        continue
    e = E[(r["processType"].lower(), r["work_unit"], r["editor"])]
    e["tasks"] += n(r["tasks"]); e["qc"] += n(r["qc"]); e["rej"] += n(r["rej"]); e["qc_h"] += n(r["qc_h"])
    if r["week_start"] == WEEK:
        e["last_qc_h"] += n(r["qc_h"])
    if n(r["qc"]) >= 10:
        e["weeks"] += 1
        if (n(r["qc"]) - n(r["rej"])) / n(r["qc"]) < 0.92:
            e["low_weeks"] += 1
judged = {k: v for k, v in E.items() if v["qc"] >= 10}
low = {k: v for k, v in judged.items() if (v["qc"] - v["rej"]) / v["qc"] < 0.92}
low_rej, all_rej = sum(v["rej"] for v in low.values()), sum(v["rej"] for v in E.values())
low_save = sum(v["last_qc_h"] for v in low.values()) * (1 - 12 / 29)
low_by_wu = defaultdict(int)
for k in low:
    low_by_wu[k[1]] += 1


def initials(name):
    """Editor name masked to initials (names only after the HR check)."""
    return ". ".join(p[0].upper() for p in str(name).split()[:3]) + "."


coach = sorted(low.items(), key=lambda kv: (-kv[1]["rej"], -kv[1]["qc"]))[:6]

# ── Finding 2: efficiency, Attr-Create, by work package ─────────────────────────────────────────────
pt2 = "attr-create-orbisconnectivity"
wps = [r for r in d["wp"] if r["week_start"] == WEEK and r["processType"].lower() == pt2]
wp_agg = defaultdict(list)
for r in wps:
    wp_agg[r["work_package"] or "-"].append(r)
wp_rows = sorted(((k, agg(v)) for k, v in wp_agg.items()), key=lambda kv: -(kv[1]["prod_h"] + kv[1]["qc_h"]))
pt2_all = PTW[(WEEK, pt2)]
pt2_h = pt2_all["prod_h"] + pt2_all["qc_h"]
slow = [(k, a) for k, a in wp_rows if a["tasks"] >= 50 and a["eff"] and 100 * a["eff"] / BL[pt2] < 80]
rest = agg([r for k, v in wp_agg.items() if k not in {s[0] for s in slow} for r in v])
notask = defaultdict(float)
for r in d["wu"]:
    if r["week_start"] == WEEK and not n(r["tasks"]):
        notask[r["processType"].lower()] += n(r["prod_h"])
notask_h = sum(notask.values())

# ── Also noticed: tasks closed without a map change ─────────────────────────────────────────────────
st = defaultdict(int)
for r in d3["status"]:
    st[r["current_status"]] += int(n(r["n"]))
st_total = sum(st.values())
no_change = {k: v for k, v in st.items() if k != "Accepted"}
no_change_n = sum(no_change.values())


# ── charts ──────────────────────────────────────────────────────────────────────────────────────────
def wl(w):
    """Week label, e.g. 19 Oct."""
    return datetime.strptime(w, "%Y-%m-%d").strftime("%d %b").lstrip("0")


X = [wl(w) for w in weeks]
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False})


def chart_coq(path):
    """CoQ % (line) with QC sampling % (bars), target and alert level, 9 complete weeks."""
    fig, ax = plt.subplots(figsize=(6.8, 2.3), dpi=130)
    ax2 = ax.twinx()
    ax2.bar(X, [100 * ALL[w]["samp"] for w in weeks], color="#dbe4f0", width=0.6, label="QC sampling %")
    ax2.set_ylim(0, 60); ax2.set_ylabel("sampling %", color="#7b8ba1"); ax2.tick_params(colors="#7b8ba1")
    ax2.spines["top"].set_visible(False)
    ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
    ys = [ALL[w]["coq"] for w in weeks]
    ax.plot(X, ys, color="#c8102e", lw=2.2, marker="o", ms=4, label="CoQ %")
    ax.axhline(TARGET["coq"], color="#16a34a", ls="--", lw=1); ax.axhline(ALERT["coq"], color="#f59e0b", ls="--", lw=1)
    ax.text(len(X) - 0.6, TARGET["coq"] - 1.2, "target 7%", color="#16a34a", ha="right", fontsize=7.5)
    ax.text(len(X) - 0.6, ALERT["coq"] + 0.4, "alert 10%", color="#b45309", ha="right", fontsize=7.5)
    for i, y in enumerate(ys):
        ax.text(i, y + 0.6, f"{y:.1f}", ha="center", fontsize=7, color="#7f1d1d")
    ax.set_ylim(0, 20); ax.set_ylabel("CoQ %")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def chart_pt(path, metric, title_unit, lo, hi):
    """One line per process type for FTA or efficiency vs baseline, with target and alert lines."""
    fig, ax = plt.subplots(figsize=(6.8, 2.1), dpi=130)
    colors = {"attr-cc-orbisconnectivity": "#1d4ed8", "attr-create-orbisconnectivity": "#c8102e", "orbis-create-lanesgaps": "#0f766e"}
    for pt in PTS:
        ys = [(PTW[(w, pt)]["fta"] if PTW[(w, pt)]["qc"] >= 10 else None) if metric == "fta" else
              (eff_bl(w, pt) if PTW[(w, pt)]["tasks"] >= 50 else None) for w in weeks]
        ax.plot(X, [y if y is not None else float("nan") for y in ys], marker="o", ms=3.5, lw=1.8, color=colors[pt], label=PT_SHORT[pt])
    ax.axhline(TARGET[metric], color="#16a34a", ls="--", lw=1); ax.axhline(ALERT[metric], color="#f59e0b", ls="--", lw=1)
    ax.set_ylim(lo, hi); ax.set_ylabel(title_unit)
    ax.legend(loc="lower left", fontsize=7, frameon=False, ncol=3)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


chart_coq(HERE / "coq.png")
chart_pt(HERE / "eff.png", "eff", "% of baseline", 40, 170)
chart_pt(HERE / "fta.png", "fta", "FTA %", 85, 100.5)

# ── HTML (Outlook-safe: tables, inline styles) ──────────────────────────────────────────────────────
F = "font-family:Segoe UI,Arial,sans-serif"
INK, MUTED, LINE, RED, AMBER, GREEN, BLUE = "#1f2937", "#6b7280", "#e5e7eb", "#c8102e", "#b45309", "#15803d", "#1d4ed8"
e = html.escape


def pct(v, dp=1):
    """'12.3%' or '–'."""
    return "–" if v is None else f"{v:.{dp}f}%"


def delta(a, b, good_up=True, unit=" pts"):
    """Coloured change between two values."""
    if a is None or b is None:
        return "–"
    dv = b - a
    good = dv >= 0 if good_up else dv <= 0
    return f'<span style="color:{GREEN if good else RED};font-weight:600">{"▲" if dv >= 0 else "▼"} {abs(dv):.1f}{unit}</span>'


def chip(text, color):
    """Small coloured label."""
    return (f'<span style="display:inline-block;padding:2px 8px;border-radius:10px;background:{color}1a;color:{color};'
            f'font-size:11px;font-weight:700;letter-spacing:.3px">{text}</span>')


def btn(text, href, color=BLUE, solid=False):
    """Link styled as a button (Outlook-safe)."""
    st = (f"background:{color};color:#fff;border:1px solid {color}" if solid else f"background:#fff;color:{color};border:1px solid {color}")
    return (f'<a href="{href}" style="{F};{st};display:inline-block;padding:5px 11px;border-radius:5px;font-size:12px;'
            f'font-weight:600;text-decoration:none;margin:2px 4px 2px 0">{text}</a>')


def table(headers, rows, align=None):
    """Simple bordered data table."""
    align = align or ["left"] + ["right"] * (len(headers) - 1)
    th = "".join(f'<th style="{F};font-size:11px;color:{MUTED};text-align:{a};padding:6px 8px;border-bottom:2px solid {LINE};'
                 f'text-transform:uppercase;letter-spacing:.3px">{h}</th>' for h, a in zip(headers, align))
    tr = "".join("<tr>" + "".join(f'<td style="{F};font-size:13px;color:{INK};text-align:{a};padding:6px 8px;border-bottom:1px solid {LINE}">{c}</td>'
                                  for c, a in zip(row, align)) + "</tr>" for row in rows)
    return f'<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%">{th and "<tr>" + th + "</tr>"}{tr}</table>'


def section(num, title, rag, body):
    """A finding card with a numbered header."""
    col = {"red": RED, "amber": AMBER, "green": GREEN, "blue": BLUE}[rag]
    return (f'<tr><td style="padding:14px 24px 4px"><table cellpadding="0" cellspacing="0" style="width:100%;border:1px solid {LINE};'
            f'border-left:5px solid {col};border-radius:6px"><tr><td style="padding:14px 18px">'
            f'<div style="{F};font-size:11px;color:{col};font-weight:700;letter-spacing:.6px;text-transform:uppercase">{num}</div>'
            f'<div style="{F};font-size:18px;color:{INK};font-weight:700;margin:2px 0 10px">{title}</div>{body}</td></tr></table></td></tr>')


def h(text):
    """Sub-heading inside a card."""
    return f'<div style="{F};font-size:12px;color:{MUTED};font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin:14px 0 6px">{text}</div>'


def p(text, size=14, color=INK, extra=""):
    """Paragraph."""
    return f'<div style="{F};font-size:{size}px;color:{color};line-height:1.5;{extra}">{text}</div>'


def bar3(parts):
    """A 100% stacked bar from (label, share, colour)."""
    cells = "".join(f'<td style="background:{c};width:{max(s, 1):.0f}%;height:22px;{F};font-size:11px;color:#fff;font-weight:700;'
                    f'text-align:center;white-space:nowrap">{s:.0f}%</td>' for _, s, c in parts)
    legend = " &nbsp; ".join(f'<span style="color:{c}">■</span> {lab}' for lab, _, c in parts)
    return (f'<table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;border-radius:4px"><tr>{cells}</tr></table>'
            + p(legend, 12, MUTED, "margin-top:5px"))


ACTIONS = []


def action(owner, what, why, impact, due, ask, extra=""):
    """One recommended action; numbered A1.., kept for the tracker at the end. `extra`: more buttons."""
    aid = f"A{len(ACTIONS) + 1}"
    ACTIONS.append((aid, owner, what, due))
    q = e(ask).replace(" ", "%20")
    return (f'<table cellpadding="0" cellspacing="0" style="width:100%;background:#f8fafc;border:1px solid {LINE};border-radius:6px;margin:8px 0">'
            f'<tr><td style="padding:10px 14px">'
            f'<div style="{F};font-size:14px;color:{INK};font-weight:700">{aid} · {what}</div>'
            f'<div style="{F};font-size:13px;color:{INK};line-height:1.5;margin-top:3px"><b>Why:</b> {why}</div>'
            f'<div style="{F};font-size:13px;color:{INK};line-height:1.5"><b>Expected impact:</b> {impact}</div>'
            f'<div style="{F};font-size:12px;color:{MUTED};margin:4px 0 6px">Owner: <b style="color:{INK}">{owner}</b> · Due: <b style="color:{INK}">{due}</b></div>'
            f'{btn("✔ Acknowledge", OPSHUB, GREEN, True)}{btn("Assign", OPSHUB)}{btn("Not an issue", OPSHUB, MUTED)}'
            f'{btn("Ask OPS Hub why →", OPSHUB + "/?q=" + q)}{extra}</td></tr></table>')


# Finding 1 body
g_cc = next(a for a in wu_rows if a["pt"] == "attr-cc-orbisconnectivity" and a["wu"] == "dpu globallogic")
g_cc_5 = agg([r for r in d["wu"] if r["week_start"] == "2026-10-05" and r["processType"].lower() == "attr-cc-orbisconnectivity" and r["work_unit"] == "dpu globallogic"])
bk = backlog[0] if backlog else None
f1 = (
    p(f'CoQ was <b>{pct(now["coq"])}</b> against a 7% target. It has been above the 10% alert level for '
      f'<b>{weeks_above} weeks in a row</b>, and it was {pct(base["coq"])} in late August and early September.')
    + '<img src="cid:coq.png" width="640" style="display:block;width:100%;max-width:640px;margin:10px 0 2px" alt="CoQ trend">'
    + p("Bars: share of production tasks that were QC'd. Line: CoQ (QC hours as a share of all hours). Complete weeks only.", 11, MUTED)
    + h("Root cause: what moved CoQ from 7.6% to 11.4%")
    + bar3([("More tasks QC'd (sampling up)", share["samp"], RED), ("Longer QC per task", share["qcmin"], AMBER),
            ("Faster production (fewer production hours per task)", share["prod"], "#64748b")])
    + p(f'Sampling went from <b>{100*base["samp"]:.1f}%</b> to <b>{100*now["samp"]:.1f}%</b> of tasks. QC time went from {base["qc_min"]:.1f} to {now["qc_min"]:.1f} '
        f'minutes per QC\'d task, and production time from {base["prod_min"]:.1f} to {now["prod_min"]:.1f} minutes per task.', 13, INK, "margin-top:6px")
    + h("Why sampling went up")
    + p(f'The RM Lanes sampling rule QC\'s about <b>29%</b> of the work of editors under 92% FTA, against 9–12% for everyone else. '
        f'Attr-CC at DPU GlobalLogic fell to {pct(g_cc_5["fta"])} FTA in the week of 5 Oct, and its sampling rose from {100*g_cc_5["samp"]:.1f}% to {100*g_cc["samp"]:.1f}%. '
        f'Over the last 4 weeks, <b>{len(low)} of {len(judged)} editors</b> were under 92%. They account for <b>{low_rej:.0f} of {all_rej:.0f} rejections '
        f'({100*low_rej/all_rej:.0f}%)</b>.', 13)
    + h("Where the QC hours went (19–25 Oct)")
    + table(["Process type · work unit", "Tasks", "QC'd", "Sampling", "FTA", "QC h", "CoQ"],
            [[f'{PT_SHORT[a["pt"]]} · {WU_NAME.get(a["wu"], a["wu"])}', f'{a["tasks"]:,.0f}', f'{a["qc"]:,.0f}',
              f'<b style="color:{RED if a["samp"] > 0.15 else INK}">{100*a["samp"]:.1f}%</b>', pct(a["fta"]), f'{a["qc_h"]:.0f}',
              f'<b style="color:{RED if a["coq"] > 10 else INK}">{pct(a["coq"])}</b>'] for a in wu_rows[:7]])
    + (p(f'<b>Note on the 16.2% peak (12 Oct):</b> this was QC catching up on a backlog, not higher cost. In Lanes Gaps at DPU GlobalLogic, '
         f'{n(bk["qc"]):,.0f} tasks were QC\'d that week against {n(bk["tasks"]):,.0f} produced.', 12, MUTED, "margin-top:8px") if bk else "")
    + h("Recommended actions")
    + p(f'<b>Coaching the {len(low)} editors under 92% FTA</b> is one action per work unit, with the full list, in section 3. '
        f'Together it could save about <b>{low_save:.0f} QC hours a week</b>.', 13, INK, "margin-bottom:4px")
    + action("Quality Lead, RM Lanes", "Check why sampling stays high where FTA is already 97% or more",
             "; ".join(f'{PT_SHORT[a["pt"]]} at {WU_NAME.get(a["wu"], a["wu"])}: {100*a["samp"]:.0f}% sampled with {pct(a["fta"])} FTA' for a, _ in excess) + ".",
             f'About <b>{excess_h:.0f} QC hours a week</b> if sampling there drops to the normal 12%.', "Wed 28 Oct",
             "Which sampling logic applies to OCC Attr-CC and Hyderabad Attr-Create, and why is sampling above 15%?")
    + action("Quality Lead, RM Lanes", "Keep QC inside the production week for Lanes Gaps",
             "A QC backlog that is cleared in one week shows up as a false CoQ spike (12 Oct) and delays rejection feedback to editors.",
             "Steady CoQ and faster feedback to editors.", "Ongoing",
             "Show QC'd versus produced tasks per week for Lanes Gaps at DPU GlobalLogic")
)

# Finding 2 body
pt2_bl = eff_bl(WEEK, pt2)
slow_h = sum(a["prod_h"] + a["qc_h"] for _, a in slow)
f2 = (
    p(f'Attr-Create Connectivity ran at <b>{pct(pt2_bl, 0)} of its baseline</b> ({pt2_all["eff"]:.2f} tasks per hour against {BL[pt2]:.1f}). '
      f'The alert level is 90%. Volume fell to {pt2_all["tasks"]:,.0f} tasks, from {PTW[("2026-10-05", pt2)]["tasks"]:,.0f} in the week of 5 Oct.')
    + '<img src="cid:eff.png" width="640" style="display:block;width:100%;max-width:640px;margin:10px 0 2px" alt="Efficiency trend">'
    + p("Efficiency as % of each process type's baseline. Weeks with fewer than 50 tasks are left out. Attr-Create swings with its volume; the Lanes Gaps baseline is to be validated.", 11, MUTED)
    + h("Root cause: the work-package mix")
    + table(["Work package", "Tasks", "Hours", "Tasks / h", "vs baseline"],
            [[e(k), f'{a["tasks"]:,.0f}', f'{a["prod_h"] + a["qc_h"]:.0f}', f'{a["eff"]:.2f}' if a["eff"] else "–",
              f'<b style="color:{RED if a["eff"] and 100*a["eff"]/BL[pt2] < 90 else INK}">{pct(100*a["eff"]/BL[pt2], 0) if a["eff"] else "–"}</b>']
             for k, a in wp_rows[:5]])
    + p(f'{" and ".join(e(k) for k, _ in slow)} ran under 80% of baseline and used <b>{100*slow_h/pt2_h:.0f}% of the hours</b>. '
        f'Without them, Attr-Create ran at <b>{pct(100*rest["eff"]/BL[pt2], 0)}</b> of baseline. '
        f'Quality Boost and rework packages are harder per task than the work the baseline was set on.', 13, INK, "margin-top:8px")
    + h("Also affecting every process type")
    + p(f'<b>{notask_h:.0f} production hours</b> were booked with no completed task and no work unit (blank or "Others"): '
        + ", ".join(f'{PT_SHORT[k]} {v:.0f} h' for k, v in sorted(notask.items(), key=lambda kv: -kv[1]))
        + f'. That is {100*notask_h/now["prod_h"]:.1f}% of all production hours, and it lowers efficiency without showing who or what.', 13)
    + p(f'<b>Lanes Gaps reads {pct(eff_bl(WEEK, "orbis-create-lanesgaps"), 0)} of baseline.</b> Its baseline of {BL["orbis-create-lanesgaps"]:.2f} tasks per hour looks out of date, '
        f'so validate it before anyone relies on the figure (OSI-033).', 13, INK, "margin-top:6px")
    + h("Recommended actions")
    + action("Process Engineer with the PM", "Confirm the baseline for Quality Boost and rework packages",
             f'{" and ".join(e(k) for k, _ in slow)} run at {", ".join(pct(100*a["eff"]/BL[pt2], 0) for _, a in slow)} of the Attr-Create baseline.',
             "Efficiency compared like for like, so the alert reflects real slowdowns only.", "Fri 30 Oct",
             "Efficiency by work package for Attr-Create Connectivity, last 4 weeks")
    + action("Operational Leads (all units)", f'Review the {notask_h:.0f} hours booked without a completed task',
             "These hours have no work unit and no output, so they lower efficiency without anyone being able to see why.",
             f'Up to {100*notask_h/now["prod_h"]:.1f}% of production hours explained or rebooked.', "Thu 29 Oct",
             "Production hours with no completed tasks by editor, last week")
)

# Finding 3: per work unit, every editor under 92% FTA and one action with an escalation draft
from urllib.parse import quote

WU_ALL = defaultdict(lambda: {"qc": 0, "rej": 0})
for (pt, wu, ed), v in E.items():
    WU_ALL[wu]["qc"] += v["qc"]; WU_ALL[wu]["rej"] += v["rej"]


def draft_link(wu, eds, unit_fta, save_h):
    """mailto: draft for the unit's escalation (opens a draft only; the lead picks the recipient)."""
    subj = f"RM Lanes: {len(eds)} editors in {WU_NAME.get(wu, wu)} under 92% FTA - coaching plan by Fri 30 Oct"
    lines = [f"Hello,", "",
             f"In the last 4 weeks (28 Sep - 25 Oct), {len(eds)} editors in {WU_NAME.get(wu, wu)} were under 92% FTA on RM Lanes "
             f"(unit FTA {unit_fta:.1f}%). Under the RM Lanes sampling rule their work is QC'd at about 29% instead of 9-12%.", "",
             "Editors (FTA, rejected / QC'd):"]
    lines += [f"- {initials(k[2])} ({PT_SHORT[k[0]]}): {100*(v['qc']-v['rej'])/v['qc']:.1f}%, {v['rej']:.0f} / {v['qc']:.0f}" for k, v in eds[:12]]
    if len(eds) > 12:
        lines.append(f"- and {len(eds) - 12} more (full list in OPS Hub)")
    lines += ["", f"Please share a coaching plan per editor by Fri 30 Oct. Expected benefit: about {save_h:.0f} QC hours a week once they are back above 92%.",
              "", "Regards,", "Lalit"]
    return "mailto:?subject=" + quote(subj) + "&body=" + quote("\r\n".join(lines))


wu_blocks = ""
for wu in sorted(low_by_wu, key=lambda w: -low_by_wu[w]):
    eds = sorted(((k, v) for k, v in low.items() if k[1] == wu), key=lambda kv: (kv[1]["qc"] - kv[1]["rej"]) / kv[1]["qc"])
    rej = sum(v["rej"] for _, v in eds)
    unit_fta = 100 * (WU_ALL[wu]["qc"] - WU_ALL[wu]["rej"]) / WU_ALL[wu]["qc"]
    save_h = sum(v["last_qc_h"] for _, v in eds) * (1 - 12 / 29)
    pts = sorted({PT_SHORT[k[0]] for k, _ in eds})
    wu_blocks += (
        f'<div style="{F};font-size:15px;color:{INK};font-weight:700;margin:16px 0 4px">{WU_NAME.get(wu, wu)} '
        f'<span style="font-weight:400;color:{MUTED};font-size:13px">· {len(eds)} editors · {rej:.0f} of the unit&#39;s {WU_ALL[wu]["rej"]:.0f} rejections '
        f'({100*rej/WU_ALL[wu]["rej"]:.0f}%) · unit FTA {unit_fta:.1f}%</span></div>'
        + table(["Editor", "Process type", "QC'd", "Rejected", "FTA", "Weeks < 92%", "Coach on"],
                [[f'<b>{initials(k[2])}</b>', PT_SHORT[k[0]], f'{v["qc"]:.0f}', f'{v["rej"]:.0f}',
                  f'<b style="color:{RED}">{100*(v["qc"]-v["rej"])/v["qc"]:.1f}%</b>', f'{v["low_weeks"]} of {v["weeks"]}' if v["weeks"] else "–",
                  f'<span style="color:{MUTED}">reason codes ▸</span>'] for k, v in eds],
                ["left", "left", "right", "right", "right", "right", "left"])
        + action(f"Operational Lead, {WU_NAME.get(wu, wu)}",
                 f"Coaching plan for the {len(eds)} editors in {WU_NAME.get(wu, wu)} under 92% FTA",
                 f"They made {100*rej/WU_ALL[wu]['rej']:.0f}% of the unit's rejections ({', '.join(pts)}) and are QC'd at about 29% instead of 9–12%.",
                 f"About <b>{save_h:.0f} QC hours a week</b> for this unit once they are back above 92%.", "Fri 30 Oct",
                 f"Which editors in {WU_NAME.get(wu, wu)} are below 92% FTA on RM Lanes, and what are their rejections about?",
                 extra=btn("✉ Draft escalation email", draft_link(wu, eds, unit_fta, save_h), RED, True))
    )

# Finding 3 body
hy = agg([r for r in d["wu"] if r["week_start"] == WEEK and r["processType"].lower() == "attr-cc-orbisconnectivity" and r["work_unit"] == "dpu hyderabad"])
hy_p = agg([r for r in d["wu"] if r["week_start"] == PREV and r["processType"].lower() == "attr-cc-orbisconnectivity" and r["work_unit"] == "dpu hyderabad"])
f3 = (
    p(f'FTA overall was <b>{pct(now["fta"])}</b> ({delta(prev["fta"], now["fta"])} on the week), above the 95% target. '
      f'One unit is still below target for a second week: <b>Attr-CC at DPU Hyderabad</b>, {pct(hy_p["fta"])} then {pct(hy["fta"])}.')
    + '<img src="cid:fta.png" width="640" style="display:block;width:100%;max-width:640px;margin:10px 0 2px" alt="FTA trend">'
    + h(f"All {len(low)} editors under 92% FTA, by work unit (last 4 weeks)")
    + p(f"Judged on {len(judged)} editors with at least 10 QC'd tasks in the 4 weeks 28 Sep – 25 Oct. Lowest FTA first.", 12, MUTED)
    + wu_blocks
    + p("Editors are shown by initials in this prototype. Full names appear only after the HR check.", 11, MUTED, "margin-top:4px")
    + '<table cellpadding="0" cellspacing="0" style="width:100%;margin-top:10px;border:1px dashed #94a3b8;border-radius:6px"><tr><td style="padding:10px 14px">'
    + p("<b>Next step: what was wrong.</b> The \"Coach on\" column will show each editor's top QC rejection reasons, for example connectivity "
        "direction or a missing lane link. That needs the QC rejection reason codes as a data feed (OSI-027 / OSI-035). They are the only input "
        "in this mail that is not available yet.", 13)
    + "</td></tr></table>"
)

# Also noticed
f4 = (
    p(f'Since 12 Oct, <b>{no_change_n:,} of {st_total:,} tasks ({100*no_change_n/st_total:.0f}%)</b> were closed without a map change. '
      f'They take editor time but produce no output.')
    + table(["Closed as", "Tasks", "Share"],
            [[e(k), f"{v:,}", f"{100*v/st_total:.1f}%"] for k, v in sorted(no_change.items(), key=lambda kv: -kv[1])[:6]])
    + action("PM, RM Lanes, with Product", "Share the no-change closures with Product",
             f'"No source" and "Road construction" alone are {100*(st.get("No source",0)+st.get("Road construction",0))/st_total:.0f}% of tasks.',
             "Fewer tasks generated where no change is possible, so editor time goes to tasks that change the map.", "Next sync",
             "Tasks closed without a map change by work package, last 2 weeks")
)

# action tracker (illustration)
tracker = table(["#", "Action", "Owner", "Due", "Status"],
                [[f"<b>{a}</b>", e(w), e(o.split(",")[0]), du,
                  chip("NEW", BLUE)] for a, o, w, du in ACTIONS],
                ["left", "left", "left", "left", "left"])

feas = table(["In this mail", "Source", "How", "Status"],
             [["Trends and week-on-week change", "Weekly quality and efficiency table", "Code computes them; chart as an image in the mail", chip("READY", GREEN)],
              ["CoQ root cause split", "Same table", "Sampling × QC time ÷ production time", chip("READY", GREEN)],
              ["Why sampling rose", "FTA / QC sampling-logic view", "Sampling band per editor", chip("READY", GREEN)],
              ["Units, work packages, editors", "Weekly table", "Ranking by contribution", chip("READY", GREEN) + " names after HR"],
              ["Closed without a map change", "QC sampling task view", "Task status mix", chip("READY", GREEN)],
              ["What was wrong (reasons)", "QC rejection reason codes", "Top reasons per editor and unit", chip("NEEDS SOURCE", AMBER) + " OSI-027/035"],
              ["Acknowledge / Assign buttons and tracker", "OPS Hub page + store", "One click; status in next mail", chip("TO BUILD", BLUE) + " OSI-007"],
              ["Ask OPS Hub why", "OPS Hub chat", "Pre-filled question per number", chip("TO BUILD", BLUE) + " ~0.5 day"],
              ["Open in Power BI", "Power BI report", "Deep link with filters", chip("NEEDS INPUT", AMBER) + " OSI-039"]],
             ["left", "left", "left", "left"])

stamp = datetime.now().strftime("%d %b %Y, %H:%M IST")
tasks_change = (f'<span style="color:{MUTED};font-weight:600">{now["tasks"] - prev["tasks"]:+,.0f} '
                f'({100 * (now["tasks"] - prev["tasks"]) / prev["tasks"]:+.0f}%)</span>')
body = f"""<html><head><meta charset="utf-8"></head><body style="margin:0;background:#f1f5f9">
<table cellpadding="0" cellspacing="0" style="width:100%;background:#f1f5f9"><tr><td align="center" style="padding:18px 8px">
<table cellpadding="0" cellspacing="0" style="width:720px;max-width:720px;background:#ffffff;border:1px solid {LINE};border-radius:8px">
<tr><td style="background:#fff7ed;border-bottom:1px solid #fed7aa;padding:10px 24px;{F};font-size:13px;color:#9a3412;border-radius:8px 8px 0 0">
<b>PROTOTYPE: the future-state mail for leads.</b> It is not a live mail and nothing was sent to anyone else. It uses real data for RM Lanes, week 19–25 Oct 2026.
Buttons are for illustration.</td></tr>
<tr><td style="padding:18px 24px 6px">
<div style="{F};font-size:12px;color:{RED};font-weight:800;letter-spacing:1px">TOMTOM · OPS NATIVE AI</div>
<div style="{F};font-size:24px;color:{INK};font-weight:800;margin-top:2px">RM Lanes: what changed, why, and what to do</div>
<div style="{F};font-size:13px;color:{MUTED};margin-top:4px">Week 19–25 Oct 2026 (last complete week) · {", ".join(PT_SHORT[pt] for pt in PTS)} · for Lalit Patkar</div>
</td></tr>
<tr><td style="padding:10px 24px 4px"><table cellpadding="0" cellspacing="0" style="width:100%;background:#0f172a;border-radius:6px"><tr><td style="padding:14px 18px">
<div style="{F};font-size:11px;color:#94a3b8;font-weight:700;letter-spacing:.6px">IN 30 SECONDS</div>
<div style="{F};font-size:14px;color:#f8fafc;line-height:1.65;margin-top:4px">
<span style="color:#f87171">●</span> <b>CoQ {pct(now["coq"])}</b> (target 7%), above 10% for {weeks_above} weeks. <b>{share["samp"]:.0f}%</b> of the rise is extra QC sampling, driven by <b>{len(low)} editors under 92% FTA</b>.<br>
<span style="color:#fbbf24">●</span> <b>Attr-Create efficiency {pct(pt2_bl, 0)} of baseline</b>. Two Quality Boost and rework packages at under 80% of baseline used {100*slow_h/pt2_h:.0f}% of the hours.<br>
<span style="color:#4ade80">●</span> <b>FTA {pct(now["fta"])}</b>, up {now["fta"]-prev["fta"]:.1f} points on the week and above target. Attr-CC at Hyderabad is still under 95% for a second week.<br>
<span style="color:#93c5fd">●</span> <b>{len(ACTIONS) if ACTIONS else 6} actions, with owners and due dates.</b> Together they could free about <b>{low_save + excess_h:.0f} QC hours a week</b>.
</div></td></tr></table></td></tr>
<tr><td style="padding:12px 24px 0">{h("Week on week")}
{table(["Metric", "12–18 Oct", "19–25 Oct", "Change", "Target"],
       [["FTA", pct(prev["fta"]), f'<b>{pct(now["fta"])}</b>', delta(prev["fta"], now["fta"]), "95%"],
        ["CoQ", pct(prev["coq"]), f'<b style="color:{RED}">{pct(now["coq"])}</b>', delta(prev["coq"], now["coq"], good_up=False), "7%"],
        ["QC sampling", f'{100*prev["samp"]:.1f}%', f'<b>{100*now["samp"]:.1f}%</b>', delta(100*prev["samp"], 100*now["samp"], good_up=False), "–"]]
       + [[f"Efficiency · {PT_SHORT[pt]}" + (" *" if pt == "orbis-create-lanesgaps" else ""), pct(eff_bl(PREV, pt), 0), f'<b>{pct(eff_bl(WEEK, pt), 0)}</b>', delta(eff_bl(PREV, pt), eff_bl(WEEK, pt), unit=" pts"), "100%"] for pt in PTS]
       + [["Tasks produced", f'{prev["tasks"]:,.0f}', f'<b>{now["tasks"]:,.0f}</b>', tasks_change, "–"]])}
{p("* Lanes Gaps baseline (2.57 tasks per hour) to be validated, see section 2.", 11, MUTED, "margin-top:4px")}
</td></tr>
{section("1 · Cost of Quality", f"CoQ {pct(now['coq'])}: QC sampling is the main driver", "red", f1)}
{section("2 · Efficiency", f"Attr-Create at {pct(pt2_bl, 0)} of baseline: the package mix, not the people", "amber", f2)}
{section("3 · Quality and coaching", f"FTA {pct(now['fta'])}: on target, with {len(low)} editors to coach in {len(low_by_wu)} work units", "green", f3)}
{section("4 · Also noticed", f"{100*no_change_n/st_total:.0f}% of tasks closed without a map change", "blue", f4)}
<tr><td style="padding:14px 24px 4px">{h("Action tracker")}
{tracker}
{p("From next week, this section shows the status of each action (Acknowledged, In progress, Done, Not an issue), how many days it has been open, and whether the number moved after it was done. In this prototype every action is NEW.", 12, MUTED, "margin-top:6px")}
<div style="margin-top:8px">{btn("Open all in OPS Hub →", OPSHUB, BLUE, True)}{btn("Open in Power BI (filtered) →", OPSHUB)}</div>
</td></tr>
<tr><td style="padding:16px 24px 4px"><table cellpadding="0" cellspacing="0" style="width:100%;background:#eff6ff;border-radius:6px"><tr><td style="padding:12px 16px">
{p("<b>Why this mail and not only Power BI?</b> Power BI shows <i>what</i> the numbers are. This mail explains <i>why</i> they moved, how much each cause contributes, who should act and by when, and from next week whether the action worked. The numbers are the same as in Power BI, from the same tables.", 13)}
</td></tr></table></td></tr>
<tr><td style="padding:14px 24px 6px">{h("How this mail is built: technical feasibility")}{feas}</td></tr>
<tr><td style="padding:14px 24px 20px;{F};font-size:11px;color:{MUTED};line-height:1.5;border-top:1px solid {LINE}">
Data: Databricks (manual efficiency and quality weekly table, FTA/QC sampling-logic view, QC sampling task view), extracted on 27 Oct 2026; mail built {stamp}. Code computes every number;
no figure is generated by AI. Prototype from OPS Native AI, sent only to {TO}.
</td></tr>
</table></td></tr></table></body></html>"""

(HERE / "mail.html").write_text(body, encoding="utf-8")
(HERE / "preview.html").write_text(body.replace('src="cid:', 'src="'), encoding="utf-8")
SUBJECT = "[PROTOTYPE] RM Lanes · root cause and actions · week 19–25 Oct (future-state mail)"
print("built", len(body) // 1024, "KB;", len(ACTIONS), "actions; low editors", len(low), "; save", round(low_save), "+", round(excess_h))

if "--send" in sys.argv:
    import win32com.client
    ol = win32com.client.Dispatch("Outlook.Application")
    m = ol.CreateItem(0)
    m.To = TO
    m.Subject = SUBJECT
    m.BodyFormat = 2
    for name in ("coq.png", "eff.png", "fta.png"):
        att = m.Attachments.Add(str(HERE / name))
        att.PropertyAccessor.SetProperty("http://schemas.microsoft.com/mapi/proptag/0x3712001F", name)
    m.HTMLBody = body
    assert m.To.strip().lower() == TO and not m.CC and not m.BCC
    m.Send()
    print("sent to", TO)
