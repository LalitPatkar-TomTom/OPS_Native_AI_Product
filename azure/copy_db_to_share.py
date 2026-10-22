"""ONE-TIME move of the laptop analytics DB to the Azure share, done on switch-over day.

Run by the user, with PIM active, between two runs (it reads the storage key; the key is never printed):
    python azure/copy_db_to_share.py            # checks everything, shows what it would do, changes nothing
    python azure/copy_db_to_share.py --go       # does it

After this the share copy (opshub-config/native-ai/trigger_audit.db) is the only analytics DB: every Azure run
loads it and saves it back, so all later events land there. A marker file (native-ai/MIGRATED_FROM_LAPTOP.json)
is written last, and the script refuses to run once the marker exists, so the laptop copy can never be pushed
over the Azure history again. There is no override: to redo a migration, the marker must be removed by hand.

Steps: laptop task disabled? -> no Azure run in progress? -> marker absent? -> consistent snapshot of the laptop
DB (SQLite backup API + integrity check) -> keep the Azure parallel DB as backups/trigger_audit.db.parallel-<ts>
-> upload -> download again and compare checksum and row counts -> upload everything else the laptop kept
(logs, briefings, UC3 reports, snapshots) to native-ai/laptop-history -> write the marker.
"""
import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ACCOUNT = "orbithubstorage"
SHARE = "opshub-config"
DIR = "native-ai"
DB = f"{DIR}/trigger_audit.db"
MARKER = f"{DIR}/MIGRATED_FROM_LAPTOP.json"
JOB, JOB_RG = "ops-native-ai-trigger", "ops-hub-rg"
LAPTOP_TASK = "OPS Native AI Trigger"
LAPTOP_DB = Path(__file__).resolve().parent.parent / "MultiAgent_Briefing" / "output" / "trigger_audit.db"


def az(*args: str, check: bool = True) -> str:
    """Run an az CLI command and return stdout; with check, exit with the stderr tail on failure."""
    r = subprocess.run(["az", *args], capture_output=True, text=True, shell=(sys.platform == "win32"))
    if check and r.returncode != 0:
        # stderr of az never contains the key; trim it anyway
        sys.exit(f"az {' '.join(a for a in args[:3])} failed: {r.stderr.strip()[-300:]}")
    return r.stdout.strip()


