"""Root causes and actions for a KPI that misses its level (OSI-027 / 035 / 040 / 047).

Rule-based, no AI call (so no token cost, OSI-049): the same checks the 28 Oct prototype lead mail made by
hand, run on the reported week of the KPI table for the profile's scope.

- FTA: who makes the rejections. Few editors with most of the rejections -> coaching, by work unit;
  rejections spread over many editors in one work package -> instructions, specs or data for that package.
- CoQ: a driver tree against the previous full week: more rejections (rework QC'd again), more sampling,
  slower QC (minutes per QC'd task) or faster production, one action per driver; FTA up while sampling went
  up too; high-FTA areas still sampled heavily; QC time spent on low-FTA editors.
- Efficiency: the work packages that lose the most hours against their process type's baseline, and hours
  booked with no completed task.
- Yield: the work unit with the lowest yield.

Inputs are the row dicts loaded by analytics_agent (editor rows and work-package rows of one week, the
4-week totals, the baselines, the work-unit breakdown). Output is plain data plus short HTML-safe texts
that email_html puts in the "Root causes and actions" box. Editors are counted, never named, here: names
stay in the operator section, which only leads get (HR check still open, OSI-009).

Not available yet, so the result says it: the error types behind rejections need the ORBIT QC feedback
categories, which no table we read holds.
"""
from __future__ import annotations

import html as _html
import math
from collections import defaultdict

MIN_QC_EDITOR = 10        # an editor's FTA is judged from 10 QC'd tasks (same as the operator section)
MIN_QC_AREA = 20          # a work package / work unit needs 20 QC'd tasks before it is named
MIN_TASKS_WP = 20         # a work package needs 20 tasks before its efficiency is named
SLOW_WP_PCT = 80.0        # a work package below 80% of its baseline is "slow"
OVERSAMPLED_FTA = 97.0    # FTA at or above this ...
OVERSAMPLED_RATE = 15.0   # ... while sampled at or above this % -> candidate for lower sampling
CONCENTRATED_SHARE = 50.0  # low-FTA editors making at least half the rejections -> coaching
MIX_RATIO = 3.0          # a CoQ factor moving more than 3x week on week = a different work mix
SPREAD_EDITORS = 3        # a work package with low FTA across 3+ editors -> look at the package, not the people

ERROR_TYPES_NOTE = ("Error types behind the rejections are not available yet: they need the QC feedback "
                    "categories from ORBIT (OSI-027).")
EDITS_NOTE = ("The share of tasks closed with a map edit is only known for Orbit SD work (yield view), so this "
              "step is not confirmed from data here.")


def _b(x) -> str:
    """Bold, HTML-escaped."""
    return f"<b>{_html.escape(str(x))}</b>"


def _e(x) -> str:
    """HTML-escaped text."""
    return _html.escape(str(x if x is not None else ""))


def _f(r: dict, k: str) -> float:
    """Number from a row, 0 when missing."""
    try:
        return float(r.get(k) or 0)
    except (TypeError, ValueError):
        return 0.0


def _pct(a: float, b: float) -> float | None:
    """a / b as a percentage, None when b is 0."""
    return a * 100.0 / b if b else None


def _wu(name: str) -> str:
    """Display name of a work unit (same names as the work-unit table)."""
    from analytics_agent import wu_name   # late import: analytics_agent imports this module
    # rows with no work unit in Databricks: say so, "Not assigned" read like a team (30 Oct)
    return wu_name(name) if (name or "").strip() else "work unit not recorded"


# ── FTA ─────────────────────────────────────────────────────────────────────────────────────────────

