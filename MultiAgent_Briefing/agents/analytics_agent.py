"""
Analytics Agent — fetches live operational metrics from Databricks.

Metrics: FTA, Efficiency vs Baseline, CoQ, CopQ, process-type breakdown.
Scope filter priority (read from skill profile):
  1. processType  — if defined in skill, filter to exact process type(s)
  2. planningid   — fallback: LIKE '%<feature_name>%' (e.g. 'ADAS-RMLanes')
  3. No filter    — full table (only if neither is configured)

Pattern adapted from MultiTenantAgent_V3/app/status_report/data_layer.py.
Falls back to last known Confluence values if Databricks is unreachable.
"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # MultiAgent_Briefing/
sys.path.insert(0, str(Path(__file__).resolve().parent))           # MultiAgent_Briefing/agents/

from config import (
    FTA_TARGET, FTA_ALERT,
    COQ_HEALTHY, COQ_MONITOR, COQ_INVESTIGATE,
    YIELD_TARGET, YIELD_ALERT,
)

# ── Date helpers ───────────────────────────────────────────────────────────────

def _compute_target(report_type: str) -> tuple[str, str]:
    """
    Return (target_week_start, data_as_of_label) for the SQL queries.

    weekly → Monday of the current calendar week.
             Run on Friday = this week Mon→Fri.
    daily  → Monday of the week that contains the previous business day.
             Monday run  → yesterday=Sunday → back to Friday → last week's Monday.
             Tue-Fri run → yesterday=weekday → this week's Monday.
    alert  → Monday of the current week (UC4). The metrics query takes the latest week up to the
             target that has a QC sample in scope, so this is this week when it has data, else last week.
    """
    today = date.today()

    if report_type == "daily":
        prev = today - timedelta(days=1)
        while prev.weekday() >= 5:          # skip Saturday(5) / Sunday(6)
            prev -= timedelta(days=1)
        monday = prev - timedelta(days=prev.weekday())
        label  = f"as of {prev.strftime('%d %b %Y')} (yesterday)"
    elif report_type == "alert":
        monday = today - timedelta(days=today.weekday())
        label  = "this week, or last week while this week has no QC data"
    else:                                   # "weekly"
        monday = today - timedelta(days=today.weekday())
        label  = f"week of {monday.strftime('%d %b %Y')}"

    return monday.strftime("%Y-%m-%d"), label


# ── SQL templates ──────────────────────────────────────────────────────────────
# {scope_filter} is injected at runtime via _build_scope_filter().
# {week_filter}  is injected at runtime via _compute_target().
# week_start is a DATE column — ORDER BY natively, no TO_DATE() needed.

# Rows: QC-sampled production rows, plus the rows where IRIS books QC time on its own
# (QC editor, no task or QC counts) — without those, CoQ reads 0% for IRIS teams.
# The HAVING keeps only weeks / process types that had a QC sample (FTA defined).
_METRICS_SQL = """
SELECT
    week_start,
    ROUND(SUM(QC_Accept_Count) * 100.0 / NULLIF(SUM(total_qc_count), 0), 2)                  AS fta_pct,
    ROUND(SUM(Prod_Done_task_count) / NULLIF(COALESCE(SUM(Prod_Total_Time), 0) + COALESCE(SUM(qc_total_time), 0), 0), 4) AS efficiency,
    ROUND(COALESCE(SUM(qc_total_time), 0) * 100.0 / NULLIF(COALESCE(SUM(Prod_Total_Time), 0) + COALESCE(SUM(qc_total_time), 0), 0), 2) AS coq_pct,
    AVG(NULLIF(Baseline, 0))                                                                    AS baseline_avg,
    SUM(total_qc_count)        AS total_qc,
    SUM(QC_Accept_Count)       AS accepted,
    SUM(Prod_Done_task_count)  AS prod_tasks,
    ROUND(COALESCE(SUM(Prod_Total_Time), 0), 2) AS prod_hrs,
    ROUND(COALESCE(SUM(qc_total_time), 0), 2)   AS qc_hrs
FROM {table}
WHERE week_start IS NOT NULL
  AND week_start <= '{target_week}'
  AND (total_qc_count > 0 OR (COALESCE(Prod_Done_task_count, 0) = 0 AND qc_total_time > 0))
  {scope_filter}
GROUP BY week_start
HAVING COALESCE(SUM(total_qc_count), 0) > 0
ORDER BY week_start DESC
LIMIT 4
"""

_BREAKDOWN_SQL = """
SELECT
    processType AS process_type,
    ROUND(SUM(QC_Accept_Count) * 100.0 / NULLIF(SUM(total_qc_count), 0), 2)                  AS fta_pct,
    ROUND(SUM(Prod_Done_task_count) / NULLIF(COALESCE(SUM(Prod_Total_Time), 0) + COALESCE(SUM(qc_total_time), 0), 0), 4) AS efficiency,
    ROUND(COALESCE(SUM(qc_total_time), 0) * 100.0 / NULLIF(COALESCE(SUM(Prod_Total_Time), 0) + COALESCE(SUM(qc_total_time), 0), 0), 2) AS coq_pct,
    AVG(NULLIF(Baseline, 0))                                                                    AS baseline_avg,
    SUM(total_qc_count)        AS total_qc,
    SUM(QC_Accept_Count)       AS accepted,
    SUM(Prod_Done_task_count)  AS prod_tasks,
    ROUND(COALESCE(SUM(Prod_Total_Time), 0), 2) AS prod_hrs,
    ROUND(COALESCE(SUM(qc_total_time), 0), 2)   AS qc_hrs,
    ROUND(COALESCE(SUM(Prod_Total_Time), 0) + COALESCE(SUM(qc_total_time), 0), 1) AS total_hrs
FROM {table}
WHERE week_start = '{week}'
  AND (total_qc_count > 0 OR (COALESCE(Prod_Done_task_count, 0) = 0 AND qc_total_time > 0))
  AND processType IS NOT NULL
  {scope_filter}
GROUP BY processType
HAVING COALESCE(SUM(total_qc_count), 0) > 0
ORDER BY total_hrs DESC
LIMIT {limit}
"""


# Same rows as _BREAKDOWN_SQL, split by work unit. Feeds the work-unit rows under each process
# type and the work-unit summary; rows with no work unit are kept as '' ("Not assigned").
_BREAKDOWN_WU_SQL = """
SELECT
    LOWER(processType) AS pt,
    COALESCE(LOWER(TRIM(work_unit)), '') AS wu,
    COALESCE(SUM(QC_Accept_Count), 0)       AS accepted,
    COALESCE(SUM(total_qc_count), 0)        AS total_qc,
    COALESCE(SUM(Prod_Done_task_count), 0)  AS prod_tasks,
    COALESCE(SUM(Prod_Total_Time), 0)       AS prod_hrs,
    COALESCE(SUM(qc_total_time), 0)         AS qc_hrs,
    AVG(NULLIF(Baseline, 0))                AS baseline_avg
FROM {table}
WHERE week_start = '{week}'
  AND (total_qc_count > 0 OR (COALESCE(Prod_Done_task_count, 0) = 0 AND qc_total_time > 0))
  AND processType IS NOT NULL
  {scope_filter}
