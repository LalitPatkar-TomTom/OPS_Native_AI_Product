"""
UC4 alert state — one alert per metric per user per day.

State stored in SQLite (shared with audit_log.db) using WAL mode —
safe for concurrent 30-min polls across many users running in parallel.
SQLite WAL mode allows multiple simultaneous readers + one writer
with no file corruption risk.

Table: uc4_alert_state  (inside output/trigger_audit.db)
"""
import logging
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import OUTPUT_DIR

log = logging.getLogger("uc4_state")

_DB_PATH = OUTPUT_DIR / "trigger_audit.db"

_DDL = """
CREATE TABLE IF NOT EXISTS uc4_alert_state (
    user_email  TEXT NOT NULL,
    metric_key  TEXT NOT NULL,
    alert_date  TEXT NOT NULL,          -- ISO date YYYY-MM-DD
    alerted_at  TEXT NOT NULL,          -- ISO-8601 UTC timestamp
    PRIMARY KEY (user_email, metric_key, alert_date)
);
"""


@contextmanager
def _conn():
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_DB_PATH), timeout=10)
    con.execute("PRAGMA journal_mode=WAL")   # concurrent write safety
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _init():
    with _conn() as con:
        con.executescript(_DDL)


_init()


def already_alerted_today(user: str, metric: str) -> bool:
    """True if a UC4 alert for this user+metric was already sent today."""
    today = date.today().isoformat()
    try:
        with _conn() as con:
            row = con.execute(
                "SELECT 1 FROM uc4_alert_state WHERE user_email=? AND metric_key=? AND alert_date=?",
                (user, metric, today),
            ).fetchone()
        return row is not None
    except Exception as exc:
        log.warning(f"[uc4_state] already_alerted_today failed — failing open: {exc}")
        return False   # fail open: allow alert rather than suppress


def mark_alerted(user: str, metric: str) -> None:
    """Record that a UC4 alert was sent for this user+metric today."""
    from datetime import datetime, timezone
    today = date.today().isoformat()
    now   = datetime.now(timezone.utc).isoformat()
    try:
        with _conn() as con:
            con.execute(
                """INSERT OR REPLACE INTO uc4_alert_state
                   (user_email, metric_key, alert_date, alerted_at)
                   VALUES (?, ?, ?, ?)""",
                (user, metric, today, now),
            )
        log.info(f"[uc4_state] Marked alerted: {user} / {metric} / {today}")
    except Exception as exc:
        log.error(f"[uc4_state] mark_alerted failed: {exc}")


def clear_for_testing(user: str | None = None) -> None:
    """
    Wipe today's alert state so test runs always fire.
    Pass user= to clear only one user; omit to clear all users for today.
    """
    today = date.today().isoformat()
    try:
        with _conn() as con:
            if user:
                con.execute(
                    "DELETE FROM uc4_alert_state WHERE alert_date=? AND user_email=?",
                    (today, user),
                )
            else:
                con.execute(
                    "DELETE FROM uc4_alert_state WHERE alert_date=?",
                    (today,),
                )
        log.info(f"[uc4_state] Cleared state for {user or 'all users'} / {today}")
    except Exception as exc:
        log.error(f"[uc4_state] clear_for_testing failed: {exc}")