def fta_causes(editors: list[dict], wps: list[dict], level: float) -> dict:
    """Who and where the rejections come from in the reported week.

    `editors`: rows {pt, wu, editor, qc, acc}; `wps`: rows {pt, wu, wp, qc, acc, eds}; `level`: the FTA alert
    level used for editors. Returns counts, the share of rejections made by editors below the level, their
    split by work unit, whether the problem is concentrated (coaching) or spread (work package), and the work
    packages with low FTA across several editors."""
    rej_all = sum(_f(e, "qc") - _f(e, "acc") for e in editors)
    judged = [e for e in editors if _f(e, "qc") >= MIN_QC_EDITOR]
    low = [e for e in judged if _pct(_f(e, "acc"), _f(e, "qc")) < level]
    low_rej = sum(_f(e, "qc") - _f(e, "acc") for e in low)
    by_wu: dict[str, dict] = defaultdict(lambda: {"editors": 0, "rej": 0.0, "qc": 0.0})
    for e in low:
        g = by_wu[e.get("wu") or ""]
        g["editors"] += 1
        g["rej"] += _f(e, "qc") - _f(e, "acc")
        g["qc"] += _f(e, "qc")
    wu_rows = sorted(({"work_unit": k, **v, "share": _pct(v["rej"], rej_all)} for k, v in by_wu.items()),
                     key=lambda r: -r["rej"])
    share = _pct(low_rej, rej_all) or 0.0
    # Work packages where several editors fail: points at the package (instructions, specs, data), not people.
    pkg = []
    for w in wps:
        qc, acc, eds = _f(w, "qc"), _f(w, "acc"), _f(w, "eds")
        fta = _pct(acc, qc)
        if qc >= MIN_QC_AREA and fta is not None and fta < level and eds >= SPREAD_EDITORS:
            pkg.append({"wp": w.get("wp") or "", "pt": w.get("pt") or "", "wu": w.get("wu") or "",
                        "fta": fta, "qc": qc, "rej": qc - acc, "eds": int(eds)})
    pkg.sort(key=lambda r: -r["rej"])
    return {"rejections": int(rej_all), "judged": len(judged), "low": len(low), "low_rej": int(low_rej),
            "low_share": share, "by_wu": wu_rows,
            "concentrated": bool(low) and share >= CONCENTRATED_SHARE,
            "packages": pkg[:3], "level": level}