GROUP BY LOWER(processType), COALESCE(LOWER(TRIM(work_unit)), '')
HAVING COALESCE(SUM(total_qc_count), 0) > 0
"""

# Display names for the work_unit values (the KPI table is lowercase, the yield view mixed case).
_WU_NAMES = {
    "occ": "OCC", "dpu globallogic": "DPU GlobalLogic", "dpu noida": "DPU Noida",
    "dpu hyderabad": "DPU Hyderabad", "dpu rmsi": "DPU RMSI", "others": "Others",
    "partner-ceda": "Partner-CEDA", "": "Not assigned",
}


def wu_name(wu: str | None) -> str:
    """Display name for a work_unit value: case-insensitive lookup in _WU_NAMES, else title case."""
    key = (wu or "").strip().lower()
    return _WU_NAMES.get(key, key.title())


# Process types with production but no QC sample in the week. They are kept out of _BREAKDOWN_SQL
# (FTA would read as 0%) and listed separately instead.
_UNSAMPLED_SQL = """
SELECT
    processType AS process_type,
    SUM(Prod_Done_task_count) AS prod_tasks,
    ROUND(COALESCE(SUM(Prod_Total_Time), 0) + COALESCE(SUM(qc_total_time), 0), 1) AS total_hrs
FROM {table}
WHERE week_start = '{week}'
  AND processType IS NOT NULL
  {scope_filter}
GROUP BY processType
HAVING COALESCE(SUM(total_qc_count), 0) = 0 AND SUM(Prod_Done_task_count) > 0
ORDER BY prod_tasks DESC
LIMIT {limit}
"""


# Planning IDs listed in the profile, split by process type so each part is judged
# against its own process-type baseline (same baselines and row rules as the
# process-type breakdown). s_* columns use the QC-scope rows, a_* every row.
_PLANNING_SQL = """
SELECT
    planningid AS planning_id,
    LOWER(processType) AS pt,
    COALESCE(SUM(QC_Accept_Count), 0) AS accepted,
    COALESCE(SUM(total_qc_count), 0) AS total_qc,
    COALESCE(SUM(CASE WHEN {qc_rows} THEN Prod_Done_task_count END), 0) AS s_tasks,
    COALESCE(SUM(CASE WHEN {qc_rows} THEN COALESCE(Prod_Total_Time, 0) + COALESCE(qc_total_time, 0) END), 0) AS s_hrs,
    COALESCE(SUM(CASE WHEN {qc_rows} THEN COALESCE(qc_total_time, 0) END), 0) AS s_qc_hrs,
    AVG(NULLIF(Baseline, 0)) AS baseline_avg,
    COALESCE(SUM(Prod_Done_task_count), 0) AS a_tasks,
    COALESCE(SUM(COALESCE(Prod_Total_Time, 0) + COALESCE(qc_total_time, 0)), 0) AS a_hrs
FROM {table}
WHERE week_start = '{week}'
  AND LOWER(planningid) IN ({ids})
GROUP BY planningid, LOWER(processType)
"""


# ── Scope filter builder ───────────────────────────────────────────────────────

def _sql_str(value: str) -> str:
    """Escape a profile value for use inside a SQL string literal ('' doubles a quote).
    Process types and planning IDs come from user-edited profiles, so they are never trusted."""
    return str(value).replace("'", "''")


def _build_scope_filter(skill: dict | None) -> tuple[str, str, int]:
    """
    Build the SQL WHERE clause fragment and breakdown row limit for this skill's scope.

    Two strategies:
      1. Explicit names (defined mode): LIKE '%name%' on processType OR planningid
         — handles minor spelling differences; both columns searched.
      2. Keyword only (gen / lane / all): LIKE '%keyword%' across BOTH processType
         AND planningid with OR — catches all related work regardless of how it's tagged.

    Scope modes:
      keyword:gen,lane  → planningid OR processType LIKE '%gen%' / '%lane%', limit 12
      keyword:gen       → planningid OR processType LIKE '%gen%',            limit 10
      keyword:lane      → planningid OR processType LIKE '%lane%',           limit 10
      all               → no filter (full table by volume),                  limit 15
      defined           → LIKE on explicit processType/planningid values,    limit  8

    Returns (sql_fragment, human_label, breakdown_limit).
    """
    if skill is None:
        return "", "all process types (full table)", 15

    mode = skill.get("scope_mode", "defined")

    def _kw_clause(keywords: list[str]) -> str:
        parts = []
        for kw in keywords:
            parts.append(f"LOWER(planningid) LIKE '%{kw}%'")
            parts.append(f"LOWER(processType) LIKE '%{kw}%'")
        return "AND (" + " OR ".join(parts) + ")"

    if mode == "keyword:gen,lane":
        clause = _kw_clause(["gen", "lane"])
        return clause, "planningid/processType contains 'gen' OR 'lane'", 12

    if mode == "keyword:gen":
        clause = _kw_clause(["gen"])
        return clause, "planningid/processType contains 'gen'", 10

    if mode == "keyword:lane":
        clause = _kw_clause(["lane"])
        return clause, "planningid/processType contains 'lane'", 10

    if mode == "all":
        return "", "all process types (sorted by volume)", 15

    # mode == "defined" — explicit names listed; use LIKE on both columns
    process_types = skill.get("databricks_process_types") or []
    if isinstance(process_types, str):
        process_types = [process_types]

    planning_ids = skill.get("databricks_planning_ids") or []
    if not planning_ids:
        legacy = skill.get("databricks_feature") or ""
        if legacy:
            planning_ids = [legacy]

    explicit = list(process_types) + list(planning_ids)
    if explicit:
        parts = []
        for name in explicit:
            parts.append(f"LOWER(processType) LIKE '%{_sql_str(name.lower())}%'")
            parts.append(f"LOWER(planningid) LIKE '%{_sql_str(name.lower())}%'")
        clause = "AND (" + " OR ".join(parts) + ")"
        label  = f"LIKE any of {explicit[:3]}{'...' if len(explicit) > 3 else ''}"
        return clause, label, 8

    return "", "all process types (full table)", 15


# ── RAG helpers ────────────────────────────────────────────────────────────────

# Alerts use this week only once it is big enough to judge (decided 26 Oct): early in the week CoQ read 64%
# and efficiency 23–39% from a few hours of work. Otherwise they use last week, and the email says why.
ALERT_MIN_QC        = 50     # QC'd tasks in scope this week
ALERT_MIN_SHARE     = 0.20   # … and at least this share of last week's QC'd tasks


def alert_week_too_early(this_qc: float, last_qc: float) -> int | None:
    """QC'd tasks needed before alerts use this week, or None when this week already has enough."""
    import math
    need = max(ALERT_MIN_QC, math.ceil(ALERT_MIN_SHARE * (last_qc or 0)))
    return need if (this_qc or 0) < need else None


def alert_hours_too_early(this_hrs: float, last_hrs: float) -> int | None:
    """Production hours needed before alerts use this week, or None when it already has enough.

    CoQ and efficiency are hour-based, and production hours arrive later than QC counts: on 27 Oct a scope
    had more QC'd tasks than the whole week before but 14% of its production hours, so CoQ read 36% (27 Oct).
    """
    import math
    need = math.ceil(ALERT_MIN_SHARE * (last_hrs or 0))
    return need if need and (this_hrs or 0) < need else None


# A process type, work unit or planning ID with fewer QC'd tasks than this is shown but never flagged:
# one rejected task out of one reads as FTA 0% (seen 26 Oct: orbis-update-lanesleads, 1 QC'd, P1 "Lowest FTA").
MIN_QC_TO_FLAG = 10


