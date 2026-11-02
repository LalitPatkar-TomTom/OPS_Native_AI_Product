"""Rule book section 1 guard (2 Nov 2026): no code deletes data — analytics, user data or backups — unnoticed.

Scans everything that goes into the image (MultiAgent_Briefing, azure, comms) and the scripts for delete
commands: file deletes, SQL DELETE / DROP / TRUNCATE and Azure share deletes. Every hit must be in ALLOWED
with the reason it is not data (a lock file, a temp copy, cool-down state). A new hit fails the tests, so a
delete can only come in after someone has written down why it is safe; deleting data needs the owner's OK.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCANNED = [ROOT / "MultiAgent_Briefing", ROOT / "azure", ROOT / "comms", ROOT / "scripts"]

DELETE = re.compile(
    r"(?-i:\brm\s+-|\brm\s+[\"'$/])|shutil\.rmtree|os\.remove\(|os\.unlink\(|\.unlink\(|\.rmdir\(|\.truncate\(|"
    r"\bDELETE\s+FROM\b|\bDROP\s+(TABLE|DATABASE|VIEW)\b|\bTRUNCATE\s+TABLE\b|"
    r"az\s+storage\s+\w+\s+delete|delete-batch|--delete-destination",
    re.I)

# (file, text on the line, why it is not data). Matched on text, not line numbers, so edits nearby still pass.
ALLOWED = [
    ("azure/entrypoint.sh", 'rm -f "$LOCK"', "the run lock file, removed when the run ends"),
    ("MultiAgent_Briefing/trigger_engine.py", "os.remove(attachment_path)",
     "temporary copy of the weekly Word report, removed after it was sent; the original stays in output/"),
    ("MultiAgent_Briefing/agents/uc4_state.py", "DELETE FROM uc4_alert_state",
     "clear_for_testing(): today's alert cool-down for test runs; not analytics"),
    ("azure/history_import.py", "DROP TABLE IF EXISTS history_log_daily",
     "rebuilds a derived table inside the snapshot copy made by copy_db_to_share.py, never the live DB"),
]


def _files():
    """Every .py and .sh file that is shipped or run by hand (not tests, not output)."""
    for base in SCANNED:
        for p in list(base.rglob("*.py")) + list(base.rglob("*.sh")):
            if "output" not in p.parts and "__pycache__" not in p.parts:
                yield p


def _hits() -> list[tuple[str, str]]:
    """(relative path, stripped line) for every line with a delete command."""
    out = []
    for p in _files():
        rel = p.relative_to(ROOT).as_posix()
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            if DELETE.search(line) and not line.lstrip().startswith("#"):
                out.append((rel, line.strip()))
    return out


def test_every_delete_command_is_allowed_with_a_reason():
    unexplained = [f"{f}: {line}" for f, line in _hits()
                   if not any(f == af and text in line for af, text, _ in ALLOWED)]
    assert not unexplained, ("Delete command without a reason (rule book section 1: data is never deleted; ask the owner, "
                             "then add it to ALLOWED with why it is not data):\n" + "\n".join(unexplained))


def test_allowed_list_has_no_stale_entries():
    # an entry whose code is gone would quietly allow a future delete with the same text
    hits = _hits()
    stale = [f"{af}: {text}" for af, text, _ in ALLOWED if not any(f == af and text in line for f, line in hits)]
    assert not stale, "Remove these from ALLOWED, the code is gone:\n" + "\n".join(stale)


def test_guard_catches_the_usual_delete_commands():
    for bad in ['rm -rf "$DATA/backups"', "shutil.rmtree(BACKUP_DIR)", "old.unlink(missing_ok=True)",
                'con.execute("DELETE FROM email_deliveries")', "DROP TABLE trigger_runs",
                "az storage file delete-batch --source opshub-config", "azcopy sync a b --delete-destination=true"]:
        assert DELETE.search(bad), bad
    for fine in ["truncated = plain[:4000]", "# rm -rf is never used here", "the user may remove a row",
                 "projects OM / RM / DPIP"]:
        assert not DELETE.search(fine) or fine.startswith("#"), fine


def test_daily_backup_moves_old_snapshots_to_archive_and_deletes_none(tmp_path, monkeypatch):
    import sqlite3
    from datetime import datetime
    import audit_log
    db = tmp_path / "trigger_audit.db"
    sqlite3.connect(db).execute("CREATE TABLE t (x)").connection.commit()
    backups = tmp_path / "backups"
    backups.mkdir()
    old = [backups / f"trigger_audit_2026-09-{d:02d}.db" for d in range(1, 31)] + \
          [backups / f"trigger_audit_2026-10-{d:02d}.db" for d in range(1, 6)]      # 35 older snapshots
    for p in old:
        p.write_text(p.name)
    (backups / "archive").mkdir()
    (backups / "archive" / old[0].name).write_text("kept from before")              # never overwritten
    monkeypatch.setattr(audit_log, "BACKUP_DIR", backups)
    monkeypatch.setattr(audit_log, "_DB_PATH", db)

    today = audit_log.backup_daily()

    assert today == backups / f"trigger_audit_{datetime.now():%Y-%m-%d}.db" and today.exists()
    kept = sorted(backups.glob("trigger_audit_*.db"))
    archived = sorted((backups / "archive").glob("trigger_audit_*.db"))
    # 36 snapshots (35 + today): the 6 oldest go to archive/, except old[0] whose name is already there
    assert {p.name for p in archived} == {p.name for p in old[:6]}
    assert (backups / "archive" / old[0].name).read_text() == "kept from before"      # never overwritten
    assert old[0].exists() and len(kept) == audit_log._BACKUP_KEEP + 1                # name clash: left in place
    assert len(kept) + len(archived) == len(old) + 1 + 1                              # nothing deleted
