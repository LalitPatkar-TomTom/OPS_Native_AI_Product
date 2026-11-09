"""
Delivery forecast ("Ops Weather") — when will each pending work package and OM ticket be done at today's pace.

Rules only, no LLM (ADR-001). Read-only Databricks: one SELECT over two tables.
  Pending:  mo_occ_reporting.manual_efficiency.project_pending_task_tbl (a snapshot: no date column)
  Pace:     the weekly KPI table, last 4 full weeks (tasks done, hours booked, editors)

Grouped by WORK PACKAGE and OM ticket, never by process type (user, 6 Nov 2026):
  work days = pending tasks / (tasks per hour x editors' hours per day) = pending / tasks done per work day.
  1. the work package's own pace when it did at least TRICKLE_TASKS tasks in the 4 weeks;
  2. else its OM ticket's pace: the WP is done when the OM is (all of the OM's pending / the OM's pace);
  3. else "trickle" (some work, too little to forecast) or "stalled" (no editor in 4 weeks) — no number.
ADP, training and pilot process types are left out (user, 9 Nov 2026). Decision: ADR-014.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

PENDING_TABLE = "mo_occ_reporting.manual_efficiency.project_pending_task_tbl"
PACE_WEEKS    = 4
WORK_DAYS     = PACE_WEEKS * 5
# Below this many tasks in 4 weeks a pace gives absurd forecasts (1 task in 4 weeks = 674,840 days on 9 Nov
# data), so the row says "trickle" instead of a number.
TRICKLE_TASKS = 50
SUNNY_DAYS    = 20    # done within about a month of work days
CLOUDY_DAYS   = 60    # within about a quarter
# Beyond about a year of work days a precise figure (5,134 for OM-337351 on 9 Nov) reads as exact when it really
# means "not at this pace", so the email shows "> 1 year" (user, 9 Nov 2026: the PM must understand the number).
CAP_DAYS      = 250

BANDS = {             # key: (symbol, label) — HTML entities so Outlook shows them in every code page
    "sunny":   ("&#9728;&#65039;",  "Done within 20 work days"),
    "cloudy":  ("&#9925;",          "21–60 work days"),
    "rainy":   ("&#127783;&#65039;", "More than 60 work days"),
    "trickle": ("&#9928;&#65039;",  f"Trickle: under {TRICKLE_TASKS} tasks in 4 weeks"),
    "stalled": ("&#9928;&#65039;",  "No editor in 4 weeks"),
}

# One OM key per WP: DeliverableID, else "OM-nnnnnn" in the WP name (845 of 2,199 IRIS WPs carry it there).
_OM_FROM_NAME = ("CASE WHEN {c} RLIKE '(?i)OM[-_ ]?[0-9]{{4,}}' "
                 "THEN CONCAT('OM-', REGEXP_EXTRACT({c}, '(?i)OM[-_ ]?([0-9]{{4,}})', 1)) END")
_EXCLUDED_PT  = ("(COALESCE(LOWER(ProcessType), '') = 'adp' OR LOWER(ProcessType) LIKE '%train%' "
                 "OR LOWER(ProcessType) LIKE '%pilot%')")


def pace_weeks(today: date) -> tuple[str, str]:
    """First and last Monday of the last PACE_WEEKS full weeks before today's week (the running week is
    partial, so it would understate the pace)."""
    monday = today - timedelta(days=today.weekday())
    return (str(monday - timedelta(weeks=PACE_WEEKS)), str(monday - timedelta(weeks=1)))


def _scope_clause(skill: dict | None, kpi_scope: str) -> str:
    """Which pending WPs belong to this profile. The pending table has no planning ID, so a WP is in scope when
    its process type or name matches a profile name / keyword, or when the profile's own scope (same filter as
    the KPIs) booked work on it in the last 8 weeks. Returns "" for the full table."""
    from analytics_agent import _sql_str
    if not skill or skill.get("scope_mode") == "all":
        return ""
    mode = skill.get("scope_mode", "defined")
    if mode.startswith("keyword:"):
        names = mode.split(":", 1)[1].split(",")
    else:
        names = list(skill.get("databricks_process_types") or []) + list(skill.get("databricks_planning_ids") or [])
        if not names and skill.get("databricks_feature"):
            names = [skill["databricks_feature"]]
    if isinstance(names, str):
        names = [names]
    parts = []
    for n in names:
        v = _sql_str(str(n).strip().lower())
        if v:
            parts += [f"LOWER(p.pt) LIKE '%{v}%'", f"LOWER(p.wp) LIKE '%{v}%'"]
    if kpi_scope:
        parts.append("LOWER(p.wp) IN (SELECT wpl FROM mine)")
    # why: a profile with neither names nor a KPI filter is the full table, like the KPI sections
    return ("AND (" + " OR ".join(parts) + ")") if parts else ""


def forecast_sql(table: str, skill: dict | None, kpi_scope: str, today: date) -> str:
    """The one read-only query: pending per WP in scope, with the WP's and its OM's 4-week pace."""
    w0, w3 = pace_weeks(today)
    w8 = str(date.fromisoformat(w3) - timedelta(weeks=7))
    om_p = _OM_FROM_NAME.format(c="work_package")
    return f"""
