"""Prototype mail, step 1 (read-only): pull the user's scope data into proto/data.json for exploration."""
import json, sys
sys.path.insert(0, ".")
from app.config import Settings
from app.main import _build_credential
from app.databricks.sql_client import DatabricksSQLClient, DatabricksError

OUT = sys.argv[1]
s = Settings()
c = DatabricksSQLClient(host=s.databricks_host, warehouse_id=s.databricks_sql_warehouse_id, quality_table="",
                        efficiency_table="", credential=_build_credential(s), pat_token=s.databricks_pat_token)
W = s.databricks_combined_table
PT = "('attr-cc-orbisconnectivity','attr-create-orbisconnectivity','orbis-create-lanesgaps')"
M = """SUM(Prod_Done_task_count) AS tasks, SUM(total_qc_count) AS qc, SUM(QC_Accept_Count) AS acc, SUM(QC_Reject_Count) AS rej,
ROUND(SUM(QC_Accept_Count)*100.0/NULLIF(SUM(total_qc_count),0),2) AS fta,
ROUND(SUM(Prod_Total_Time),1) AS prod_h, ROUND(SUM(qc_total_time),1) AS qc_h,
ROUND(COALESCE(SUM(qc_total_time),0)*100.0/NULLIF(COALESCE(SUM(Prod_Total_Time),0)+COALESCE(SUM(qc_total_time),0),0),2) AS coq,
ROUND(SUM(Prod_Done_task_count)/NULLIF(COALESCE(SUM(Prod_Total_Time),0)+COALESCE(SUM(qc_total_time),0),0),4) AS eff,
ROUND(AVG(NULLIF(Baseline,0)),4) AS bl"""
Q = {
 "weekly_pt": f"SELECT week_start, processType, {M} FROM {W} WHERE lower(processType) IN {PT} AND week_start >= '2026-08-24' GROUP BY 1,2 ORDER BY 1,2",
 "weekly_all": f"SELECT week_start, {M} FROM {W} WHERE lower(processType) IN {PT} AND week_start >= '2026-08-24' GROUP BY 1 ORDER BY 1",
 "wu": f"SELECT week_start, processType, work_unit, {M} FROM {W} WHERE lower(processType) IN {PT} AND week_start >= '2026-10-05' GROUP BY 1,2,3",
 "editor": f"SELECT week_start, processType, work_unit, Production_Editor AS editor, {M} FROM {W} WHERE lower(processType) IN {PT} AND week_start >= '2026-09-28' GROUP BY 1,2,3,4",
 "wp": f"SELECT week_start, processType, work_package, deliverable_id, planningid, {M} FROM {W} WHERE lower(processType) IN {PT} AND week_start >= '2026-10-05' GROUP BY 1,2,3,4,5",
 "tool": f"SELECT week_start, processType, tool, feature, value_Stream, {M} FROM {W} WHERE lower(processType) IN {PT} AND week_start >= '2026-10-05' GROUP BY 1,2,3,4,5",
 "daily": f"SELECT CAST(created_at AS DATE) AS d, processType, {M} FROM mo_occ_reporting.manual_efficiency.manual_efficiency_orbit_sd_daily_tbl WHERE lower(processType) IN {PT} AND created_at >= '2026-10-05' GROUP BY 1,2 ORDER BY 1",
 "qca": f"SELECT week_start, processType, qc_user, qc_work_unit, SUM(Accept_count) a, SUM(Reject_count) r, SUM(Invalid_rejection) inv, ROUND(SUM(qc_time),1) qh FROM {s.databricks_qca_table} WHERE lower(processType) IN {PT} AND week_start >= '2026-09-28' GROUP BY 1,2,3,4",
}
out = {}
for k, q in Q.items():
    try:
        out[k] = c._submit(q, 5000)["rows"]; print("OK ", k, len(out[k]))
    except DatabricksError as e:
        print("ERR", k, str(e)[:200])
json.dump(out, open(OUT, "w", encoding="utf-8"), default=str)
