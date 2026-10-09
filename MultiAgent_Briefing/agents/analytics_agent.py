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
    """
    today = date.today()

    if report_type == "daily":
        prev = today - timedelta(days=1)
        while prev.weekday() >= 5:          # skip Saturday(5) / Sunday(6)
            prev -= timedelta(days=1)
        monday = prev - timedelta(days=prev.weekday())
        label  = f"as of {prev.strftime('%d %b %Y')} (yesterday)"
    else:                                   # "weekly"
        monday = today - timedelta(days=today.weekday())
        label  = f"week of {monday.strftime('%d %b %Y')}"

    return monday.strftime("%Y-%m-%d"), label


# ── SQL templates ──────────────────────────────────────────────────────────────
# {scope_filter} is injected at runtime via _build_scope_filter().
# {week_filter}  is injected at runtime via _compute_target().
# week_start is a DATE column — ORDER BY natively, no TO_DATE() needed.

_METRICS_SQL = """
SELECT
    week_start,
    ROUND(SUM(QC_Accept_Count) * 100.0 / NULLIF(SUM(total_qc_count), 0), 2)                  AS fta_pct,
    ROUND(SUM(Prod_Done_task_count) / NULLIF(SUM(Prod_Total_Time) + SUM(qc_total_time), 0), 4) AS efficiency,
    ROUND(SUM(qc_total_time) * 100.0 / NULLIF(SUM(Prod_Total_Time) + SUM(qc_total_time), 0), 2) AS coq_pct,
    AVG(NULLIF(Baseline, 0))                                                                    AS baseline_avg,
    SUM(total_qc_count)        AS total_qc,
    SUM(QC_Accept_Count)       AS accepted,
    SUM(Prod_Done_task_count)  AS prod_tasks,
    ROUND(SUM(Prod_Total_Time), 2) AS prod_hrs,
    ROUND(SUM(qc_total_time), 2)   AS qc_hrs
FROM {table}
WHERE week_start IS NOT NULL
  AND week_start <= '{target_week}'
  AND total_qc_count > 0
  {scope_filter}
GROUP BY week_start
ORDER BY week_start DESC
LIMIT 4
"""

_BREAKDOWN_SQL = """
SELECT
    processType AS process_type,
    ROUND(SUM(QC_Accept_Count) * 100.0 / NULLIF(SUM(total_qc_count), 0), 2)                  AS fta_pct,
    ROUND(SUM(Prod_Done_task_count) / NULLIF(SUM(Prod_Total_Time) + SUM(qc_total_time), 0), 4) AS efficiency,
    ROUND(SUM(qc_total_time) * 100.0 / NULLIF(SUM(Prod_Total_Time) + SUM(qc_total_time), 0), 2) AS coq_pct,
    AVG(NULLIF(Baseline, 0))                                                                    AS baseline_avg,
    SUM(total_qc_count)        AS total_qc,
    SUM(QC_Accept_Count)       AS accepted,
    SUM(Prod_Done_task_count)  AS prod_tasks,
    ROUND(SUM(Prod_Total_Time), 2) AS prod_hrs,
    ROUND(SUM(qc_total_time), 2)   AS qc_hrs,
    ROUND(SUM(Prod_Total_Time) + SUM(qc_total_time), 1) AS total_hrs
FROM {table}
WHERE week_start = '{week}'
  AND total_qc_count > 0
  AND processType IS NOT NULL
  {scope_filter}
GROUP BY processType
ORDER BY total_hrs DESC
LIMIT {limit}
"""


# ── Scope filter builder ───────────────────────────────────────────────────────

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
            parts.append(f"LOWER(processType) LIKE '%{name.lower()}%'")
            parts.append(f"LOWER(planningid) LIKE '%{name.lower()}%'")
        clause = "AND (" + " OR ".join(parts) + ")"
        label  = f"LIKE any of {explicit[:3]}{'...' if len(explicit) > 3 else ''}"
        return clause, label, 8

    return "", "all process types (full table)", 15


# ── RAG helpers ────────────────────────────────────────────────────────────────

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
    ROUND(SUM(Prod_Done_task_count) / NULLIF(SUM(Prod_Total_Time) + SUM(qc_total_time), 0), 4) AS efficiency,
    ROUND(SUM(qc_total_time) * 100.0 / NULLIF(SUM(Prod_Total_Time) + SUM(qc_total_time), 0), 2) AS coq_pct,
    AVG(NULLIF(Baseline, 0))                                                                    AS baseline_avg,
    SUM(Prod_Done_task_count) AS prod_tasks,
    SUM(total_qc_count)       AS total_qc,
    SUM(QC_Accept_Count)      AS accepted
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
  AND LOWER(work_unit) IN ('occ', 'dpu hyderabad', 'dpu noida', 'dpu globallogic', 'others')
  {scope_filter}
GROUP BY DATE_TRUNC('week', CAST(updated_at AS DATE))
ORDER BY week_mon DESC
LIMIT 4
"""