def _mark_small_samples(rows: list[dict]) -> None:
    """Set fta_rag to "SMALL" on rows (and their work units) with too few QC'd tasks to judge."""
    for r in rows or []:
        if r.get("fta_rag") and (r.get("total_qc") or 0) < MIN_QC_TO_FLAG:
            r["fta_rag"] = "SMALL"
        _mark_small_samples(r.get("work_units") or [])


def _fta_rag(fta: float) -> str:
    if fta >= FTA_TARGET: return "GREEN"
    if fta >= FTA_ALERT:  return "AMBER"
    return "RED"

def _coq_rag(coq: float) -> str:
    if coq < COQ_HEALTHY:     return "GREEN"
    if coq < COQ_MONITOR:     return "AMBER_P3"
    if coq < COQ_INVESTIGATE: return "AMBER_P2"
    return "RED_P1"

def _eff_rag(eff_vs_bl: float) -> str:
    """eff_vs_bl is (actual / baseline) * 100 — 100 = exactly at baseline."""
    if eff_vs_bl >= 100: return "GREEN"
    if eff_vs_bl >= 90:  return "AMBER"
    return "RED"

def _yield_rag(y: float) -> str:
    if y >= YIELD_TARGET: return "GREEN"
    if y >= YIELD_ALERT:  return "AMBER"
    return "RED"

def _trend(values: list[float]) -> str:
    """Classify trend from most-recent-first list."""
    if len(values) < 2:
        return "stable"
    diff = values[0] - values[1]
    if diff > 0.5:  return "improving"
    if diff < -0.5: return "declining"
    return "stable"


# ── Post-query metric derivation (mirrors data_layer._ops_metrics) ─────────────

def _compute_metrics(row: dict) -> dict:
    """Derive CopQ, efficiency-vs-baseline, and sampling rate from a raw query result row."""
    total_qc   = float(row.get("total_qc")     or 0)
    accepted   = float(row.get("accepted")     or 0)
    prod_hrs   = float(row.get("prod_hrs")     or 0)
    qc_hrs     = float(row.get("qc_hrs")       or 0)
    baseline   = float(row.get("baseline_avg") or 0)
    efficiency = float(row.get("efficiency")   or 0)
    prod_tasks = float(row.get("prod_tasks")   or 0)

    rejected  = total_qc - accepted
    total_hrs = prod_hrs + qc_hrs

    # CopQ = fraction of QC time attributable to rejected tasks
    copq_hrs = round((rejected / total_qc) * qc_hrs, 2) if total_qc > 0 else 0.0
    copq_pct = round(copq_hrs / total_hrs * 100, 2)     if total_hrs > 0 else 0.0

    eff_vs_baseline = round(efficiency / baseline * 100, 1) if baseline > 0 else None

    # Sampling % = QC'd tasks / Production tasks — valuation of quality coverage
    sampling_pct = round(total_qc / prod_tasks * 100, 1) if prod_tasks > 0 else None

    return {
        "copq_hrs":        copq_hrs,
        "copq_pct":        copq_pct,
        "eff_vs_baseline": eff_vs_baseline,
        "efficiency_raw":  efficiency,
        "total_hrs":       round(total_hrs, 2),
        "prod_hrs":        prod_hrs,
        "qc_hrs":          qc_hrs,
        "total_qc":        int(total_qc),
        "prod_tasks":      int(prod_tasks),
        "sampling_pct":    sampling_pct,
    }


# ── Operator breakdown SQL ────────────────────────────────────────────────────
_OPERATOR_SQL = """
SELECT
    processType AS process_type,
    Production_Editor AS operator,
    ROUND(SUM(QC_Accept_Count) * 100.0 / NULLIF(SUM(total_qc_count), 0), 2)                   AS fta_pct,
    ROUND(SUM(Prod_Done_task_count) / NULLIF(COALESCE(SUM(Prod_Total_Time), 0) + COALESCE(SUM(qc_total_time), 0), 0), 4) AS efficiency,
    ROUND(COALESCE(SUM(qc_total_time), 0) * 100.0 / NULLIF(COALESCE(SUM(Prod_Total_Time), 0) + COALESCE(SUM(qc_total_time), 0), 0), 2) AS coq_pct,
    AVG(NULLIF(Baseline, 0))                                                                    AS baseline_avg,
    SUM(Prod_Done_task_count) AS prod_tasks,
    SUM(total_qc_count)       AS total_qc,
    SUM(QC_Accept_Count)      AS accepted,
    COALESCE(SUM(Prod_Total_Time), 0) + COALESCE(SUM(qc_total_time), 0) AS total_hrs
FROM {table}
WHERE week_start = '{week}'
  AND total_qc_count > 0
  AND Production_Editor IS NOT NULL
  AND Production_Editor != ''
  {scope_filter}
GROUP BY processType, Production_Editor
QUALIFY ROW_NUMBER() OVER (PARTITION BY processType ORDER BY prod_tasks DESC) <= {per_pt_limit}
ORDER BY processType, prod_tasks DESC
LIMIT {limit}
"""


def _load_operator_breakdown(
    client, combined_table: str, week_label: str,
    scope_filter: str, baselines: dict[str, float],
    limit: int = 1000,
    per_pt_limit: int = 100,
) -> list[dict]:
    """Query per-operator metrics for the current week. Returns list of operator dicts.
    Caps rows per process type so one large PT cannot crowd out the others."""
    try:
        sql = _OPERATOR_SQL.format(
            table=combined_table, week=week_label,
            scope_filter=scope_filter, limit=limit, per_pt_limit=per_pt_limit,
        )
        result = client.execute_sql(sql, max_rows=limit)
        rows = result.get("rows", [])
    except Exception as exc:
        print(f"[analytics] Operator breakdown query failed: {exc}")
        return []

    operators = []
    for r in rows:
        pt        = (r.get("process_type") or "").lower()
        operator  = r.get("operator") or ""
        fta       = float(r.get("fta_pct")    or 0)
        eff_raw   = float(r.get("efficiency") or 0)
        coq       = float(r.get("coq_pct")    or 0)
        bl_avg    = float(r.get("baseline_avg") or 0)
        prod      = int(r.get("prod_tasks")   or 0)
        qc        = int(r.get("total_qc")     or 0)
        accepted  = int(r.get("accepted")     or 0)

        # eff vs baseline: use per-PT baseline first, then row's baseline_avg
        pt_bl = baselines.get(pt)
        if pt_bl and eff_raw > 0:
            eff_vs_bl = round(eff_raw / pt_bl * 100, 1)
        elif bl_avg > 0 and eff_raw > 0:
            eff_vs_bl = round(eff_raw / bl_avg * 100, 1)
        else:
            eff_vs_bl = None

        sampling = round(qc / prod * 100, 1) if prod > 0 else None
        operators.append({
            "process_type": r.get("process_type", ""),
            "operator":     operator,
            "fta_pct":      fta,
            "fta_rag":      _fta_rag(fta) if qc > 0 else "GREEN",
            "efficiency":   eff_raw,
            "eff_vs_bl":    eff_vs_bl,
            "has_prod":     prod > 0,
            "coq_pct":      coq,
            "prod_tasks":   prod,
            "total_qc":     qc,
            "accepted":     accepted,
            "sampling_pct": sampling,
            "total_hrs":    round(float(r.get("total_hrs") or 0), 1),
            "yield_pct":    None,
        })
    print(f"[analytics] Operator breakdown: {len(operators)} rows across {len({o['process_type'] for o in operators})} PTs")
    return operators


