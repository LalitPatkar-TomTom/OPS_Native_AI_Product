"""
Trigger Audit Log — SQLite-backed event store for all UC trigger runs.

Records every execution: who, what UC, when, metric values at time of trigger,
alert outcome, Jira summary. Used for operational analytics and debugging.

DB location: output/trigger_audit.db
Query helpers: recent_events(), user_history(), alert_history()
"""
import json
import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("audit_log")

_DB_PATH = Path(__file__).parent / "output" / "trigger_audit.db"

_DDL = """
CREATE TABLE IF NOT EXISTS trigger_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT    NOT NULL,          -- ISO-8601 UTC
    uc_id           TEXT    NOT NULL,          -- UC1 / UC2 / UC3 / UC4
    user_email      TEXT    NOT NULL,
    project_name    TEXT,
    status          TEXT,                      -- sent / suppressed / healthy / error
    -- Analytics snapshot
    fta_current     REAL,
    fta_rag         TEXT,
    fta_trend       TEXT,
    efficiency_vs_bl REAL,
    efficiency_rag  TEXT,
    coq_current     REAL,
    coq_rag         TEXT,
    week_label      TEXT,
    data_label      TEXT,
    process_types   TEXT,                      -- JSON list
    -- UC4 alert details
    metric_key      TEXT,
    alert_value     REAL,
    threshold_value REAL,
    alert_direction TEXT,
    -- Jira summary
    sla_breaches    INTEGER DEFAULT 0,
    sla_warnings    INTEGER DEFAULT 0,
    open_tickets    INTEGER DEFAULT 0,
    -- Error
    error_msg       TEXT
);

CREATE INDEX IF NOT EXISTS idx_te_user ON trigger_events(user_email);
CREATE INDEX IF NOT EXISTS idx_te_uc   ON trigger_events(uc_id);
CREATE INDEX IF NOT EXISTS idx_te_ts   ON trigger_events(ts);

-- One row per fire_all_now run, so missed / late slots are visible
CREATE TABLE IF NOT EXISTS trigger_runs (
    run_id          TEXT PRIMARY KEY,
    started_at      TEXT NOT NULL,             -- ISO-8601 UTC
    finished_at     TEXT,
    slot_date_ist   TEXT,                      -- YYYY-MM-DD of the slot served
    slot_ist        TEXT,                      -- 09:00 / 13:00 / 17:00 / 21:00
    delay_min       INTEGER,                   -- minutes after the slot time
    ucs_selected    TEXT,                      -- JSON list
    users           INTEGER,
    trigger_source  TEXT,                      -- scheduled / manual
    is_test         INTEGER DEFAULT 0,
    errors          INTEGER DEFAULT 0
);

-- One row per email handed to Outlook: who received what
CREATE TABLE IF NOT EXISTS email_deliveries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,             -- ISO-8601 UTC
    run_id          TEXT,
    uc_id           TEXT,
    profile_owner   TEXT,                      -- whose profile triggered it
    to_email        TEXT,
    cc_emails       TEXT,                      -- JSON list
    recipient_count INTEGER,
    subject         TEXT,
    has_attachment  INTEGER DEFAULT 0,
    sent_ok         INTEGER,                   -- 1 = accepted by Outlook
    is_test         INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ed_ts  ON email_deliveries(ts);
CREATE INDEX IF NOT EXISTS idx_ed_uc  ON email_deliveries(uc_id);
"""

# Columns added after the first release — created on existing databases at import
_MIGRATIONS = {
    "trigger_events": [
        ("run_id", "TEXT"),
        ("is_test", "INTEGER DEFAULT 0"),
        ("trigger_source", "TEXT"),
    ],
}

# Backups of the audit DB (consistent snapshots) — inside OneDrive, outside output/
BACKUP_DIR = Path(__file__).resolve().parent.parent / "analytics_backups"
_BACKUP_KEEP = 30

