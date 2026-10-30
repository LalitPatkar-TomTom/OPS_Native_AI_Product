"""Prototype mail, step 3 (read-only): can QC outcomes per task be linked to what the edit changed?"""
import json, sys
sys.path.insert(0, ".")
from app.config import Settings
from app.main import _build_credential
from app.databricks.sql_client import DatabricksSQLClient, DatabricksError
s = Settings()
c = DatabricksSQLClient(host=s.databricks_host, warehouse_id=s.databricks_sql_warehouse_id, quality_table="",
                        efficiency_table="", credential=_build_credential(s), pat_token=s.databricks_pat_token)
g = "maps_operations_published_catalog.orbit_sd_gold."
PT = "('attr-cc-orbisconnectivity','attr-create-orbisconnectivity','orbis-create-lanesgaps')"
Q = {
 "status": f"SELECT current_stage, current_status, rework, COUNT(*) n FROM {g}orbit_sd_maps_tasks_for_qc_sampling WHERE lower(process_type) IN {PT} AND production_done_at >= '2026-10-12' GROUP BY 1,2,3 ORDER BY 4 DESC LIMIT 30",
 "join": f"""SELECT t.current_status, t.rework, COUNT(DISTINCT t.task_id) tasks,
   ROUND(AVG(r.relations_count),2) rel, ROUND(AVG(r.relation_op_add_count),2) rel_add, ROUND(AVG(r.relation_op_delete_count),2) rel_del,
   ROUND(AVG(r.relation_tags_op_update_count),2) tag_upd, ROUND(AVG(r.relation_members_count),2) members
   FROM {g}orbit_sd_maps_tasks_for_qc_sampling t JOIN {g}orbit_sd_changelet_relations r ON r.issue = t.task_id
   WHERE lower(t.process_type) IN {PT} AND t.production_done_at >= '2026-10-12' GROUP BY 1,2 ORDER BY 3 DESC LIMIT 20""",
}
out = {}
for k, q in Q.items():
    try:
        out[k] = c._submit(q, 500)["rows"]; print("==", k, out[k][:30])
    except DatabricksError as e:
        print("ERR", k, str(e)[:300])
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), default=str)
