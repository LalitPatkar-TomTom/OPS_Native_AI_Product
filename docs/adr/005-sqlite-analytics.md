# ADR-005: Analytics in SQLite, copied in and out of the share for each run

**Status:** Accepted (20 Oct 2026, a single analytics master on Azure). Revisit before scale-out.

## Context
Every run, event and email has to be recorded for the business value analytics, and the history must
survive the container. SQLite directly on an SMB share (Azure Files) risks corruption through file
locking, and a managed database was not available in the landing zone.

## Decision
- **One master:** the analytics DB (`trigger_audit.db`) lives on the `opshub-config` share as the
  single master.
- **Copy per run:** each run copies it into the container, writes locally, and saves it back with
  SQLite's backup API (write-then-rename).
- **Backups:** daily snapshots, keeping the last 30.
- **Migration lock:** a marker file prevents the one-off laptop migration from ever overwriting the
  master.
- **Safety stop:** if the master is missing after the migration, the run stops before sending.

## Consequences
- **Consistent DB:** safe on SMB, no database service to run, and the DB is easy to copy for analysis.
- **Depends on the run lock:** it works only with one run at a time, which the run lock guarantees.
- **Read by other tools:** reports such as the weekly analytics and the impact report read the saved
  master.

## Revisit when
Parallel runs or near-real-time dashboards are needed. Then move to a managed store, such as Azure
SQL or Databricks Delta, with the same tables.
