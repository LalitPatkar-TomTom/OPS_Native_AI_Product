"""Rule book sections 2 and 7 (2 Nov 2026): a Native AI release never overlaps a run and starts with a checked backup.

* release_window.py blocks 15 minutes before to 45 minutes after each 09/13/17/21 IST run, matching the job CRON;
* release.sh runs the window check, then backs up all three shares and stops when verify_backup.py fails,
  with the storage key in an environment variable, never on a command line;
* azure/verify_backup.py is the same file as OPS Hub's deploy/verify_backup.py (checked when both repos are here).
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import deploy_job
import release_window as rw

ROOT = Path(__file__).resolve().parent.parent
IST = rw.IST


def _at(h, m, day=2):
    """2 Nov 2026 (a Monday) at h:m IST."""
    return datetime(2026, 11, day, h, m, tzinfo=IST)


def test_window_blocks_around_each_run_and_allows_between():
    assert rw.blocked_until(_at(8, 44)) is None
    assert rw.blocked_until(_at(8, 45)) == _at(9, 45)                 # 15 min before the 09:00 run
    assert rw.blocked_until(_at(9, 21)) == _at(9, 45)                 # run still writing the DB
    assert rw.blocked_until(_at(9, 45)) is None
    assert rw.blocked_until(_at(11, 0)) is None
    assert rw.blocked_until(_at(21, 30)) == _at(21, 45)


def test_window_works_from_utc_and_across_midnight():
    assert rw.blocked_until(datetime(2026, 11, 2, 3, 40, tzinfo=timezone.utc)) == _at(9, 45)   # 09:10 IST
    assert rw.blocked_until(_at(0, 30, day=3)) is None                # after the 21:00 run of the day before


def test_window_hours_match_the_job_schedule():
    minute, hours = deploy_job.CRON.split()[:2]
    utc = [datetime(2026, 11, 2, int(h), int(minute), tzinfo=timezone.utc).astimezone(IST) for h in hours.split(",")]
    assert sorted((t.hour, t.minute) for t in utc) == [(h, 0) for h in rw.RUN_HOURS_IST]


def test_release_script_checks_window_and_backup_before_building():
    sh = (ROOT / "azure" / "release.sh").read_text(encoding="utf-8")
    order = [sh.index(s) for s in ("release_window.py", "run_checks.py", "download-batch", "verify_backup.py",
                                   "az acr build")]
    assert order == sorted(order)
    for share in ("opshub-sessions", "opshub-config", "opshub-skills"):
        assert share in sh
    assert "--account-key" not in sh and "export AZURE_STORAGE_KEY" in sh
    assert "BACKUP_ONLY" in sh


def test_verify_backup_is_the_same_file_as_in_ops_hub():
    ours = (ROOT / "azure" / "verify_backup.py").read_text(encoding="utf-8")
    theirs = ROOT.parent / "OPSHUB" / "deploy" / "verify_backup.py"
    if theirs.exists():                                               # both repos side by side (laptop)
        assert ours == theirs.read_text(encoding="utf-8"), "copy deploy/verify_backup.py from OPS Hub again"


def test_verify_backup_stops_on_an_incomplete_backup(tmp_path):
    import verify_backup as v
    b = tmp_path / "2026-11-02_1000_nativeai-v1"
    (b / "opshub-config").mkdir(parents=True)
    (b / "opshub-config" / "allowed_users.json").write_text("{}")
    r = v.verify(b, tmp_path)
    assert not r["complete"]
    assert any("opshub-skills" in p for p in r["problems"]) and any("trigger_audit.db" in p for p in r["problems"])
    assert v.main([str(b)]) == 1 and (b / "backup_check.json").exists()


def test_release_script_has_no_raw_line_breaks_in_tr():
    # 2 Nov 2026: a patch had put a raw CR inside tr -d '...' instead of the two characters \r
    sh = open(ROOT / "azure" / "release.sh", encoding="utf-8", newline="").read()
    assert "tr -d '\r" not in sh and "tr -d '\n" not in sh and sh.count(r"tr -d '\r'") >= 2
