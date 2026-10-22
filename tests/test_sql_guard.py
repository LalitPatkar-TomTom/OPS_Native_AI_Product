"""Databricks access is read-only (agents/db_client.py) and profile values cannot change a query
(agents/analytics_agent.py). The Databricks identity must also be read-only; these checks are the
second line of defence."""
import pytest

import analytics_agent as aa
from db_client import DatabricksError, DatabricksSQLClient as C


@pytest.mark.parametrize("sql", [
    "SELECT 1", "  -- comment\nselect x from t", "/* c */ WITH a AS (SELECT 1) SELECT * FROM a",
    "select a from t where p = 'create-x';", "select updated_at, deleted from t",
    "select `update` from t", "select 'it''s; drop' from t"])
def test_read_queries_are_allowed(sql):
    C._assert_select_only(sql)


@pytest.mark.parametrize("sql", [
    "DELETE FROM t", "", "SHOW TABLES", "(SELECT 1)",
    "WITH a AS (SELECT 1) INSERT INTO t SELECT * FROM a", "SELECT 1; DROP TABLE t",
    "select 1 from t where x='a' ; drop table t --'","select * from t; update t set a=1"])
def test_write_or_multi_statements_are_refused(sql):
    with pytest.raises(DatabricksError):
        C._assert_select_only(sql)


def test_table_scope_blocks_other_registered_tables():
    c = C("https://h/", "w", None, registered_tables=["cat.sch.main_tbl", "cat.sch.other_tbl"])
    assert c._host == "https://h"
    with pytest.raises(DatabricksError):
        c._assert_table_scope("select * from other_tbl", "cat.sch.main_tbl")
    c._assert_table_scope("select * from cat.sch.main_tbl", "cat.sch.main_tbl")


def test_profile_values_are_escaped_in_scope_filter():
    clause, _, limit = aa._build_scope_filter({"databricks_process_types": ["x' OR 1=1 --"]})
    assert "'%x'' or 1=1 --%'" in clause and limit == 8
    C._assert_select_only(f"SELECT * FROM t WHERE 1=1 {clause}")       # still one harmless query


def test_scope_filter_modes():
    assert aa._build_scope_filter(None) == ("", "all process types (full table)", 15)
    assert aa._build_scope_filter({"databricks_process_types": ["PT-A"]})[0] == \
        "AND (LOWER(processType) LIKE '%pt-a%' OR LOWER(planningid) LIKE '%pt-a%')"


def test_yield_scope_filter_escapes_values():
    assert aa._build_yield_scope_filter({"scope_mode": "defined"}, ["A", "o'b"]) == \
        "AND LOWER(process_type) IN ('a', 'o''b')"