# ── Yield view (orbit_sd task-level data) ─────────────────────────────────────
_YIELD_VIEW = "maps_operations_dev_catalog.orbit_sd_reporting_views.orbit_sd_maps_timespent_agg_vw"

_YIELD_SQL = """
SELECT
    DATE_TRUNC('week', CAST(updated_at AS DATE)) AS week_mon,
    SUM(CASE WHEN to_status IN ('Resolved', 'DB alternatively updated')
             AND to_stage IN ('Resolution', 'Expert', 'Source Expert', 'OSM')
             THEN prod_count ELSE 0 END) AS yield_num,
    SUM(CASE WHEN COALESCE(n_rework_flag, 0) != 1
             AND to_stage IN ('Resolution', 'Expert', 'Source Expert', 'OSM')
             THEN prod_count ELSE 0 END) AS yield_den
FROM {view}
WHERE CAST(updated_at AS DATE) >= DATE_ADD(TO_DATE('{target_week}'), -21)
  AND CAST(updated_at AS DATE) <= DATE_ADD(TO_DATE('{target_week}'), 6)
  {scope_filter}
GROUP BY DATE_TRUNC('week', CAST(updated_at AS DATE))
ORDER BY week_mon DESC
LIMIT 4
"""

# Yield follows the same rules as FTA, Eff vs BL and CoQ: every work unit, no work-unit list (decided 26 Oct,
# OSI-004). The one difference is the source: today only the Orbit SD view has Yield, so other work (e.g.
# TTI / TMC) has none until Yield exists for every workflow (OSI-041).
YIELD_SD_ONLY_NOTE = ("Yield is currently available for Orbit SD work only; the process types in your scope have "
                      "no Yield data yet, so no Yield is shown or alerted.")

_YIELD_BY_PID_SQL = """
SELECT
    LOWER(planning_id) AS pid,
    SUM(CASE WHEN to_status IN ('Resolved', 'DB alternatively updated')
             AND to_stage IN ('Resolution', 'Expert', 'Source Expert', 'OSM')
             THEN prod_count ELSE 0 END) AS yield_num,
    SUM(CASE WHEN COALESCE(n_rework_flag, 0) != 1
             AND to_stage IN ('Resolution', 'Expert', 'Source Expert', 'OSM')
             THEN prod_count ELSE 0 END) AS yield_den
FROM {view}
WHERE CAST(updated_at AS DATE) >= TO_DATE('{target_week}')
  AND CAST(updated_at AS DATE) <= DATE_ADD(TO_DATE('{target_week}'), 6)
  AND planning_id IS NOT NULL
  {scope_filter}
GROUP BY LOWER(planning_id)
"""

_YIELD_BY_OPERATOR_SQL = """
SELECT
    LOWER(process_type) AS pt,
    LOWER(TRIM(editor)) AS op,
    SUM(CASE WHEN to_status IN ('Resolved', 'DB alternatively updated')
             AND to_stage IN ('Resolution', 'Expert', 'Source Expert', 'OSM')
             THEN prod_count ELSE 0 END) AS yield_num,
    SUM(CASE WHEN COALESCE(n_rework_flag, 0) != 1
             AND to_stage IN ('Resolution', 'Expert', 'Source Expert', 'OSM')
             THEN prod_count ELSE 0 END) AS yield_den
FROM {view}
WHERE CAST(updated_at AS DATE) >= TO_DATE('{target_week}')
  AND CAST(updated_at AS DATE) <= DATE_ADD(TO_DATE('{target_week}'), 6)
  AND editor IS NOT NULL
  {scope_filter}
GROUP BY LOWER(process_type), LOWER(TRIM(editor))
"""

# Operators with fewer production tasks / QC'd tasks than this are listed but not judged: one task swings
# FTA, CoQ or efficiency to an extreme.
OP_MIN_TASKS = 10


def mark_operator_breaches(operators: list[dict], levels: dict[str, dict]) -> None:
    """Add "breaches" (metric keys past the profile's alert level) to each operator row (OSI-009)."""
    field = {"fta": "fta_pct", "efficiency": "eff_vs_bl", "coq": "coq_pct", "yield": "yield_pct"}
    for o in operators:
        out = []
        for m, lv in levels.items():
            v = o.get(field[m])
            judged = (o.get("total_qc") or 0) >= OP_MIN_TASKS if m == "fta" else (o.get("prod_tasks") or 0) >= OP_MIN_TASKS
            if v is None or not judged:
                continue
            if (v > lv["alert"]) if lv["direction"] == "rise" else (v < lv["alert"]):
                out.append(m)
        o["breaches"] = out


_YIELD_BY_PT_WU_SQL = """
SELECT
    LOWER(process_type) AS pt,
    COALESCE(LOWER(TRIM(work_unit)), '') AS wu,
    SUM(CASE WHEN to_status IN ('Resolved', 'DB alternatively updated')
             AND to_stage IN ('Resolution', 'Expert', 'Source Expert', 'OSM')
             THEN prod_count ELSE 0 END) AS yield_num,
    SUM(CASE WHEN COALESCE(n_rework_flag, 0) != 1
             AND to_stage IN ('Resolution', 'Expert', 'Source Expert', 'OSM')
             THEN prod_count ELSE 0 END) AS yield_den
FROM {view}
WHERE CAST(updated_at AS DATE) >= TO_DATE('{target_week}')
  AND CAST(updated_at AS DATE) <= DATE_ADD(TO_DATE('{target_week}'), 6)
  {scope_filter}
GROUP BY LOWER(process_type), COALESCE(LOWER(TRIM(work_unit)), '')
"""


# ── Baseline view (same source as ConfluenceAutoUpdate) ───────────────────────
_BASELINE_VIEW = "mo_occ_reporting.manual_efficiency.manual_efficiency_orbit_sd_daily_vw"

_BASELINES_SQL = f"""
SELECT LOWER(processType) AS pt,
       SUM(Prod_Done_task_count) / NULLIF(COALESCE(SUM(Prod_Total_Time), 0) + COALESCE(SUM(qc_total_time), 0), 0) AS hist_eff
FROM {_BASELINE_VIEW}
WHERE Prod_Done_task_count > 0
  AND processType IS NOT NULL
GROUP BY LOWER(processType)
"""