# Current run / use case, set by fire_all_now and trigger_engine so that
# deliver() and the log_* helpers can tag rows without extra parameters
_CTX: dict = {"run_id": None, "uc_id": None, "trigger_source": None, "is_test": False}


def _env_is_test() -> bool:
    """Runs with test switches must not count towards business value."""
    return any(os.getenv(k, "").strip() for k in
               ("TEST_RECIPIENT_OVERRIDE", "FORCE_UC4_ALERT", "PREVIEW_MODE", "OPS_AUDIT_TEST"))


@contextmanager
def _conn():
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_DB_PATH), timeout=10)   # same DB as uc4_state
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _init():
    with _conn() as con:
        con.executescript(_DDL)
        for table, cols in _MIGRATIONS.items():
            have = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
            for name, decl in cols:
                if name not in have:
                    con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


_init()


# ── Run context ────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_run(slot_date_ist: str, slot_ist: str, delay_min: int, ucs: list[str],
              users: int, trigger_source: str) -> str:
    """Record the start of a fire_all_now run and make it the current context."""
    run_id = uuid.uuid4().hex[:12]
    is_test = _env_is_test()
    _CTX.update(run_id=run_id, trigger_source=trigger_source, is_test=is_test)
    try:
        with _conn() as con:
            con.execute(
                "INSERT INTO trigger_runs (run_id, started_at, slot_date_ist, slot_ist, delay_min,"
                " ucs_selected, users, trigger_source, is_test) VALUES (?,?,?,?,?,?,?,?,?)",
                (run_id, _now(), slot_date_ist, slot_ist, delay_min, json.dumps(ucs),
                 users, trigger_source, int(is_test)))
    except Exception as exc:
        log.warning(f"[audit_log] start_run failed: {exc}")
    return run_id


def finish_run(errors: int = 0) -> None:
    run_id = _CTX.get("run_id")
    if not run_id:
        return
    try:
        with _conn() as con:
            con.execute("UPDATE trigger_runs SET finished_at=?, errors=? WHERE run_id=?",
                        (_now(), errors, run_id))
    except Exception as exc:
        log.warning(f"[audit_log] finish_run failed: {exc}")


def set_uc(uc_id: str | None) -> None:
    """Tag subsequent deliveries with the use case being run."""
    _CTX["uc_id"] = uc_id


def log_delivery(*, profile_owner: str, to_email: str, cc_emails: list[str] | None,
                 subject: str, has_attachment: bool, sent_ok: bool) -> None:
    """Called by delivery.deliver() for every email handed to Outlook."""
    cc = list(cc_emails or [])
    try:
        with _conn() as con:
            con.execute(
                "INSERT INTO email_deliveries (ts, run_id, uc_id, profile_owner, to_email, cc_emails,"
                " recipient_count, subject, has_attachment, sent_ok, is_test)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (_now(), _CTX.get("run_id"), _CTX.get("uc_id"), profile_owner, to_email,
                 json.dumps(cc), 1 + len(cc), subject, int(bool(has_attachment)),
                 int(bool(sent_ok)), int(_CTX.get("is_test") or _env_is_test())))
    except Exception as exc:
        log.warning(f"[audit_log] delivery log failed for {profile_owner}: {exc}")


def backup_daily() -> Path | None:
    """Keep one consistent snapshot per day in BACKUP_DIR (last 30 kept)."""
    target = BACKUP_DIR / f"trigger_audit_{datetime.now():%Y-%m-%d}.db"
    if target.exists():
        return None
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".db.tmp")
        src = sqlite3.connect(str(_DB_PATH), timeout=10)
        dst = sqlite3.connect(str(tmp))
        with dst:
            src.backup(dst)          # safe while WAL writers are active
        dst.close(); src.close()
        os.replace(tmp, target)
        for old in sorted(BACKUP_DIR.glob("trigger_audit_*.db"))[:-_BACKUP_KEEP]:
            old.unlink(missing_ok=True)
        log.info(f"[audit_log] daily backup -> {target}")
        return target
    except Exception as exc:
        log.warning(f"[audit_log] daily backup failed: {exc}")
        return None


