"""
Databricks SQL Statement Execution API client.
Self-contained — no dependency on MultiTenantAgent_V2.

SECURITY: Only SELECT / WITH (CTE) statements are permitted.
          Mutating SQL is rejected before reaching the warehouse.
"""
import logging
import re
import time

import httpx

logger = logging.getLogger(__name__)

_DATABRICKS_SCOPE = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default"


class DatabricksError(Exception):
    pass


class DatabricksSQLClient:
    def __init__(
        self,
        host: str,
        warehouse_id: str,
        credential,
        pat_token: str = "",
        registered_tables: list[str] | None = None,
    ):
        self._host = host.rstrip("/")
        self._warehouse_id = warehouse_id
        self._credential = credential
        self._pat_token = pat_token
        self._registered_tables: list[str] = registered_tables or []
        self._schema_cache: dict[str, list[dict]] = {}

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _headers(self) -> dict:
        token = self._pat_token or self._credential.get_token(_DATABRICKS_SCOPE).token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ── Security ──────────────────────────────────────────────────────────────

    @staticmethod
    def _assert_select_only(sql: str) -> None:
        stripped = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
        stripped = re.sub(r"--[^\n]*", " ", stripped)
        first_word = stripped.strip().split()[0].upper() if stripped.strip() else ""
        if first_word not in ("SELECT", "WITH"):
            raise DatabricksError(
                f"Only SELECT statements are permitted. Got: {first_word!r}"
            )

    def _assert_table_scope(self, sql: str, allowed_table: str) -> None:
        sql_lower = sql.lower()
        for table in self._registered_tables:
            if table == allowed_table:
                continue
            short = table.split(".")[-1].lower()
            if table.lower() in sql_lower or re.search(
                r"\b" + re.escape(short) + r"\b", sql_lower
            ):
                raise DatabricksError(
                    f"Table scope violation: this tool only queries '{allowed_table}'. "
                    f"Reference to '{table}' found. Use the correct tool for that table."
                )

    # ── Core execution ────────────────────────────────────────────────────────

    def _submit(self, sql: str, max_rows: int) -> dict:
        logger.info("SQL ▶ %.200s", sql.replace("\n", " "))
        try:
            r = httpx.post(
                f"{self._host}/api/2.0/sql/statements",
                headers=self._headers(),
                json={
                    "warehouse_id": self._warehouse_id,
                    "statement": sql,
                    "wait_timeout": "50s",
                    "on_wait_timeout": "CONTINUE",
                },
                timeout=65,
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DatabricksError(
                f"SQL submit {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc

        result = r.json()
        statement_id = result.get("statement_id")

        for elapsed in range(600):
            state = (result.get("status") or {}).get("state", "")
            if state == "SUCCEEDED":
                logger.info("SQL completed in ~%ds", elapsed)
                return self._format(result, max_rows)
            if state in ("FAILED", "CANCELED", "CLOSED"):
                msg = ((result.get("status") or {}).get("error") or {}).get("message", state)
                raise DatabricksError(f"SQL {state}: {msg}")
            if elapsed > 0 and elapsed % 30 == 0:
                logger.info("SQL still running… %ds elapsed", elapsed)
            time.sleep(1)
            try:
                poll = httpx.get(
                    f"{self._host}/api/2.0/sql/statements/{statement_id}",
                    headers=self._headers(),
                    timeout=60,
                )
                poll.raise_for_status()
                result = poll.json()
            except httpx.HTTPStatusError as exc:
                raise DatabricksError(f"Poll error: {exc.response.text[:200]}") from exc

        raise DatabricksError("SQL timed out after 10 minutes")

    def _fetch_chunk(self, statement_id: str, chunk_index: int) -> list:
        try:
            r = httpx.get(
                f"{self._host}/api/2.0/sql/statements/{statement_id}/result/chunks/{chunk_index}",
                headers=self._headers(),
                timeout=60,
            )
            r.raise_for_status()
            return r.json().get("data_array") or []
        except Exception as exc:
            logger.warning("Could not fetch chunk %d: %s", chunk_index, exc)
            return []

    def _format(self, result: dict, max_rows: int) -> dict:
        manifest = result.get("manifest") or {}
        data = result.get("result") or {}
        columns = [c["name"] for c in (manifest.get("schema") or {}).get("columns", [])]
        total_row_count = manifest.get("total_row_count", 0)
        raw_rows = data.get("data_array") or []

        if not raw_rows and total_row_count and total_row_count > 0:
            statement_id = result.get("statement_id", "")
            for chunk in (manifest.get("chunks") or []):
                if len(raw_rows) >= max_rows:
                    break
                raw_rows.extend(self._fetch_chunk(statement_id, chunk.get("chunk_index", 0)))

        rows = [dict(zip(columns, row)) for row in raw_rows[:max_rows]]
        return {
            "columns": columns,
            "rows": rows,
            "total_row_count": total_row_count or len(raw_rows),
            "returned": len(rows),
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def execute_sql(self, sql: str, max_rows: int = 100, allowed_table: str = "") -> dict:
        self._assert_select_only(sql)
        if allowed_table:
            self._assert_table_scope(sql, allowed_table)
        return self._submit(sql, max_rows)

    def get_schema(self, table: str) -> list[dict]:
        """Fetch and cache DESCRIBE TABLE result."""
        if table in self._schema_cache:
            return self._schema_cache[table]
        try:
            result = self._submit(f"DESCRIBE TABLE {table}", max_rows=300)
            schema = [
                r for r in result["rows"]
                if r.get("col_name") and not str(r["col_name"]).startswith("#")
            ]
            self._schema_cache[table] = schema
            return schema
        except Exception as exc:
            logger.warning("Could not fetch schema for %s: %s", table, exc)
            return []

    @staticmethod
    def schema_to_markdown(schema: list[dict]) -> str:
        if not schema:
            return "(schema unavailable)"
        lines = ["| Column | Type | Comment |", "| --- | --- | --- |"]
        for col in schema:
            lines.append(
                f"| `{col.get('col_name','')}` | {col.get('data_type','')} | "
                f"{str(col.get('comment') or '').strip()} |"
            )
        return "\n".join(lines)