def _load_baselines(client, fallback_table: str = "") -> dict[str, float]:
    """Load per-process-type efficiency baselines.
    Queries VIEW_A AND the combined table Baseline column, merging both.
    VIEW_A values take priority; combined table fills gaps for process types
    VIEW_A doesn't cover (VIEW_A has 51 types, combined table has 107+)."""
    baselines: dict[str, float] = {}

    # Step 1: load from combined table first (broader coverage — 107+ types)
    if fallback_table:
        try:
            fallback_sql = f"""
SELECT LOWER(processType) AS pt,
       AVG(NULLIF(Baseline, 0)) AS hist_eff
FROM {fallback_table}
WHERE Prod_Done_task_count > 0
  AND processType IS NOT NULL
  AND Baseline IS NOT NULL AND Baseline > 0
GROUP BY LOWER(processType)
"""
            result = client.execute_sql(fallback_sql, max_rows=500)
            for r in result.get("rows", []):
                pt  = r.get("pt")
                eff = r.get("hist_eff")
                if pt and eff is not None:
                    baselines[pt] = round(float(eff), 6)
            print(f"[analytics] Loaded {len(baselines)} baselines from combined table (Baseline col)")
        except Exception as exc:
            print(f"[analytics] Could not load combined table baselines: {exc}")

    # Step 2: overlay VIEW_A values (more precise historical calc) where available
    try:
        result = client.execute_sql(_BASELINES_SQL, max_rows=500)
        view_a: dict[str, float] = {}
        for r in result.get("rows", []):
            pt  = r.get("pt")
            eff = r.get("hist_eff")
            if pt and eff is not None:
                view_a[pt] = round(float(eff), 6)
        if view_a:
            baselines.update(view_a)  # VIEW_A overwrites combined table for same keys
            print(f"[analytics] Merged {len(view_a)} VIEW_A baselines (total: {len(baselines)})")
    except Exception:
        pass  # VIEW_A unavailable — combined table baselines already loaded

    return baselines


def _eff_vs_bl_from_baselines(efficiency_raw: float, process_types: list[str], baselines: dict[str, float]) -> float | None:
    """
    Compute efficiency vs baseline % using per-process-type historical baselines.
    Averages the baseline across all in-scope process types, then returns (actual/avg_bl)*100.
    Falls back to None if no matching baselines found.
    """
    if not baselines or efficiency_raw == 0:
        return None
    if process_types:
        matched = [baselines[pt.lower()] for pt in process_types if pt.lower() in baselines]
    else:
        matched = list(baselines.values())
    if not matched:
        return None
    avg_bl = sum(matched) / len(matched)
    return round(efficiency_raw / avg_bl * 100, 1) if avg_bl > 0 else None


# ── Yield helpers ─────────────────────────────────────────────────────────────

def _build_yield_scope_filter(skill: dict | None, actual_pts: list[str]) -> str:
    """Build scope filter for orbit_sd yield view (uses process_type, not processType)."""
    if skill is None:
        return ""
    mode = skill.get("scope_mode", "defined")
    if mode == "keyword:gen,lane":
        return "AND (LOWER(process_type) LIKE '%gen%' OR LOWER(process_type) LIKE '%lane%')"
    if mode == "keyword:gen":
        return "AND LOWER(process_type) LIKE '%gen%'"
    if mode == "keyword:lane":
        return "AND LOWER(process_type) LIKE '%lane%'"
    if mode == "all":
        return ""
    # defined mode — use actual_pts derived from breakdown (or explicit config)
    pts = actual_pts or skill.get("databricks_process_types") or []
    if pts:
        quoted = ", ".join(f"'{_sql_str(p.lower())}'" for p in pts)
        return f"AND LOWER(process_type) IN ({quoted})"
    return ""


def _load_yield(client, skill: dict | None, actual_pts: list[str], target_week: str) -> dict:
    """Query 4-week aggregate + per-process-type yield from orbit_sd_maps_timespent_agg_vw."""
    scope_filter = _build_yield_scope_filter(skill, actual_pts)

    # ── 4-week weekly aggregate ────────────────────────────────────────────────
    weekly: list[dict] = []
    try:
        sql = _YIELD_SQL.format(view=_YIELD_VIEW, target_week=target_week, scope_filter=scope_filter)
        result = client.execute_sql(sql, max_rows=4)
        for r in result.get("rows", []):
            num = float(r.get("yield_num") or 0)
            den = float(r.get("yield_den") or 0)
            yld = round(num / den * 100, 2) if den > 0 else None
            weekly.append({"week": str(r.get("week_mon", ""))[:10], "yield": yld})
    except Exception as exc:
        print(f"[analytics] Yield (4-week) query failed: {exc}")

    # ── Current week by process type × work unit, rolled up to each level ─────
    pct = lambda n, d: round(n / d * 100, 2) if d > 0 else None
    yield_by_pt: dict[str, float | None] = {}
    yield_by_wu: dict[str, float | None] = {}
    yield_by_pt_wu: dict[tuple[str, str], float | None] = {}
    try:
        pt_sql = _YIELD_BY_PT_WU_SQL.format(view=_YIELD_VIEW, target_week=target_week, scope_filter=scope_filter)
        pt_result = client.execute_sql(pt_sql, max_rows=1000)
        pt_tot: dict[str, list[float]] = {}
        wu_tot: dict[str, list[float]] = {}
        for r in pt_result.get("rows", []):
            pt  = (r.get("pt") or "").lower()
            wu  = (r.get("wu") or "").lower()
            num = float(r.get("yield_num") or 0)
            den = float(r.get("yield_den") or 0)
            if not pt:
                continue
            yield_by_pt_wu[(pt, wu)] = pct(num, den)
            for tot, key in ((pt_tot, pt), (wu_tot, wu)):
                t = tot.setdefault(key, [0.0, 0.0])
                t[0] += num
                t[1] += den
        yield_by_pt = {k: pct(n, d) for k, (n, d) in pt_tot.items()}
        yield_by_wu = {k: pct(n, d) for k, (n, d) in wu_tot.items()}
        print(f"[analytics] Yield by PT: {len(yield_by_pt)} process types, {len(yield_by_wu)} work units")
    except Exception as exc:
        print(f"[analytics] Yield (by PT / work unit) query failed: {exc}")

    # ── Current week by planning ID (OSI-030 rows at Planning ID level) ───────
    yield_by_pid: dict[str, float | None] = {}
    try:
        pid_sql = _YIELD_BY_PID_SQL.format(view=_YIELD_VIEW, target_week=target_week, scope_filter=scope_filter)
        for r in client.execute_sql(pid_sql, max_rows=1000).get("rows", []):
            yield_by_pid[(r.get("pid") or "").lower()] = pct(float(r.get("yield_num") or 0), float(r.get("yield_den") or 0))
    except Exception as exc:
        print(f"[analytics] Yield (by planning ID) query failed: {exc}")

    current = weekly[0]["yield"] if weekly else None
    print(f"[analytics] Yield loaded: current={current}  weeks={len(weekly)}")
    return {"yield_current": current, "yield_4w": weekly, "yield_by_pt": yield_by_pt,
            "yield_by_wu": yield_by_wu, "yield_by_pt_wu": yield_by_pt_wu, "yield_by_pid": yield_by_pid}


# ── Databricks client factory ──────────────────────────────────────────────────