WITH pend AS (
  SELECT work_package AS wp, MAX(Data_Source) AS src, MAX(ProcessType) AS pt,
         MAX(COALESCE(DeliverableID, {om_p})) AS om, SUM(task_count) AS pending
  FROM {PENDING_TABLE}
  WHERE work_package IS NOT NULL AND NOT {_EXCLUDED_PT}
  GROUP BY work_package HAVING SUM(task_count) > 0),
wkr AS (
  SELECT LOWER(work_package) AS wpl, work_package AS wp, Production_Editor AS ed,
         COALESCE(Prod_Done_task_count, 0) AS t,
         COALESCE(Prod_Total_Time, 0) + COALESCE(qc_total_time, 0) AS h
  FROM {table}
  WHERE week_start BETWEEN '{w0}' AND '{w3}' AND work_package IS NOT NULL),
ommap AS (SELECT LOWER(wp) AS wpl, MAX(om) AS om FROM pend WHERE om IS NOT NULL GROUP BY LOWER(wp)),
wkr_om AS (SELECT wkr.*, COALESCE(m.om, {_OM_FROM_NAME.format(c="wkr.wp")}) AS om
           FROM wkr LEFT JOIN ommap m ON wkr.wpl = m.wpl),
wk AS (SELECT wpl, SUM(t) AS tasks, SUM(h) AS hrs, COUNT(DISTINCT ed) AS eds FROM wkr GROUP BY wpl),
om_pace AS (SELECT om, SUM(t) AS tasks, SUM(h) AS hrs, COUNT(DISTINCT ed) AS eds
            FROM wkr_om WHERE om IS NOT NULL GROUP BY om),
om_pend AS (SELECT om, SUM(pending) AS pending, COUNT(*) AS wps FROM pend WHERE om IS NOT NULL GROUP BY om),
mine AS (SELECT DISTINCT LOWER(work_package) AS wpl FROM {table}
         WHERE week_start BETWEEN '{w8}' AND '{w3}' AND work_package IS NOT NULL {kpi_scope})
SELECT p.wp, p.src, p.pt, p.om, p.pending,
       w.tasks, w.hrs, w.eds,
       o.tasks AS om_tasks, o.hrs AS om_hrs, o.eds AS om_eds, op.pending AS om_pending, op.wps AS om_wps
FROM pend p
LEFT JOIN wk w       ON LOWER(p.wp) = w.wpl
LEFT JOIN om_pace o  ON p.om = o.om
LEFT JOIN om_pend op ON p.om = op.om
WHERE 1 = 1 {_scope_clause(skill, kpi_scope)}
ORDER BY p.pending DESC
"""


def _num(v: Any) -> float:
    """Databricks returns numbers as strings (or None); 0.0 for missing."""
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def band_of(days: float) -> str:
    """Weather band for a forecast in work days."""
    return "sunny" if days <= SUNNY_DAYS else "cloudy" if days <= CLOUDY_DAYS else "rainy"


def days_text(days: float | None) -> str:
    """Work days as shown to a PM: a whole number, "> 1 year" past CAP_DAYS, "–" without a forecast."""
    if days is None:
        return "–"
    return "> 1 year" if days > CAP_DAYS else f"{days:,.0f}"


def basis_text(it: dict) -> str:
    """Where the row's pace comes from, with its real figures, so a PM can check the number."""
    if it["basis"] == "own":
        return f"own pace: {it['tasks_4w']:,} tasks in 4 wks"
    if it["basis"] == "om":
        return (f"no own work in 4 wks; done with {it['om']}: {it['om_tasks_4w']:,} tasks in 4 wks, "
                f"{it['om_pending']:,} pending in {it['om_wps']:,} WPs")
    return BANDS[it["band"]][1]