def fta_change(cur: list[dict], prev: list[dict], level: float, edited: dict | None = None
               ) -> tuple[list[str], list[str]]:
    """Why FTA moved against the previous full week: a driver tree like CoQ's (causes, more actions).

    - Where: the work units whose rejections changed most (rejections, QC'd and FTA, then vs now).
    - The sample: FTA is measured on the QC'd sample only. When more of the sample comes from editors who were
      already below the level the week before (the sampling rule sends more of their work to QC), reported FTA
      drops although nobody got worse; the same editors' own FTA tells the two apart.
    - Edits: more tasks closed with a map edit means more chances of a rejection (Orbit SD only)."""
    def tot(rows):
        q = sum(_f(r, "qc") for r in rows)
        return q, q - sum(_f(r, "acc") for r in rows)
    q1, r1 = tot(prev)
    q2, r2 = tot(cur)
    if q1 < MIN_QC_AREA or q2 < MIN_QC_AREA:
        return [], []
    f1, f2 = 100 * (q1 - r1) / q1, 100 * (q2 - r2) / q2
    causes, more = [], []
    if abs(f2 - f1) < 0.3:
        return [f"FTA is about the same as the previous full week ({f1:.1f}% → {f2:.1f}%)."], []
    word = "fell" if f2 < f1 else "rose"
    causes.append(f"Against the previous full week FTA {word} from {f1:.1f}% to {f2:.1f}% "
                  f"({int(r1)} → {int(r2)} rejections on {int(q1):,} → {int(q2):,} QC'd).")
    # where: rejection rate change per work unit, weighted by its share of this week's sample
    g: dict[str, list] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])   # q1, r1, q2, r2
    for rows, i in ((prev, 0), (cur, 2)):
        for r in rows:
            k = r.get("wu") or ""
            g[k][i] += _f(r, "qc")
            g[k][i + 1] += _f(r, "qc") - _f(r, "acc")
    moves = []
    for k, (a1, b1, a2, b2) in g.items():
        if a1 >= MIN_QC_AREA and a2 >= MIN_QC_AREA:
            effect = (b2 / a2 - b1 / a1) * a2 / q2 * 100   # FTA points this unit moved the total by
            moves.append((effect, k, 100 * (a1 - b1) / a1, 100 * (a2 - b2) / a2))
    moves.sort(key=lambda m: -m[0] if f2 < f1 else m[0])
    top = [m for m in moves if (m[0] > 0.1 if f2 < f1 else m[0] < -0.1)][:3]
    if top:
        causes.append("Where: " + "; ".join(f"{_e(_wu(k))} FTA {a:.1f}% → {b:.1f}% ({abs(e):.1f} pts of the total)"
                                            for e, k, a, b in top) + ".")
    # the sample: share of QC'd tasks from editors already below the level last week
    key = lambda r: (r.get("pt"), r.get("wu"), r.get("editor"))
    was_low = {key(r) for r in prev if _f(r, "qc") >= MIN_QC_EDITOR and _pct(_f(r, "acc"), _f(r, "qc")) < level}
    if was_low:
        s1 = sum(_f(r, "qc") for r in prev if key(r) in was_low) * 100 / q1
        s2 = sum(_f(r, "qc") for r in cur if key(r) in was_low) * 100 / q2
        q_low = sum(_f(r, "qc") for r in cur if key(r) in was_low)
        r_low = sum(_f(r, "qc") - _f(r, "acc") for r in cur if key(r) in was_low)
        fta_rest = _pct(sum(_f(r, "acc") for r in cur if key(r) not in was_low), q2 - q_low)
        if f2 < f1 and s2 > s1 + 2 and fta_rest is not None and fta_rest >= f1 - 0.3:
            causes.append(f"Chain: more of the sample came from editors already below {level:g}% last week "
                          f"({s1:.0f}% → {s2:.0f}% of QC'd tasks) → the sampling rule sends more of their work to QC → "
                          f"reported FTA drops. The other editors are at {fta_rest:.1f}%, so overall quality did "
                          "not get worse.")
            more.append("Read the drop as a sampling effect, not a quality drop: coaching those editors fixes both.")
        elif q_low:
            causes.append(f"Editors below {level:g}% last week made {int(r_low)} of this week's {int(r2)} rejections "
                          f"({s2:.0f}% of the QC'd tasks).")
    if edited and f2 < f1 and edited["cur"] > edited["prev"] + 2:
        causes.append(f"Chain: more tasks closed with a map edit ({edited['prev']:.0f}% → {edited['cur']:.0f}% of "
                      "completed tasks) → more edits per week → more chances of a rejection.")
    return causes, more


def fta_texts(c: dict, has_operator_section: bool) -> tuple[str, list[str], list[str]]:
    """(main action, causes, more actions) for the FTA item, from fta_causes()."""
    causes, more = [], []
    if c["rejections"] <= 0:
        return "", [], []
    if c["low"]:
        wus = ", ".join(f"{_e(_wu(w['work_unit']))} {w['editors']}" for w in c["by_wu"][:4])
        share = f"{c['low_share']:.0f}%"
        causes.append(f"{_b(c['low'])} of {c['judged']} editors are below {c['level']:g}% FTA and made "
                      f"{_b(share)} of the {c['rejections']:,} rejections (by work unit: {wus}).")
    for p in c["packages"]:
        causes.append(f"Work package {_b(p['wp'])} ({_e(p['pt'])}, {_e(_wu(p['wu']))}): FTA {p['fta']:.1f}% across "
                      f"{p['eds']} editors, {int(p['rej'])} rejections. Several editors failing on the same package "
                      "points at its instructions, specs or data rather than at the editors.")
    where = " Names are in the operator section below." if has_operator_section else ""
    if c["concentrated"]:
        top = c["by_wu"][0]
        action = (f"Coach the {c['low']} editors below {c['level']:g}% FTA, starting with "
                  f"{_e(_wu(top['work_unit']))} ({top['editors']} editors, {top['share'] or 0:.0f}% of rejections){where}")
        if c["packages"]:
            more.append(f"Review the instructions for {_e(c['packages'][0]['wp'])} with QC.")
    elif c["packages"]:
        p = c["packages"][0]
        action = (f"Review the instructions, specs and source data of work package {_e(p['wp'])} with QC: "
                  f"rejections there are spread over {p['eds']} editors")
        if c["low"]:
            more.append(f"Coach the {c['low']} editors below {c['level']:g}% FTA.{where}")
    elif c["low"]:
        action = f"Coach the {c['low']} editors below {c['level']:g}% FTA{where}"
    else:
        action = "Rejections are spread thinly; ask QC for the most common rejection reasons this week"
    more.append("Ask QC for the top rejection reasons on these areas. " + ERROR_TYPES_NOTE)
    return action, causes, more