def _load_workunit_breakdown(client, table: str, week: str, scope_filter: str,
                             baselines: dict[str, float], process_breakdown: list[dict]) -> list[dict]:
    """
    Split the week's in-scope rows by work unit. Adds a "work_units" list to each
    process_breakdown entry and returns the overall per-work-unit summary (all
    in-scope process types). Eff vs BL is expected hours (tasks / process-type
    baseline) over actual hours, so mixed process types are each judged against
    their own baseline.
    """
    try:
        result = client.execute_sql(_BREAKDOWN_WU_SQL.format(
            table=table, week=week, scope_filter=scope_filter), max_rows=2000)
    except Exception as exc:
        print(f"[analytics] Work-unit breakdown failed: {exc}")
        return []

    def _new():
        return dict(acc=0.0, qc=0.0, tasks=0.0, prod_hrs=0.0, qc_hrs=0.0, exp_hrs=0.0, bl_hrs=0.0)

    def _add(g, r, pt):
        f = lambda k: float(r.get(k) or 0)
        g["acc"] += f("accepted"); g["qc"] += f("total_qc"); g["tasks"] += f("prod_tasks")
        g["prod_hrs"] += f("prod_hrs"); g["qc_hrs"] += f("qc_hrs")
        bl = baselines.get(pt) or f("baseline_avg")
        hrs = f("prod_hrs") + f("qc_hrs")
        if bl > 0 and f("prod_tasks") > 0 and hrs > 0:
            g["exp_hrs"] += f("prod_tasks") / bl
            g["bl_hrs"] += hrs

    def _row(wu, g):
        hrs = g["prod_hrs"] + g["qc_hrs"]
        fta = round(g["acc"] * 100 / g["qc"], 2) if g["qc"] > 0 else 0.0
        return {
            "work_unit":    wu,
            "name":         wu_name(wu),
            "fta_pct":      fta,
            "fta_rag":      _fta_rag(fta),
            "eff_vs_bl":    round(g["exp_hrs"] * 100 / g["bl_hrs"], 1) if g["bl_hrs"] > 0 else None,
            "has_prod":     g["tasks"] > 0,
            "coq_pct":      round(g["qc_hrs"] * 100 / hrs, 2) if hrs > 0 else 0.0,
            "prod_tasks":   int(g["tasks"]),
            "total_qc":     int(g["qc"]),
            "sampling_pct": round(g["qc"] / g["tasks"] * 100, 1) if g["tasks"] > 0 else None,
            "total_hrs":    round(hrs, 1),
            "yield_pct":    None,
        }

    by_pt: dict[str, dict[str, dict]] = {}
    overall: dict[str, dict] = {}
    for r in result.get("rows", []):
        pt = (r.get("pt") or "").lower()
        wu = (r.get("wu") or "").lower()
        _add(by_pt.setdefault(pt, {}).setdefault(wu, _new()), r, pt)
        _add(overall.setdefault(wu, _new()), r, pt)

    for entry in process_breakdown:
        groups = by_pt.get(entry["process_type"].lower(), {})
        entry["work_units"] = sorted((_row(wu, g) for wu, g in groups.items()),
                                     key=lambda w: -w["total_hrs"])
    summary = sorted((_row(wu, g) for wu, g in overall.items()), key=lambda w: -w["total_hrs"])
    print(f"[analytics] Work-unit breakdown: {len(summary)} work units")
    return summary


def _build_client():
    import os
    from db_client import DatabricksSQLClient

    host         = os.getenv("DATABRICKS_HOST", "").rstrip("/")
    warehouse_id = os.getenv("DATABRICKS_SQL_WAREHOUSE_ID", "")
    pat_token    = os.getenv("DATABRICKS_PAT_TOKEN", "")

    if not host or not warehouse_id:
        raise ValueError("DATABRICKS_HOST and DATABRICKS_SQL_WAREHOUSE_ID must be set in OPS_Native_AI/.env")

    credential = None
    if not pat_token:
        try:
            from azure.identity import DefaultAzureCredential
            credential = DefaultAzureCredential()
        except ImportError:
            raise ValueError("DATABRICKS_PAT_TOKEN not set and azure-identity not installed.")

    combined_table = os.getenv(
        "COMBINED_TABLE",
        "mo_occ_reporting.manual_efficiency.manual_efficiency_quality_all_weekly_tbl",
    )
    return DatabricksSQLClient(
        host=host, warehouse_id=warehouse_id,
        credential=credential, pat_token=pat_token,
        registered_tables=[combined_table],
    ), combined_table


# ── Fallback ───────────────────────────────────────────────────────────────────

def _fallback(error: str) -> dict[str, Any]:
    """Placeholder metrics when Databricks has no data or is unreachable, marked live=False.
    The numbers are NOT current data: UC4 never raises an alert on them (trigger_engine._run_uc4)."""
    return {
        "fta_current":       96.68,
        "fta_prev_week":     96.27,
        "fta_trend":         "stable",
        "fta_rag":           "GREEN",
        "fta_4w":            [],
        "efficiency_raw":    None,
        "efficiency_vs_bl":  None,
        "efficiency_rag":    "GREEN",
        "coq_current":       6.44,
        "coq_rag":           "AMBER_P3",
        "copq_hrs":          None,
        "copq_pct":          None,
        "prod_hrs":          None,
        "qc_hrs":            None,
        "process_breakdown":  [],
        "workunit_breakdown": [],
        "operator_breakdown": [],
        "scope_label":        "cached",
        "week_label":        "2026-08-23",
        "source":            "Confluence Progress Page (cached — Databricks offline)",
        "as_of":             datetime.now(timezone.utc).isoformat(),
        "live":              False,
        "error":             error,
    }


# ── Public entry point ─────────────────────────────────────────────────────────