def counts(path: Path) -> dict:
    """Row count per table of a SQLite DB, opened read-only."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = [t for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in sorted(tables)}
    finally:
        con.close()


def sha256(path: Path) -> str:
    """Hex SHA-256 of the file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """One-time move of the laptop analytics DB to the Azure share (steps in the module docstring).

    Without --go only the checks run; any failed check exits. With --go it uploads, verifies and
    writes the marker last.
    """
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--go", action="store_true", help="really do it (without it: checks only)")
    a = ap.parse_args()

    # 1. the laptop must not run (and write its DB) during or after the move
    r = subprocess.run(["schtasks", "/Query", "/TN", LAPTOP_TASK, "/FO", "CSV", "/NH"], capture_output=True, text=True)
    state = r.stdout.strip().split(",")[-1].strip('"') if r.returncode == 0 else "not found"
    print(f"laptop task '{LAPTOP_TASK}': {state}")
    if state not in ("Disabled", "not found"):
        sys.exit("STOP: disable the laptop task first (Task Scheduler -> OPS Native AI Trigger -> Disable).")

    # 2. an Azure run in progress would save its own copy over the upload when it ends
    running = az("containerapp", "job", "execution", "list", "-n", JOB, "-g", JOB_RG,
                 "--query", "[?properties.status=='Running'].name", "-o", "tsv")
    if running:
        sys.exit(f"STOP: an Azure run is in progress ({running}); wait until it finishes.")
    print("Azure job: no run in progress")

    rg = az("storage", "account", "show", "-n", ACCOUNT, "--query", "resourceGroup", "-o", "tsv")
    key = az("storage", "account", "keys", "list", "-n", ACCOUNT, "-g", rg, "--query", "[0].value", "-o", "tsv")
    auth = ["--account-name", ACCOUNT, "--account-key", key]

    def exists(path: str) -> bool:
        """True if the path exists on the share."""
        return az("storage", "file", "exists", "--share-name", SHARE, "--path", path, *auth,
                  "--query", "exists", "-o", "tsv") == "true"

    # 3. one time only
    if exists(MARKER):
        sys.exit(f"STOP: {SHARE}/{MARKER} exists — the laptop DB was already moved. The Azure DB is the master; "
                 "nothing was changed.")

    # 4. consistent snapshot of the laptop DB
    if not LAPTOP_DB.exists():
        sys.exit(f"STOP: laptop DB not found at {LAPTOP_DB}")
    tmp = Path(tempfile.mkdtemp(prefix="nativeai_db_"))
    snap = tmp / "trigger_audit.db"
    src, dst = sqlite3.connect(f"file:{LAPTOP_DB}?mode=ro", uri=True), sqlite3.connect(snap)
    src.backup(dst)
    ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
    dst.close(); src.close()
    if ok != "ok":
        sys.exit(f"STOP: laptop DB integrity check failed: {ok}")
    # emails and runs of 1–13 Oct exist only in the laptop run log: add them as table history_log_daily
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from history_import import import_history
    h = import_history(snap, LAPTOP_DB.parent / "task_scheduler.log")
    print(f"pilot history from the run log added: {h['emails']} emails, {h['runs']} runs ({h['days'][0]} – {h['days'][-1]})")
    laptop_counts, laptop_sha = counts(snap), sha256(snap)
    print(f"laptop snapshot: {snap.stat().st_size:,} bytes, integrity ok, rows {laptop_counts}")

    share_has_db = exists(DB)
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    backup = f"{DIR}/backups/trigger_audit.db.parallel-{ts}"
    print(f"Azure DB on the share: {'present -> will be kept as ' + backup if share_has_db else 'none yet'}")

    if not a.go:
        print("\nCHECKS PASSED. Nothing changed. Run again with --go to move the DB.")
        return

    # 5. keep the Azure parallel DB
    if share_has_db:
        old = tmp / "azure_parallel.db"
        az("storage", "file", "download", "--share-name", SHARE, "--path", DB, "--dest", str(old), *auth, "-o", "none")
        if sha256(old) == laptop_sha:
            # an earlier attempt already uploaded this laptop copy; its parallel backup was made then
            share_has_db = False
            print("Azure DB is already this laptop copy (earlier attempt) — no second backup")
        else:
            az("storage", "directory", "create", "--share-name", SHARE, "--name", f"{DIR}/backups", *auth, "-o", "none")
            az("storage", "file", "upload", "--share-name", SHARE, "--source", str(old), "--path", backup, *auth, "-o", "none")
            print(f"kept Azure parallel DB as {backup} (rows {counts(old)})")

    # 6. upload and verify
    az("storage", "file", "upload", "--share-name", SHARE, "--source", str(snap), "--path", DB, *auth, "-o", "none")
    back = tmp / "verify.db"
    az("storage", "file", "download", "--share-name", SHARE, "--path", DB, "--dest", str(back), *auth, "-o", "none")
    if sha256(back) != laptop_sha or counts(back) != laptop_counts:
        sys.exit("STOP: the uploaded DB does not match the laptop snapshot. Marker NOT written; run again.")
    print(f"uploaded and verified: {SHARE}/{DB} (checksum and row counts match)")

    # 7. everything else the laptop kept (logs since 25 Sep, briefings, UC3 reports, snapshots) for analytics
    hist = tmp / "laptop-history"
    hist.mkdir()
    files = [p for p in LAPTOP_DB.parent.iterdir() if p.is_file() and not p.name.startswith("trigger_audit.db")]
    # plus the 19 Oct business value report and the data it was built from
    deployed = LAPTOP_DB.parents[3]
    files += sorted(deployed.glob("OPS_NativeAI_OPSHub_Business_Value_Report_*.*"))
    files += sorted((LAPTOP_DB.parents[2] / "business_analytics").glob("ba_data*.json"))
    dest = f"{DIR}/laptop-history"
    az("storage", "directory", "create", "--share-name", SHARE, "--name", dest, *auth, "-o", "none")

    def remote_sizes() -> dict:
        """File name -> size for the files in the laptop-history folder on the share."""
        # sizes in Python: a JMESPath like length(@) breaks the Windows command shell
        return {f["name"]: (f.get("properties") or {}).get("contentLength")
                for f in json.loads(az("storage", "file", "list", "--share-name", SHARE, "--path", dest,
                                       *auth, "-o", "json") or "[]")}

    # delta only: upload files that are missing on the share or have a different size
    have = remote_sizes()
    delta = [p for p in files if have.get(p.name) != p.stat().st_size]
    print(f"laptop history: {len(files)} files, {len(files) - len(delta)} already on the share, uploading {len(delta)}")
    if len(delta) > 20:
        for p in delta:
            (hist / p.name).write_bytes(p.read_bytes())
        az("storage", "file", "upload-batch", "--destination", SHARE, "--destination-path", dest,
           "--source", str(hist), *auth, "-o", "none")
    else:
        for p in delta:
            az("storage", "file", "upload", "--share-name", SHARE, "--source", str(p), "--path", f"{dest}/{p.name}",
               *auth, "-o", "none")
    have = remote_sizes()
    missing = [p.name for p in files if have.get(p.name) != p.stat().st_size]
    listed = len(files) - len(missing)
    if missing:
        print("not on the share (or a different size):", ", ".join(missing[:10]))
        sys.exit(f"STOP: only {listed} of {len(files)} history files arrived in {dest}. Marker NOT written; run again.")
    print(f"laptop history uploaded: {len(files)} files ({sum(p.stat().st_size for p in files):,} bytes) -> {SHARE}/{dest}")

    # 8. lock it: marker last, so a failed run above can simply be repeated
    marker = tmp / "MIGRATED_FROM_LAPTOP.json"
    marker.write_text(json.dumps({
        "migrated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(LAPTOP_DB), "sha256": laptop_sha, "rows": laptop_counts,
        "azure_parallel_backup": backup if share_has_db else None,
        "laptop_history": f"{DIR}/laptop-history ({len(files)} files)",
        "rule": "The Azure share DB is the only analytics DB from now on. Never upload a laptop copy over it.",
    }, indent=2), encoding="utf-8")
    az("storage", "file", "upload", "--share-name", SHARE, "--source", str(marker), "--path", MARKER, *auth, "-o", "none")
    print(f"marker written: {SHARE}/{MARKER} — this script will refuse to run again.")
    print("\nNext: python azure/deploy_job.py --image <tag> --mode live")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