# ── CoQ ─────────────────────────────────────────────────────────────────────────────────────────────

def coq_drivers(cur: dict, prev: dict) -> dict | None:
    """Why CoQ moved between two weeks of totals {prod_tasks, total_qc, accepted, prod_hrs, qc_hrs}: a driver tree.

    QC hours / production hours = (QC'd per produced task) x (QC minutes per QC'd task / production minutes
    per task), so the change of that ratio splits exactly into log terms. The QC'd-per-task term is split again
    by the change of its two parts: rejected tasks (each one is reworked and QC'd again) and accepted ones
    (the sampling itself). Drivers: rejections, sampling, qc_speed (slower QC), production_speed.
    `fta_up_sampling_up` marks the case where FTA improved and sampling still rose. None when a week lacks a
    factor."""
    def parts(w):
        t, q, ph, qh = (_f(w, k) for k in ("prod_tasks", "total_qc", "prod_hrs", "qc_hrs"))
        if min(t, q, ph, qh) <= 0:
            return None
        acc = _f(w, "accepted") if w.get("accepted") is not None else q
        return {"samp": 100 * q / t, "rej_rate": 100 * (q - acc) / q, "fta": 100 * acc / q,
                "rej_per_task": (q - acc) / t, "acc_per_task": acc / t,
                "qc_min": 60 * qh / q, "prod_min": 60 * ph / t, "coq": 100 * qh / (ph + qh)}
    a, b = parts(prev or {}), parts(cur or {})
    if not a or not b:
        return None
    qc_term = math.log(b["samp"] / a["samp"])
    d_rej, d_acc = b["rej_per_task"] - a["rej_per_task"], b["acc_per_task"] - a["acc_per_task"]
    den = abs(d_rej) + abs(d_acc)
    # split the QC'd-per-task change between rejections and sampling in proportion to their own change
    rej_term = qc_term * d_rej / (d_rej + d_acc) if (d_rej + d_acc) else 0.0
    if den and (d_rej + d_acc) == 0:
        rej_term = 0.0
    terms = {"rejections": rej_term, "sampling": qc_term - rej_term,
             "qc_speed": math.log(b["qc_min"] / a["qc_min"]),
             "production_speed": -math.log(b["prod_min"] / a["prod_min"])}
    total = sum(terms.values())
    # Shares only make sense when every driver pushes the same way as the total.
    same_way = total != 0 and all(abs(v) < 1e-9 or (v > 0) == (total > 0) for v in terms.values())
    shares = {k: 100 * v / total for k, v in terms.items()} if same_way else None
    # drivers smaller than 5% of the move are noise and not listed
    pushing = sorted((k for k, v in terms.items() if abs(v) >= max(1e-9, 0.05 * abs(total)) and (v > 0) == (total > 0)),
                     key=lambda k: -abs(terms[k]))
    # A factor that moved more than 3x means different work, not the same work done differently (Devika,
    # 30 Oct: production 69 -> 8 min per task after small address-point tasks came in): the split would
    # mislead, so the texts explain the level instead.
    mix = any(not (1 / MIX_RATIO <= b[k] / a[k] <= MIX_RATIO) for k in ("samp", "qc_min", "prod_min"))
    return {"prev": a, "cur": b, "terms": terms, "shares": shares, "order": pushing, "mix": mix,
            "main": pushing[0] if pushing else None, "rising": total > 0, "flat": abs(total) < 0.03,
            "fta_up_sampling_up": b["fta"] > a["fta"] + 0.2 and b["samp"] > a["samp"] * 1.03}