# ── Write helpers ──────────────────────────────────────────────────────────────

def log_uc1(user: str, skill: dict, analytics: dict, jira: dict,
            status: str = "sent", error: str | None = None):
    """Log a UC1 (Daily Briefing) execution."""
    pts = skill.get("databricks_process_types") or []
    _insert(
        uc_id="UC1", user=user, skill=skill, status=status, error=error,
        analytics=analytics, jira=jira,
        process_types=json.dumps(pts),
    )


def log_uc2(user: str, skill: dict, jira: dict,
            status: str = "sent", error: str | None = None):
    """Log a UC2 (Jira SLA) check — 'sent' when an alert went out, else 'healthy'."""
    _insert(
        uc_id="UC2", user=user, skill=skill, status=status, error=error,
        analytics={}, jira=jira,
    )


def log_uc3(user: str, skill: dict, analytics: dict, jira: dict,
            status: str = "sent", error: str | None = None):
    """Log a UC3 (Weekly Report) execution."""
    pts = skill.get("databricks_process_types") or []
    _insert(
        uc_id="UC3", user=user, skill=skill, status=status, error=error,
        analytics=analytics, jira=jira,
        process_types=json.dumps(pts),
    )


def log_uc4(user: str, skill: dict, analytics: dict,
            metric_key: str, alert_value: float, threshold_value: float,
            direction: str, status: str, error: str | None = None):
    """Log a UC4 (Quality Alert) evaluation — one row per metric checked."""
    _insert(
        uc_id="UC4", user=user, skill=skill, status=status, error=error,
        analytics=analytics, jira={},
        metric_key=metric_key,
        alert_value=alert_value,
        threshold_value=threshold_value,
        alert_direction=direction,
    )


def log_skipped(uc_id: str, user: str, skill: dict, reason: str):
    """Log a UC that was due but deliberately not run (e.g. quiet hours)."""
    _insert(uc_id=uc_id, user=user, skill=skill, status="skipped",
            error=reason, analytics={}, jira={})


def log_error(uc_id: str, user: str, skill: dict, error: str):
    """Log any UC that crashed before producing analytics."""
    _insert(uc_id=uc_id, user=user, skill=skill, status="error",
            error=error, analytics={}, jira={})


def _insert(**kwargs):
    """Audit is best-effort: a DB error must never abort alert delivery."""
    try:
        _insert_row(**kwargs)
    except Exception as exc:
        log.warning(f"[audit_log] write failed for {kwargs.get('uc_id')} [{kwargs.get('user')}]: {exc}")