def classify(row: dict) -> dict:
    """One pending WP -> forecast item. Own pace first, then the OM's, else trickle / stalled without a number."""
    pending, tasks, hrs, eds = _num(row.get("pending")), _num(row.get("tasks")), _num(row.get("hrs")), _num(row.get("eds"))
    om_tasks, om_hrs, om_pending = _num(row.get("om_tasks")), _num(row.get("om_hrs")), _num(row.get("om_pending"))
    item = {"wp": row.get("wp") or "", "om": row.get("om") or "", "src": row.get("src") or "",
            "pt": row.get("pt") or "", "pending": int(pending), "tasks_4w": int(tasks),
            "editors": int(eds), "tph": round(tasks / hrs, 2) if hrs else None,
            "h_per_day": round(hrs / WORK_DAYS, 1), "days": None, "basis": "",
            "om_days": round(om_pending / (om_tasks / WORK_DAYS), 1) if om_tasks >= TRICKLE_TASKS and om_pending
                       else None, "om_worked": om_tasks > 0,
            "om_tasks_4w": int(om_tasks), "om_pending": int(om_pending), "om_wps": int(_num(row.get("om_wps")))}
    if tasks >= TRICKLE_TASKS:
        item.update(days=round(pending / (tasks / WORK_DAYS), 1), basis="own")
    elif om_tasks >= TRICKLE_TASKS and om_pending:
        # why: the WP itself has (almost) no history; the OM's team is the best real evidence of capacity, and
        # it works on all of the OM's WPs, so the WP is forecast to finish with its OM, not on its own.
        item.update(days=item["om_days"], basis="om",
                    editors=int(_num(row.get("om_eds"))),
                    tph=round(om_tasks / om_hrs, 2) if om_hrs else None,
                    h_per_day=round(om_hrs / WORK_DAYS, 1))
    item["band"] = band_of(item["days"]) if item["days"] is not None else (
        "trickle" if (tasks or om_tasks) else "stalled")
    return item


def om_rollup(items: list[dict]) -> list[dict]:
    """One row per OM ticket in scope: its pending in scope and the whole OM's forecast (all of its pending /
    its 4-week pace); trickle / stalled when the OM has no usable pace. Sorted by pending, largest first."""
    by: dict[str, dict] = {}
    for it in items:
        if not it["om"]:
            continue
        g = by.setdefault(it["om"], {"om": it["om"], "pending": 0, "wps": 0, "days": it["om_days"],
                                     "worked": False})
        g["pending"] += it["pending"]
        g["wps"] += 1
        g["worked"] = g["worked"] or it["om_worked"] or it["tasks_4w"] > 0
    for g in by.values():
        g["band"] = band_of(g["days"]) if g["days"] is not None else ("trickle" if g["worked"] else "stalled")
    return sorted(by.values(), key=lambda g: -g["pending"])


def summarise(rows: list[dict], weeks: tuple[str, str]) -> dict:
    """Forecast items, band totals and the OM roll-up from the query rows."""
    items = [classify(r) for r in rows]
    totals = {b: {"wps": 0, "pending": 0} for b in BANDS}
    for it in items:
        totals[it["band"]]["wps"] += 1
        totals[it["band"]]["pending"] += it["pending"]
    w_end = str(date.fromisoformat(weeks[1]) + timedelta(days=6))
    return {"items": items, "totals": totals, "oms": om_rollup(items), "pace_from": weeks[0], "pace_to": w_end,
            "pending_total": sum(it["pending"] for it in items),
            "excluded": "ADP, training and pilot process types"}


def run(skill: dict | None = None, today: date | None = None, client=None, table: str | None = None) -> dict:
    """Delivery forecast for one profile's scope. Never raises: {"error": ...} when Databricks fails, so the
    weekly report goes out without the section."""
    import os
    from analytics_agent import _build_client, _build_scope_filter
    if os.getenv("DELIVERY_FORECAST", "1").strip().lower() in ("0", "false", "off"):
        return {"off": True}
    if skill and skill.get("no_databricks_scope"):
        return {"error": "no scope in the profile"}
    today = today or date.today()
    try:
        if client is None:
            client, table = _build_client()
        kpi_scope = _build_scope_filter(skill)[0]
        rows = client.execute_sql(forecast_sql(table, skill, kpi_scope, today), 5000)["rows"]
    except Exception as exc:                   # why: a forecast problem must never stop the weekly report
        print(f"[forecast] failed: {exc}")
        return {"error": str(exc)[:200]}
    out = summarise(rows, pace_weeks(today))
    print(f"[forecast] {len(out['items'])} WPs, {out['pending_total']:,} pending, {len(out['oms'])} OMs")
    return out