def _cap(s: str) -> str:
    """First letter upper case."""
    return s[:1].upper() + s[1:]


_COQ_FACT = {
    "rejections": lambda p, c: (f"more rejections: {100 * p['rej_per_task']:.1f} → {100 * c['rej_per_task']:.1f} "
                                f"per 100 produced tasks (FTA {p['fta']:.1f}% → {c['fta']:.1f}%), each one reworked "
                                "and QC'd again"),
    "sampling": lambda p, c: f"more sampling: {p['samp']:.1f}% → {c['samp']:.1f}% of produced tasks QC'd",
    "qc_speed": lambda p, c: f"slower QC: {p['qc_min']:.1f} → {c['qc_min']:.1f} QC minutes per QC'd task",
    "production_speed": lambda p, c: (f"faster production: {p['prod_min']:.1f} → {c['prod_min']:.1f} minutes per "
                                      "task, so the same QC weighs more"),
}
_COQ_FACT_DOWN = {
    "rejections": lambda p, c: (f"fewer rejections: {100 * p['rej_per_task']:.1f} → {100 * c['rej_per_task']:.1f} "
                                "per 100 produced tasks, so less rework to QC again"),
    "sampling": lambda p, c: f"less sampling: {p['samp']:.1f}% → {c['samp']:.1f}%",
    "qc_speed": lambda p, c: f"faster QC: {p['qc_min']:.1f} → {c['qc_min']:.1f} min per QC'd task",
    "production_speed": lambda p, c: f"slower production: {p['prod_min']:.1f} → {c['prod_min']:.1f} min per task",
}
_COQ_ACTION = {
    "rejections": ("Cut the rework first: fix the rejections behind it (see the FTA causes: coach the low-FTA "
                   "editors or fix the work package)"),
    "sampling": ("Review the sampling: more tasks went to QC than in the previous week; check the sampling rule "
                 "and lower it where FTA is high"),
    "qc_speed": ("Find out why QC takes longer per task: new or changed checks, tool or data issues, new QC staff, "
                 "harder tasks"),
    "production_speed": ("Production got faster per task, so the same QC weighs more: check that the QC sample "
                         "and checks still fit this work"),
}


def oversampled(wps: list[dict]) -> list[dict]:
    """Process type x work unit areas with FTA >= 97% that are still sampled at 15% or more, most QC hours first."""
    g: dict[tuple, dict] = defaultdict(lambda: {"qc": 0.0, "acc": 0.0, "tasks": 0.0, "qc_h": 0.0})
    for w in wps:
        k = (w.get("pt") or "", w.get("wu") or "")
        for f in ("qc", "acc", "tasks", "qc_h"):
            g[k][f] += _f(w, f)
    out = []
    for (pt, wu), v in g.items():
        fta, rate = _pct(v["acc"], v["qc"]), _pct(v["qc"], v["tasks"])
        if v["qc"] >= MIN_QC_AREA and fta is not None and rate is not None and fta >= OVERSAMPLED_FTA \
                and rate >= OVERSAMPLED_RATE:
            out.append({"pt": pt, "wu": wu, "fta": fta, "rate": rate, "qc_h": v["qc_h"]})
    return sorted(out, key=lambda r: -r["qc_h"])[:3]


def coq_level(cur: dict | None, target: float) -> str:
    """Why CoQ is at its level (not why it moved): with the week's QC and production minutes per task, the
    sampling that would bring CoQ to the target. CoQ = s*q / (p + s*q) for sampling s, QC minutes q and
    production minutes p, so s = target/(1-target) * p/q. Empty when already at or below the target."""
    if not cur or cur["coq"] <= target:
        return ""
    t = target / 100
    need = 100 * t / (1 - t) * cur["prod_min"] / cur["qc_min"]
    return (f"Why it is at {cur['coq']:.1f}%: {cur['samp']:.1f}% of tasks are QC'd, at {cur['qc_min']:.1f} QC minutes "
            f"each against {cur['prod_min']:.1f} production minutes per task. At these times, CoQ reaches "
            f"{target:g}% with about {_b(f'{need:.0f}%')} sampling, or with QC at about "
            f"{t / (1 - t) * cur['prod_min'] * 100 / cur['samp']:.1f} minutes per task at today's sampling.")


