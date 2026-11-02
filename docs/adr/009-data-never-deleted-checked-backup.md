# ADR-009: Data is never deleted, and every release starts with a checked backup

**Status:** Accepted, 2 Nov 2026. Same decision as OPS Hub ADR-007. Source: the rule book
(`Deployed/RULEBOOK.md`, sections 1, 2, 6 and 7).

## Context
The job reads and writes the analytics DB, profiles and users on the same Azure Files shares as OPS Hub
(ADR-005). Gaps found on 1 Nov 2026:
- `azure/release.sh` took **no backup** before updating the job;
- `audit_log.backup_daily()` **deleted** daily DB snapshots older than the newest 30 (from about
  mid-November it would have started removing analytics backups);
- a release during a run could copy a half-written DB or cut the run off.

## Decision
- **No release in a run window:** `azure/release_window.py` blocks from 15 minutes before to 45 minutes
  after each 09/13/17/21 IST run (tested against the job CRON).
- **Checked backup before the build:** `release.sh` downloads all three shares into the same backup folder
  as OPS Hub deploys (`OPSHUB/deploy/backups`, so each backup is compared with the last complete one) and
  runs `azure/verify_backup.py` (same file as OPS Hub's); an incomplete backup stops the release. The
  storage key goes in `AZURE_STORAGE_KEY`, never on a command line. `BACKUP_ONLY=1` stops after the check.
- **Snapshots are archived, not deleted:** `backup_daily()` keeps the newest 30 in the backups folder and
  moves older ones to `backups/archive/` on the same share (a rename; a name already there is kept).
- **Delete guard:** `tests/test_no_data_delete.py` fails on any delete command in the shipped code or the
  scripts that is not listed with the reason it is not data.

## Consequences
- The share keeps every daily snapshot (about 2-3 MB each today); revisit storage when it passes 1 GB.
- A release can be refused by the window or by an incomplete backup; waiting or running it again is the fix.
