"""Check that a pre-deploy backup of the Azure Files shares is complete; the deploy stops when it is not.

Rule book section 2 (2 Nov 2026): every deployment starts with a full backup of the live data, and the backup is
checked before anything is built. deploy.sh (OPS Hub) and azure/release.sh (OPS Native AI) run this right after
downloading the shares. The same file is kept in both repos (OPSHUB/deploy, OPS_Native_AI_Product/azure).

Checks, read-only:
  * every share folder exists and has files;
  * the key files are there and not empty: users, OPS Hub audit DB, usage log, Native AI analytics DB, profiles;
  * each SQLite DB opens read-only and passes PRAGMA quick_check (not half-copied);
  * each share has at least MIN_SHARE_RATIO of the files in the previous complete backup (catches a download that
    stopped early, like 2026-10-30_1530: 27 of 808 config files).
Writes backup_check.json into the backup folder (the result, kept with the backup). Exit 0 = complete, 1 = not.

Usage: python verify_backup.py <backup folder> [--backups-root <folder with earlier backups>]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

SHARES = ("opshub-sessions", "opshub-config", "opshub-skills")
KEY_FILES = (
    "opshub-config/allowed_users.json",          # who may use OPS Hub, and the admins
    "opshub-config/opshub_audit.db",             # OPS Hub users, email log
    "opshub-config/usage_log.jsonl",             # OPS Hub analytics
    "opshub-config/native-ai/trigger_audit.db",  # Native AI analytics: runs, emails, alerts
)
MIN_SKILL_FILES = 1                              # user profiles (SKILL.md) on opshub-skills
MIN_SHARE_RATIO = 0.9                            # vs the previous complete backup: shares only grow


def _count(folder: Path) -> int:
    """Number of files under folder (0 when it does not exist)."""
    return sum(1 for p in folder.rglob("*") if p.is_file()) if folder.is_dir() else 0


def _db_ok(path: Path) -> str:
    """'' when the SQLite file opens read-only and passes quick_check, else the problem."""
    try:
        # immutable=1: no locking and no -wal/-shm side files, so checking never adds files to a backup
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro&immutable=1", uri=True)
        try:
            res = con.execute("PRAGMA quick_check").fetchone()[0]
        finally:
            con.close()
        return "" if res == "ok" else f"quick_check: {res}"
    except sqlite3.Error as exc:
        return f"cannot open: {exc}"


def _previous(backups_root: Path, current: Path) -> tuple[Path | None, dict]:
    """The newest earlier backup that is complete, and its file counts.

    Earlier backups are walked oldest to newest. A backup with a backup_check.json uses its saved result; an
    older one (from before this check) is checked here, read-only, against the last complete backup before it.
    Why: a partial backup must never become the baseline, or the next partial one would look normal."""
    # folders are named by date and time (YYYY-MM-DD_HHMM...), so name order is time order
    earlier = sorted(p for p in backups_root.iterdir() if p.is_dir() and p.name < current.name)
    last, last_counts = None, {}
    for folder in earlier:
        rep = folder / "backup_check.json"
        if rep.exists():
            try:
                data = json.loads(rep.read_text(encoding="utf-8"))
            except ValueError:
                continue
        else:
            data = _check(folder, last_counts)
        if data.get("complete"):
            last, last_counts = folder, data.get("counts", {})
    return last, last_counts


def _check(backup: Path, prev_counts: dict) -> dict:
    """The checks on one folder, with prev_counts (file counts of the last complete backup) for the ratio rule."""
    problems: list[str] = []
    counts = {s: _count(backup / s) for s in SHARES}
    for share, n in counts.items():
        if n == 0:
            problems.append(f"{share}: no files (missing or empty download)")
    for rel in KEY_FILES:
        f = backup / rel
        if not f.is_file():
            problems.append(f"{rel}: missing")
        elif f.stat().st_size == 0:
            problems.append(f"{rel}: empty")
        elif f.suffix == ".db" and (err := _db_ok(f)):
            problems.append(f"{rel}: {err}")
    if len(list((backup / "opshub-skills").rglob("*.md"))) < MIN_SKILL_FILES:
        problems.append("opshub-skills: no profile (.md) files")
    for share in SHARES:
        before = prev_counts.get(share, 0)
        if before and counts[share] < before * MIN_SHARE_RATIO:
            problems.append(f"{share}: {counts[share]} files, the last complete backup had {before} "
                            f"(download stopped early?)")
    return {"complete": not problems, "problems": problems, "counts": counts}


def verify(backup: Path, backups_root: Path | None = None) -> dict:
    """Run every check on one backup folder; returns {"complete": bool, "problems": [...], "counts": {...}}.
    With backups_root, the file counts are also compared with the last complete earlier backup there."""
    prev_folder, prev_counts = _previous(backups_root, backup) if backups_root and backups_root.is_dir() else (None, {})
    result = _check(backup, prev_counts)
    result.update(compared_with=prev_folder.name if prev_folder else None,
                  checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    return result


def main(argv: list[str] | None = None) -> int:
    """Check the backup, write backup_check.json next to it, print the result; 0 = complete."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("backup", type=Path)
    ap.add_argument("--backups-root", type=Path, help="folder with earlier backups (default: the backup's parent)")
    a = ap.parse_args(argv)
    result = verify(a.backup, a.backups_root or a.backup.parent)
    (a.backup / "backup_check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for share, n in result["counts"].items():
        print(f"    {share}: {n} files")
    if result["complete"]:
        print(f"    backup complete (compared with {result['compared_with'] or 'no earlier checked backup'})")
        return 0
    print("    BACKUP INCOMPLETE:")
    for p in result["problems"]:
        print(f"      - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