def coq_texts(d: dict | None, over: list[dict], low_qc_h: float, total_qc_h: float, level: float,
              edited: dict | None = None) -> tuple[str, list[str], list[str]]:
    """(main action, causes, more actions) for the CoQ item: the driver tree from coq_drivers, FTA up while
    sampling went up too, the over-sampled areas, and the QC time spent on low-FTA editors."""
    causes, more = [], []
    action = ""
    if d and d.get("mix"):
        p, c = d["prev"], d["cur"]
        causes.append(f"Against the previous full week CoQ {'rose' if d['rising'] else 'fell'} from {p['coq']:.1f}% to "
                      f"{c['coq']:.1f}%, but the work mix changed a lot (production {p['prod_min']:.1f} → "
                      f"{c['prod_min']:.1f} min per task, QC {p['qc_min']:.1f} → {c['qc_min']:.1f} min, sampling "
                      f"{p['samp']:.0f}% → {c['samp']:.0f}%), so a week-on-week split would mislead. What matters is "
                      "the level below.")
    elif d and not d["flat"]:
        p, c = d["prev"], d["cur"]
        word = "rose" if d["rising"] else "fell"
        causes.append(f"Against the previous full week CoQ {word} from {p['coq']:.1f}% to {c['coq']:.1f}%.")
        facts = _COQ_FACT if d["rising"] else _COQ_FACT_DOWN
        listed = d["order"] if d["rising"] else [k for k, v in sorted(d["terms"].items(), key=lambda kv: kv[1])
                                                  if v < -max(1e-9, 0.05 * abs(sum(d["terms"].values())))]
        for k in listed:
            share = f" ({d['shares'][k]:.0f}% of the change)" if d["shares"] and abs(d["shares"][k]) >= 1 else ""
            causes.append(_cap(facts[k](p, c)) + share + ".")
        if d["rising"] and d["main"]:
            action = _COQ_ACTION[d["main"]]
            more += [_COQ_ACTION[k] + "." for k in d["order"][1:2]]
        t = d["terms"]
        # The two chains leads use to read a high CoQ (29 Oct):
        # 1) higher rejection -> lower FTA -> the sampling rule QCs more -> more QC hours -> higher CoQ;
        # 2) more edits per task -> more QC time per task -> higher CoQ.
        if d["rising"] and t["rejections"] > 0 and t["sampling"] > 0:
            causes.append(f"Chain: more rejections (FTA {p['fta']:.1f}% → {c['fta']:.1f}%) → the sampling rule "
                          "sends more of the low-FTA editors' work to QC → more QC hours → higher CoQ. Fixing FTA "
                          "brings the sampling down by itself.")
        if d["rising"] and t["qc_speed"] > 0:
            if edited and edited["cur"] > edited["prev"] + 2:
                causes.append(f"Chain: more tasks closed with a map edit (Publish / Accepted): {edited['prev']:.0f}% → "
                              f"{edited['cur']:.0f}% of completed tasks → every edited task needs a full QC (and "
                              "Logic 2–4 double the sampling at Publish / Accepted) → more QC time → higher CoQ.")
                more.append("More edited tasks is real work, not a quality problem: plan QC capacity for it rather "
                            "than cutting checks.")
            elif edited:
                causes.append(f"Tasks closed with a map edit stayed about the same ({edited['prev']:.0f}% → "
                              f"{edited['cur']:.0f}%), so the longer QC is not from more edited tasks: look at the "
                              "checks, the tool or the QC staff.")
            else:
                causes.append("Chain: more QC minutes per task → usually more edits per task or harder tasks → more "
                              "QC time → higher CoQ. " + EDITS_NOTE)
        if d["fta_up_sampling_up"]:
            causes.append(f"FTA improved ({p['fta']:.1f}% → {c['fta']:.1f}%) but sampling still went up "
                          f"({p['samp']:.1f}% → {c['samp']:.1f}%): sampling is not following the better quality.")
            more.append("Check why sampling went up while FTA improved: the sampling rule should lower it.")
    if over:
        names = "; ".join(f"{_e(o['pt'])} / {_e(_wu(o['wu']))} (FTA {o['fta']:.1f}%, sampled {o['rate']:.0f}%, "
                          f"{o['qc_h']:,.0f} QC h)" for o in over)
        causes.append(f"High-FTA areas still sampled heavily: {names}.")
        if action:
            more.append("Lower the sampling for the high-FTA areas above, if the sampling rule allows it.")
        else:
            action = "Lower the sampling for the high-FTA areas named below, if the sampling rule allows it"
    if low_qc_h > 0 and total_qc_h > 0:
        causes.append(f"{_b(f'{low_qc_h:,.0f} QC h')} ({low_qc_h * 100 / total_qc_h:.0f}% of QC time) went to "
                      f"editors below {level:g}% FTA; better first-time quality there also cuts QC and rework.")
    if not action and causes and not (d and d.get("mix")):   # a mix change gets its action from the level
        action = "Find where QC and rework time goes: check for over-sampling or repeated rework"
    return action, causes, more