def run(skill: dict | None = None, report_type: str = "weekly") -> dict[str, Any]:
    """
    Fetch FTA, Efficiency, CoQ, CopQ and process-type breakdown from Databricks.

    Args:
        skill:       parsed skill profile dict from skill_registry.load_skill().
        report_type: "weekly" → current week's Monday; "daily" → Monday of the
                     week containing the previous business day; "alert" → current week,
                     falling back to last week when this week has no QC data.
    """
    as_of = datetime.now(timezone.utc).isoformat()

    if skill and skill.get("no_databricks_scope"):
        # Nothing to scope the numbers to: no Databricks query, and nothing that could be shown as data.
        r = _fallback("no process types or planning IDs in the profile")
        r.update(no_scope=True, live=False, week_label="", data_label="",
                 fta_rag="GREEN", efficiency_rag="GREEN", coq_rag="GREEN", yield_rag="GREEN",
                 process_breakdown=[], workunit_breakdown=[], operator_breakdown=[], planning_breakdown=[],
                 metrics_4w=[], fta_4w=[], scope_label="no scope in the profile")
        return r

    target_week, data_label = _compute_target(report_type)
    print(f"[analytics] report_type={report_type}  target_week={target_week}  ({data_label})")

    scope_filter, scope_label, bd_limit = _build_scope_filter(skill)
    process_types = (skill.get("databricks_process_types") or []) if skill else []

    try:
        client, combined_table = _build_client()
    except ValueError as exc:
        return _fallback(str(exc))

    # Load per-process-type efficiency baselines: VIEW_A first, combined table as fallback
    baselines = _load_baselines(client, combined_table)

    # ── Main metrics: last 4 weeks up to target_week ───────────────────────────
    try:
        sql = _METRICS_SQL.format(
            table=combined_table,
            target_week=target_week,
            scope_filter=scope_filter,
        )
        result = client.execute_sql(sql, max_rows=4)
        rows = result.get("rows", [])
        if not rows:
            return _fallback(f"Metrics query returned no rows (scope: {scope_label})")

        early_week = None
        if report_type == "alert" and len(rows) > 1 and str(rows[0].get("week_start"))[:10] == target_week:
            this_qc, last_qc = float(rows[0].get("total_qc") or 0), float(rows[1].get("total_qc") or 0)
            this_h, last_h = float(rows[0].get("prod_hrs") or 0), float(rows[1].get("prod_hrs") or 0)
            need = alert_week_too_early(this_qc, last_qc)
            need_h = alert_hours_too_early(this_h, last_h)
            if need is not None or need_h is not None:
                early_week = {"week": target_week, "qc": int(this_qc), "needed": need,
                              "hrs": round(this_h), "needed_hrs": need_h}
                rows = rows[1:]
                target_week = str(rows[0].get("week_start"))[:10]
                print(f"[analytics] this week too early for alerts ({int(this_qc)} QC'd / {this_h:.0f} production h; "
                      f"needs {need or '-'} QC'd / {need_h or '-'} h) — using {target_week}")

        current  = rows[0]
        previous = rows[1] if len(rows) > 1 else rows[0]

        fta_current = float(current.get("fta_pct")  or 0)
        fta_prev    = float(previous.get("fta_pct") or fta_current)
        coq_current = float(current.get("coq_pct")  or 0)
        week_label  = str(current.get("week_start", "latest"))

        fta_4w = [
            {"week": str(r.get("week_start")), "fta": float(r.get("fta_pct") or 0)}
            for r in rows
        ]
        # Store raw efficiency per week; eff_vs_bl filled after breakdown (need actual_pts)
        _raw_eff_by_week = [float(r.get("efficiency") or 0) for r in rows]
        metrics_4w = [
            {
                "week":             str(r.get("week_start")),
                "fta":              float(r.get("fta_pct") or 0),
                "coq":              float(r.get("coq_pct") or 0),
                "efficiency_vs_bl": None,  # filled below after breakdown
                "sampling_pct":     round(float(r.get("total_qc") or 0) / float(r.get("prod_tasks") or 1) * 100, 1)
                                    if float(r.get("prod_tasks") or 0) > 0 else None,
                "qc_tasks":         int(float(r.get("total_qc") or 0)),   # sample size, shown with the reference week
            }
            for r in rows
        ]
        computed = _compute_metrics(current)

    except Exception as exc:
        return _fallback(f"Metrics query failed: {exc}")

    # ── Process-type breakdown for the latest week ─────────────────────────────
    process_breakdown: list[dict] = []
    try:
        bd_sql = _BREAKDOWN_SQL.format(
            table=combined_table,
            week=week_label,
            scope_filter=scope_filter,
            limit=bd_limit,
        )
        bd_result = client.execute_sql(bd_sql, max_rows=bd_limit)
        for r in bd_result.get("rows", []):
            bd  = _compute_metrics(r)
            pt  = (r.get("process_type") or "").lower()
            pt_bl = baselines.get(pt)
            pt_eff_raw = float(r.get("efficiency") or 0)
            has_prod = bd["prod_tasks"] > 0
            # Use explicit > 0 check — efficiency=0.0 is falsy in Python but means "no prod work"
            if pt_bl and pt_eff_raw > 0:
                pt_eff_vs_bl = round(pt_eff_raw / pt_bl * 100, 1)
            elif pt_eff_raw > 0:
                # efficiency > 0 but no specific baseline — use the baseline_avg col from the row
                pt_eff_vs_bl = bd["eff_vs_baseline"]
            else:
                pt_eff_vs_bl = None  # no production work this week
            process_breakdown.append({
                "process_type": r.get("process_type", ""),
                "fta_pct":     float(r.get("fta_pct")    or 0),
                "fta_rag":     _fta_rag(float(r.get("fta_pct") or 0)),
                "efficiency":  pt_eff_raw,
                "eff_vs_bl":   pt_eff_vs_bl,
                "has_prod":    has_prod,
                "coq_pct":     float(r.get("coq_pct")    or 0),
                "copq_hrs":    bd["copq_hrs"],
                "prod_tasks":  bd["prod_tasks"],
                "total_qc":    bd["total_qc"],
                "sampling_pct": bd["sampling_pct"],
                "total_hrs":   float(r.get("total_hrs")  or 0),
            })
    except Exception:
        pass  # breakdown is supplementary — don't fail the whole run

    unsampled_breakdown: list[dict] = []
    try:
        un_result = client.execute_sql(_UNSAMPLED_SQL.format(
            table=combined_table, week=week_label, scope_filter=scope_filter, limit=bd_limit,
        ), max_rows=bd_limit)
        unsampled_breakdown = [
            {"process_type": r.get("process_type", ""),
             "prod_tasks": int(float(r.get("prod_tasks") or 0)),
             "total_hrs": float(r.get("total_hrs") or 0)}
            for r in un_result.get("rows", [])
        ]
    except Exception:
        pass  # supplementary, like the breakdown

    workunit_breakdown = _load_workunit_breakdown(
        client, combined_table, week_label, scope_filter, baselines, process_breakdown)

    planning_breakdown: list[dict] = []
    planning_missing: list[str] = []
    listed_ids = list(dict.fromkeys(p.strip().lower() for p in (skill.get("databricks_planning_ids") or []) if p.strip())) if skill else []
    if listed_ids:
        try:
            ids_sql = ", ".join("'" + p.replace("'", "''") + "'" for p in listed_ids)
            qc_rows = "(total_qc_count > 0 OR (COALESCE(Prod_Done_task_count, 0) = 0 AND qc_total_time > 0))"
            pl_result = client.execute_sql(_PLANNING_SQL.format(
                table=combined_table, week=week_label, ids=ids_sql, qc_rows=qc_rows), max_rows=500)
            agg: dict[str, dict] = {}
            for r in pl_result.get("rows", []):
                pid = r.get("planning_id") or ""
                g = agg.setdefault(pid, dict(acc=0.0, qc=0.0, s_tasks=0.0, s_hrs=0.0, s_qc_hrs=0.0,
                                             exp_hrs=0.0, bl_hrs=0.0, a_tasks=0.0, a_hrs=0.0))
                f = lambda k: float(r.get(k) or 0)
                for k_out, k_in in (("acc", "accepted"), ("qc", "total_qc"), ("s_tasks", "s_tasks"), ("s_hrs", "s_hrs"),
                                    ("s_qc_hrs", "s_qc_hrs"), ("a_tasks", "a_tasks"), ("a_hrs", "a_hrs")):
                    g[k_out] += f(k_in)
                bl = baselines.get(r.get("pt") or "") or f("baseline_avg")
                if bl > 0 and f("s_hrs") > 0:
                    g["exp_hrs"] += f("s_tasks") / bl
                    g["bl_hrs"] += f("s_hrs")
            for pid, g in sorted(agg.items(), key=lambda kv: -kv[1]["a_tasks"]):
                sampled = g["qc"] > 0
                fta = round(g["acc"] * 100 / g["qc"], 2) if sampled else None
                hrs = g["s_hrs"] if sampled else g["a_hrs"]
                planning_breakdown.append({
                    "planning_id": pid,
                    "fta_pct": fta,
                    "fta_rag": _fta_rag(fta) if fta is not None else None,
                    "eff_vs_bl": round(g["exp_hrs"] * 100 / g["bl_hrs"], 1) if sampled and g["bl_hrs"] > 0 else None,
                    "coq_pct": round(g["s_qc_hrs"] * 100 / g["s_hrs"], 2) if sampled and g["s_hrs"] > 0 else 0.0,
                    "total_qc": int(g["qc"]),
                    "prod_tasks": int(g["s_tasks"] if sampled else g["a_tasks"]),
                    "total_hrs": round(hrs, 1),
                })
            seen = {b["planning_id"].lower() for b in planning_breakdown}
            planning_missing = [p for p in listed_ids if p not in seen]
        except Exception as exc:
            print(f"[analytics] Planning ID breakdown failed: {exc}")

    # ── Efficiency vs baseline — use actual in-scope process types ─────────────
    # For planningid-scoped users (process_types=[]), derive from breakdown rows.
    # This ensures we average only the baselines relevant to this user's scope.
    actual_pts = process_types or [r["process_type"] for r in process_breakdown]
    eff_raw   = computed["efficiency_raw"] or 0
    eff_vs_bl = _eff_vs_bl_from_baselines(eff_raw, actual_pts, baselines)
    eff_rag   = _eff_rag(eff_vs_bl) if eff_vs_bl is not None else "GREEN"

    # Fill metrics_4w eff_vs_bl using same actual process types
    for wk, raw_eff in zip(metrics_4w, _raw_eff_by_week):
        wk["efficiency_vs_bl"] = _eff_vs_bl_from_baselines(raw_eff, actual_pts, baselines)

    # 3rd-tier fallback: breakdown entries with efficiency>0 but still no eff_vs_bl
    # (specific baseline missing and baseline_avg col also absent) — use scope average
    _scope_avg_bl = _eff_vs_bl_from_baselines(1.0, actual_pts, baselines)  # =1/avg_bl*100 ≡ inverse
    _avg_bl_val: float | None = None
    if _scope_avg_bl is not None and _scope_avg_bl > 0:
        _avg_bl_val = 1.0 / (_scope_avg_bl / 100)  # recover avg baseline value
    for _bd in process_breakdown:
        if _bd["eff_vs_bl"] is None and _bd["efficiency"] > 0 and _avg_bl_val:
            _bd["eff_vs_bl"] = round(_bd["efficiency"] / _avg_bl_val * 100, 1)

    # ── Operator breakdown (optional — only when skill has "operator_view" enabled) ──
    pri_metrics = set(skill.get("primary_metrics") or []) if skill else set()
    include_ops = bool(skill.get("operator_view") or skill.get("include_operator_breakdown")) if skill else False
    if include_ops:
        operator_breakdown = _load_operator_breakdown(
            client, combined_table, week_label, scope_filter, baselines,
        )
    else:
        operator_breakdown = []

    # ── Yield: every scoped profile (the headline shows it since OSI-008); alerts only when the profile asks ──
    yield_data   = _load_yield(client, skill, actual_pts, target_week)
    yield_current = yield_data["yield_current"]
    yield_rag_val = _yield_rag(yield_current) if yield_current is not None else "GREEN"
    yield_4w_list = yield_data["yield_4w"]
    # merge yield into metrics_4w by matching week string
    yield_by_week = {w["week"][:10]: w["yield"] for w in yield_4w_list}
    for wk in metrics_4w:
        wk["yield"] = yield_by_week.get(wk["week"][:10])
    # merge per-process-type and per-work-unit yield into the breakdowns
    yield_by_pt = yield_data.get("yield_by_pt", {})
    yield_by_pt_wu = yield_data.get("yield_by_pt_wu", {})
    for bd_entry in process_breakdown:
        pt = bd_entry["process_type"].lower()
        bd_entry["yield_pct"] = yield_by_pt.get(pt)
        for w in bd_entry.get("work_units", []):
            w["yield_pct"] = yield_by_pt_wu.get((pt, w["work_unit"]))
    yield_by_wu = yield_data.get("yield_by_wu", {})
    for w in workunit_breakdown:
        w["yield_pct"] = yield_by_wu.get(w["work_unit"])
    yield_by_pid = yield_data.get("yield_by_pid", {})
    for p_entry in planning_breakdown:
        p_entry["yield_pct"] = yield_by_pid.get(str(p_entry.get("planning_id", "")).lower())
    yield_note = YIELD_SD_ONLY_NOTE if yield_current is None else ""

    operator_levels_used = {}
    if operator_breakdown:
        try:
            op_sql = _YIELD_BY_OPERATOR_SQL.format(view=_YIELD_VIEW, target_week=target_week,
                                                   scope_filter=_build_yield_scope_filter(skill, actual_pts))
            op_yield = {}
            for r in client.execute_sql(op_sql, max_rows=5000).get("rows", []):
                num, den = float(r.get("yield_num") or 0), float(r.get("yield_den") or 0)
                op_yield[((r.get("pt") or "").lower(), (r.get("op") or "").lower())] = round(num / den * 100, 2) if den > 0 else None
            for o in operator_breakdown:
                y = op_yield.get((o["process_type"].lower(), str(o["operator"]).strip().lower()))
                # Yield counts reworked tasks resolved later on top; for one operator's few tasks that can
                # read above 100% (58 of 557 groups, 19-25 Oct), which is not a real yield: leave it out.
                o["yield_pct"] = y if y is None or y <= 100 else None
                o["yield_over_100"] = y is not None and y > 100
        except Exception as exc:
            print(f"[analytics] Yield (by operator) query failed: {exc}")
        from skill_registry import operator_levels
        operator_levels_used = operator_levels(skill or {})
        mark_operator_breaches(operator_breakdown, operator_levels_used)

    for rows in (process_breakdown, workunit_breakdown, planning_breakdown):
        _mark_small_samples(rows)

    return {
        "early_week":        early_week,
        "fta_current":       fta_current,
        "fta_prev_week":     fta_prev,
        "fta_trend":         _trend([r["fta"] for r in fta_4w]),
        "fta_rag":           _fta_rag(fta_current),
        "fta_4w":            fta_4w,
        "metrics_4w":        metrics_4w,
        "efficiency_raw":    computed["efficiency_raw"],
        "efficiency_vs_bl":  eff_vs_bl,
        "efficiency_rag":    eff_rag,
        "coq_current":       coq_current,
        "coq_rag":           _coq_rag(coq_current),
        "sampling_pct":      computed["sampling_pct"],
        "prod_tasks":        computed["prod_tasks"],
        "total_qc":          computed["total_qc"],
        "yield_current":     yield_current,
        "yield_rag":         yield_rag_val,
        "yield_note":        yield_note,
        "operator_levels":   operator_levels_used,
        "yield_4w":          yield_4w_list,
        "copq_hrs":          computed["copq_hrs"],
        "copq_pct":          computed["copq_pct"],
        "prod_hrs":          computed["prod_hrs"],
        "qc_hrs":            computed["qc_hrs"],
        "process_breakdown":    process_breakdown,
        "unsampled_breakdown":  unsampled_breakdown,
        "workunit_breakdown":   workunit_breakdown,
        "planning_breakdown":   planning_breakdown,
        "planning_missing":     planning_missing,
        "operator_breakdown":   operator_breakdown,
        "scope_label":          scope_label,
        "scope_mode":        skill.get("scope_mode", "defined") if skill else "defined",
        "week_label":        week_label,
        "target_week":       target_week,
        "data_label":        data_label,
        "report_type":       report_type,
        "source":            "Databricks — manual_efficiency_quality_all_weekly_tbl (live)",
        "as_of":             as_of,
        "live":              True,
        "error":             None,
    }


if __name__ == "__main__":
    import pprint
    # Simulate lalit's skill — no processType, fallback to planningid
    mock_skill = {"databricks_feature": "RMLanes"}
    pprint.pprint(run(mock_skill))