def _insert_row(*, uc_id, user, skill, status, error, analytics, jira,
                process_types=None, metric_key=None, alert_value=None,
                threshold_value=None, alert_direction=None):
    with _conn() as con:
        con.execute("""
            INSERT INTO trigger_events (
                ts, uc_id, user_email, project_name, status,
                fta_current, fta_rag, fta_trend,
                efficiency_vs_bl, efficiency_rag,
                coq_current, coq_rag,
                week_label, data_label, process_types,
                metric_key, alert_value, threshold_value, alert_direction,
                sla_breaches, sla_warnings, open_tickets,
                error_msg, run_id, is_test, trigger_source
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            _now(),
            uc_id,
            user,
            skill.get("project_name", ""),
            status,
            analytics.get("fta_current"),
            analytics.get("fta_rag"),
            analytics.get("fta_trend"),
            analytics.get("efficiency_vs_bl"),
            analytics.get("efficiency_rag"),
            analytics.get("coq_current"),
            analytics.get("coq_rag"),
            analytics.get("week_label"),
            analytics.get("data_label"),
            process_types,
            metric_key,
            alert_value,
            threshold_value,
            alert_direction,
            len(jira.get("sla_breaches", [])),
            len(jira.get("sla_warnings", [])),
            jira.get("total_open", 0),
            error,
            _CTX.get("run_id"),
            int(bool(_CTX.get("is_test") or _env_is_test())),
            _CTX.get("trigger_source"),
        ))


# ── Query helpers ──────────────────────────────────────────────────────────────

def recent_events(days: int = 7, uc_id: str | None = None,
                  user: str | None = None) -> list[dict]:
    """Return trigger events from the last N days, newest first."""
    clauses = [f"ts >= datetime('now', '-{days} days')"]
    params: list = []
    if uc_id:
        clauses.append("uc_id = ?");    params.append(uc_id)
    if user:
        clauses.append("user_email = ?"); params.append(user)
    where = " AND ".join(clauses)
    with _conn() as con:
        rows = con.execute(
            f"SELECT * FROM trigger_events WHERE {where} ORDER BY ts DESC", params
        ).fetchall()
    return [dict(r) for r in rows]


def alert_history(days: int = 30) -> list[dict]:
    """Return only rows where an alert was sent (status='sent', uc_id='UC4')."""
    with _conn() as con:
        rows = con.execute("""
            SELECT ts, user_email, project_name, metric_key,
                   alert_value, threshold_value, alert_direction, fta_current,
                   efficiency_vs_bl, coq_current, week_label
            FROM trigger_events
            WHERE uc_id = 'UC4'
              AND status = 'sent'
              AND ts >= datetime('now', ?)
            ORDER BY ts DESC
        """, (f"-{days} days",)).fetchall()
    return [dict(r) for r in rows]


def daily_summary(days: int = 14) -> list[dict]:
    """
    Aggregate view: one row per (date, user, UC) with counts and latest metrics.
    Useful for a quick health dashboard.
    """
    with _conn() as con:
        rows = con.execute("""
            SELECT
                DATE(ts)            AS date,
                user_email,
                uc_id,
                COUNT(*)            AS runs,
                SUM(CASE WHEN status='sent' THEN 1 ELSE 0 END)       AS alerts_sent,
                SUM(CASE WHEN status='error' THEN 1 ELSE 0 END)       AS errors,
                AVG(fta_current)    AS avg_fta,
                AVG(coq_current)    AS avg_coq,
                MAX(sla_breaches)   AS max_sla_breaches
            FROM trigger_events
            WHERE ts >= datetime('now', ?)
            GROUP BY DATE(ts), user_email, uc_id
            ORDER BY date DESC, user_email, uc_id
        """, (f"-{days} days",)).fetchall()
    return [dict(r) for r in rows]


def print_summary(days: int = 7):
    """CLI helper — print a quick audit summary to stdout."""
    rows = daily_summary(days)
    if not rows:
        print(f"No trigger events in the last {days} days.")
        return

    print(f"\n{'Date':<12} {'User':<32} {'UC':<5} {'Runs':>5} {'Alerts':>7} {'Errors':>7} {'Avg FTA':>9} {'Avg CoQ':>9} {'SLA Br':>7}")
    print("-" * 100)
    for r in rows:
        fta = f"{r['avg_fta']:.2f}%" if r['avg_fta'] is not None else "  N/A  "
        coq = f"{r['avg_coq']:.2f}%" if r['avg_coq'] is not None else "  N/A  "
        print(f"{r['date']:<12} {r['user_email']:<32} {r['uc_id']:<5} "
              f"{r['runs']:>5} {r['alerts_sent']:>7} {r['errors']:>7} "
              f"{fta:>9} {coq:>9} {r['max_sla_breaches'] or 0:>7}")


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print_summary(days)
    print("\n--- Recent Alerts (UC4) ---")
    for a in alert_history(days):
        print(f"  {a['ts'][:16]}  {a['user_email']:<30}  {a['metric_key']:12}"
              f"  value={a['alert_value']}  threshold={a['threshold_value']}"
              f"  dir={a['alert_direction']}")