# ── Efficiency ──────────────────────────────────────────────────────────────────────────────────────

def slow_packages(wps: list[dict], baselines: dict[str, float]) -> tuple[list[dict], float]:
    """Work packages below 80% of their process type's baseline, most hours lost first; and all hours lost.
    Hours lost = hours booked - tasks / baseline (tasks per hour)."""
    slow, lost_all = [], 0.0
    for w in wps:
        bl = baselines.get((w.get("pt") or "").lower())
        tasks, hrs = _f(w, "tasks"), _f(w, "prod_h") + _f(w, "qc_h")
        if not bl or hrs <= 0 or tasks <= 0:
            continue
        lost = hrs - tasks / bl
        lost_all += max(lost, 0)
        eff = 100 * (tasks / hrs) / bl
        if tasks >= MIN_TASKS_WP and eff < SLOW_WP_PCT:
            slow.append({"wp": w.get("wp") or "", "pt": w.get("pt") or "", "wu": w.get("wu") or "",
                         "eff": eff, "hrs": hrs, "lost": lost, "tasks": tasks})
    slow.sort(key=lambda r: -r["lost"])
    return slow[:3], lost_all


def idle_hours(wps: list[dict]) -> list[dict]:
    """Hours booked with no completed task, by process type x work unit, most first."""
    g: dict[tuple, float] = defaultdict(float)
    for w in wps:
        g[(w.get("pt") or "", w.get("wu") or "")] += _f(w, "idle_h")
    return [{"pt": k[0], "wu": k[1], "hrs": v} for k, v in sorted(g.items(), key=lambda kv: -kv[1]) if v >= 1][:3]


def eff_texts(slow: list[dict], lost_all: float, idle: list[dict]) -> tuple[str, list[str], list[str]]:
    """(main action, causes, more actions) for the efficiency item."""
    causes, more, action = [], [], ""
    if slow:
        names = "; ".join(f"{_b(s['wp'])} ({_e(s['pt'])}, {_e(_wu(s['wu']))}: {s['eff']:.0f}% of baseline, "
                          f"{s['lost']:,.0f} h lost)" for s in slow)
        share = f", {sum(s['lost'] for s in slow) * 100 / lost_all:.0f}% of the {lost_all:,.0f} h lost in the scope" \
            if lost_all > 0 else ""
        causes.append(f"Slowest work packages against their baseline: {names}{share}.")
        action = (f"Check work package {_e(slow[0]['wp'])} for blockers (tools, data, complexity, new editors); "
                  "if it is different work, ask for its own baseline")
    if idle:
        tot = sum(i["hrs"] for i in idle)
        names = "; ".join(f"{_e(i['pt'])} / {_e(_wu(i['wu']))} {i['hrs']:,.0f} h" for i in idle)
        causes.append(f"{_b(f'{tot:,.0f} h')} booked with no completed task: {names}.")
        if action:
            more.append("Check the hours booked with no completed task: blocked, unfinished or wrongly booked work.")
        else:
            action = "Check the hours booked with no completed task: blocked, unfinished or wrongly booked work"
    return action, causes, more


