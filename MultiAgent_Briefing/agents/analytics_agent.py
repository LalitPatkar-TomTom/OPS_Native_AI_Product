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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # MultiAgent_Briefing/
sys.path.insert(0, str(Path(__file__).resolve().parent))           # MultiAgent_Briefing/agents/

from config import (
    FTA_TARGET, FTA_ALERT,
    COQ_HEALTHY, COQ_MONITOR, COQ_INVESTIGATE,
)

# ── SQL templates ──────────────────────────────────────────────────────────────
# {scope_filter} is injected at runtime via _build_scope_filter().
# week_start is a DATE column — ORDER BY natively, no TO_DATE() needed.
# Column names confirmed against live information_schema (Databricks is case-insensitive).

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
    """Derive CopQ and efficiency-vs-baseline from a raw query result row."""
    total_qc   = float(row.get("total_qc")     or 0)
    accepted   = float(row.get("accepted")     or 0)
    prod_hrs   = float(row.get("prod_hrs")     or 0)
    qc_hrs     = float(row.get("qc_hrs")       or 0)
    baseline   = float(row.get("baseline_avg") or 0)
    efficiency = float(row.get("efficiency")   or 0)

    rejected  = total_qc - accepted
    total_hrs = prod_hrs + qc_hrs

    # CopQ = fraction of QC time attributable to rejected tasks
    copq_hrs = round((rejected / total_qc) * qc_hrs, 2) if total_qc > 0 else 0.0
    copq_pct = round(copq_hrs / total_hrs * 100, 2)     if total_hrs > 0 else 0.0

    eff_vs_baseline = round(efficiency / baseline * 100, 1) if baseline > 0 else None

    return {
        "copq_hrs":        copq_hrs,
        "copq_pct":        copq_pct,
        "eff_vs_baseline": eff_vs_baseline,
        "efficiency_raw":  efficiency,
        "total_hrs":       round(total_hrs, 2),
        "prod_hrs":        prod_hrs,
        "qc_hrs":          qc_hrs,
    }


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
        "process_breakdown": [],
        "scope_label":       "cached",
        "week_label":        "2026-08-23",
        "source":            "Confluence Progress Page (cached — Databricks offline)",
        "as_of":             datetime.now(timezone.utc).isoformat(),
        "live":              False,
        "error":             error,
    }


# ── Public entry point ─────────────────────────────────────────────────────────

def run(skill: dict | None = None) -> dict[str, Any]:
    """
    Fetch FTA, Efficiency, CoQ, CopQ and process-type breakdown from Databricks.

    Args:
        skill: parsed skill profile dict from skill_registry.load_skill().
               Used to build the scope filter (processType or planningid).
               Pass None to run unscoped (full table).
    """
    as_of = datetime.now(timezone.utc).isoformat()

    scope_filter, scope_label, bd_limit = _build_scope_filter(skill)

    try:
        client, combined_table = _build_client()
    except ValueError as exc:
        return _fallback(str(exc))

    # ── Main metrics: last 4 weeks ─────────────────────────────────────────────
    try:
        sql = _METRICS_SQL.format(table=combined_table, scope_filter=scope_filter)
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
        # Extended 4-week history with CoQ and efficiency (used by UC3 weekly report)
        metrics_4w = []
        for r in rows:
            bl  = float(r.get("baseline_avg") or 0)
            eff = float(r.get("efficiency")   or 0)
            metrics_4w.append({
                "week":           str(r.get("week_start")),
                "fta":            float(r.get("fta_pct")  or 0),
                "coq":            float(r.get("coq_pct")  or 0),
                "efficiency_vs_bl": round(eff / bl * 100, 1) if bl > 0 else None,
            })
        computed = _compute_metrics(current)

    except Exception as exc:
        return _fallback(f"Metrics query failed: {exc}")

    eff_vs_bl = computed["eff_vs_baseline"]
    eff_rag   = _eff_rag(eff_vs_bl) if eff_vs_bl is not None else "GREEN"

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
            bd = _compute_metrics(r)
            process_breakdown.append({
                "process_type": r.get("process_type", ""),
                "fta_pct":     float(r.get("fta_pct")    or 0),
                "fta_rag":     _fta_rag(float(r.get("fta_pct") or 0)),
                "efficiency":  float(r.get("efficiency")  or 0),
                "eff_vs_bl":   bd["eff_vs_baseline"],
                "coq_pct":     float(r.get("coq_pct")    or 0),
                "copq_hrs":    bd["copq_hrs"],
                "prod_tasks":  int(r.get("prod_tasks")   or 0),
                "total_hrs":   float(r.get("total_hrs")  or 0),
            })
    except Exception:
        pass  # breakdown is supplementary — don't fail the whole run

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
        "copq_hrs":          computed["copq_hrs"],
        "copq_pct":          computed["copq_pct"],
        "prod_hrs":          computed["prod_hrs"],
        "qc_hrs":            computed["qc_hrs"],
        "process_breakdown": process_breakdown,
        "scope_label":       scope_label,
        "scope_mode":        skill.get("scope_mode", "defined") if skill else "defined",
        "week_label":        week_label,
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