_YIELD_BY_PT_SQL = """
SELECT
    LOWER(process_type) AS pt,
    SUM(CASE WHEN to_status IN ('Resolved', 'DB alternatively updated')
             AND to_stage IN ('Resolution', 'Expert', 'Source Expert', 'OSM')
             THEN prod_count ELSE 0 END) AS yield_num,
    SUM(CASE WHEN COALESCE(n_rework_flag, 0) != 1
             AND to_stage IN ('Resolution', 'Expert', 'Source Expert', 'OSM')
             THEN prod_count ELSE 0 END) AS yield_den
FROM {view}
WHERE CAST(updated_at AS DATE) >= TO_DATE('{target_week}')
  AND CAST(updated_at AS DATE) <= DATE_ADD(TO_DATE('{target_week}'), 6)
  AND LOWER(work_unit) IN ('occ', 'dpu hyderabad', 'dpu noida', 'dpu globallogic', 'others')
  {scope_filter}
GROUP BY LOWER(process_type)
"""


# ── Baseline view (same source as ConfluenceAutoUpdate) ───────────────────────
_BASELINE_VIEW = "mo_occ_reporting.manual_efficiency.manual_efficiency_orbit_sd_daily_vw"

_BASELINES_SQL = f"""
SELECT LOWER(processType) AS pt,
       SUM(Prod_Done_task_count) / NULLIF(SUM(Prod_Total_Time) + SUM(qc_total_time), 0) AS hist_eff
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
        quoted = ", ".join(f"'{p.lower()}'" for p in pts)
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

    # ── Per-process-type for current week ─────────────────────────────────────
    yield_by_pt: dict[str, float | None] = {}
    try:
        pt_sql = _YIELD_BY_PT_SQL.format(view=_YIELD_VIEW, target_week=target_week, scope_filter=scope_filter)
        pt_result = client.execute_sql(pt_sql, max_rows=200)
        for r in pt_result.get("rows", []):
            pt  = (r.get("pt") or "").lower()
            num = float(r.get("yield_num") or 0)
            den = float(r.get("yield_den") or 0)
            if pt:
                yield_by_pt[pt] = round(num / den * 100, 2) if den > 0 else None
        print(f"[analytics] Yield by PT: {len(yield_by_pt)} process types")
    except Exception as exc:
        print(f"[analytics] Yield (by PT) query failed: {exc}")

    current = weekly[0]["yield"] if weekly else None
    print(f"[analytics] Yield loaded: current={current}  weeks={len(weekly)}")
    return {"yield_current": current, "yield_4w": weekly, "yield_by_pt": yield_by_pt}


# ── Databricks client factory ──────────────────────────────────────────────────

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
                     week containing the previous business day.
    """
    as_of = datetime.now(timezone.utc).isoformat()

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
    include_ops = bool(skill.get("include_operator_breakdown")) if skill else False
    if include_ops:
        operator_breakdown = _load_operator_breakdown(
            client, combined_table, week_label, scope_filter, baselines,
        )
    else:
        operator_breakdown = []

    # ── Yield (optional — only when skill has "yield" in primary_metrics) ────────
    if "yield" in pri_metrics:
        yield_data   = _load_yield(client, skill, actual_pts, target_week)
        yield_current = yield_data["yield_current"]
        yield_rag_val = _yield_rag(yield_current) if yield_current is not None else "GREEN"
        yield_4w_list = yield_data["yield_4w"]
        # merge yield into metrics_4w by matching week string
        yield_by_week = {w["week"][:10]: w["yield"] for w in yield_4w_list}
        for wk in metrics_4w:
            wk["yield"] = yield_by_week.get(wk["week"][:10])
        # merge per-process-type yield into breakdown
        yield_by_pt = yield_data.get("yield_by_pt", {})
        for bd_entry in process_breakdown:
            pt = bd_entry["process_type"].lower()
            bd_entry["yield_pct"] = yield_by_pt.get(pt)
    else:
        yield_current = None
        yield_rag_val = "GREEN"
        yield_4w_list = []

    return {
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
        "yield_4w":          yield_4w_list,
        "copq_hrs":          computed["copq_hrs"],
        "copq_pct":          computed["copq_pct"],
        "prod_hrs":          computed["prod_hrs"],
        "qc_hrs":            computed["qc_hrs"],
        "process_breakdown":    process_breakdown,
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