# ── Yield ───────────────────────────────────────────────────────────────────────────────────────────

def yield_texts(workunits: list[dict], target: float) -> tuple[str, list[str], list[str]]:
    """(main action, causes, more actions) for yield: work units below the target, lowest first."""
    low = sorted((w for w in workunits or [] if w.get("yield_pct") is not None and w["yield_pct"] < target
                  and (w.get("total_qc") or 0) >= MIN_QC_AREA), key=lambda w: w["yield_pct"])[:3]
    if not low:
        return "", [], []
    names = "; ".join(f"{_e(_wu(w.get('work_unit')))} {w['yield_pct']:.1f}%" for w in low)
    return (f"Check why tasks in {_e(_wu(low[0].get('work_unit')))} go back to production before completion",
            [f"Lowest yield by work unit: {names}."], [])


# ── All together ────────────────────────────────────────────────────────────────────────────────────

def analyse(editors: list[dict], wps: list[dict], metrics_4w: list[dict], baselines: dict[str, float],
            workunits: list[dict], fta_level: float, yield_target: float, has_operator_section: bool,
            edited: dict | None = None, coq_target: float = 7.0) -> dict:
    """Root causes and actions for every KPI, for email_html to show where a KPI misses its level.

    `editors` holds the reported week and the week before (column "week"); rows without a week count as the
    reported week. Returns {metric: {"action": str, "causes": [str], "more": [str]}} for fta, coq, efficiency
    and yield (a metric is left out when nothing can be said), plus "partial": what is not available yet."""
    out: dict = {}
    weeks = sorted({str(e.get("week") or "")[:10] for e in editors if e.get("week")})
    this = weeks[-1] if weeks else ""
    prev_eds = [e for e in editors if e.get("week") and str(e["week"])[:10] != this]
    editors = [e for e in editors if not e.get("week") or str(e["week"])[:10] == this]
    fc = fta_causes(editors, wps, fta_level)
    a, c, m = fta_texts(fc, has_operator_section)
    if a:
        ch_c, ch_m = fta_change(editors, prev_eds, fta_level, edited)
        out["fta"] = {"action": a, "causes": ch_c + c, "more": ch_m + m, "facts": fc}
    cur, prev = (metrics_4w[0] if metrics_4w else {}), (metrics_4w[1] if len(metrics_4w) > 1 else {})
    low_keys = {(e.get("pt"), e.get("wu"), e.get("editor")) for e in editors
                if _f(e, "qc") >= MIN_QC_EDITOR and _pct(_f(e, "acc"), _f(e, "qc")) < fta_level}
    low_qc_h = sum(_f(e, "qc_h") for e in editors if (e.get("pt"), e.get("wu"), e.get("editor")) in low_keys)
    total_qc_h = sum(_f(e, "qc_h") for e in editors)
    d = coq_drivers(cur, prev)
    a, c, m = coq_texts(d, oversampled(wps), low_qc_h, total_qc_h, fta_level, edited)
    lv = coq_level(d["cur"] if d else None, coq_target)
    if lv:
        c.insert(1 if d and (d.get("mix") or not d["flat"]) else 0, lv)
        if d and d.get("mix") and not a:
            a = (f"Review the sampling: {d['cur']['samp']:.0f}% of tasks are QC'd; see below what would bring CoQ "
                 f"to {coq_target:g}%")
    if a:
        out["coq"] = {"action": a, "causes": c, "more": m}
    slow, lost = slow_packages(wps, baselines)
    a, c, m = eff_texts(slow, lost, idle_hours(wps))
    if a:
        out["efficiency"] = {"action": a, "causes": c, "more": m}
    a, c, m = yield_texts(workunits, yield_target)
    if a:
        out["yield"] = {"action": a, "causes": c, "more": m}
    out["partial"] = ERROR_TYPES_NOTE
    return out
