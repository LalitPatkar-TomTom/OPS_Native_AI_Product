#!/usr/bin/env bash
# ── Release the OPS Native AI engine to the Azure job: test → build → deploy → sanity check ──
# Run from the repo root with PIM active and on VPN:
#   bash azure/release.sh v2026-10-22-1 live        (or: parallel)
#   BACKUP_ONLY=1 bash azure/release.sh v2026-10-22-1 live   → window check + tests + backup + backup check only
# Rule book: no release during a run window; every release starts with a CHECKED backup of the shares.
# Each step stops the release when it fails. Reports land in test_reports/ — commit them with the
# release. Never start a manual run of the job to "test" it: that sends real emails.
set -euo pipefail

TAG="${1:?usage: bash azure/release.sh <image-tag> <live|parallel>}"
MODE="${2:?usage: bash azure/release.sh <image-tag> <live|parallel>}"
PY="${PYTHON:-python}"
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> [0/4] Release window (no run due or running)"
"$PY" azure/release_window.py || exit 1

echo "==> [1/4] Unit tests and profile check"
"$PY" scripts/run_checks.py || { echo "STOP: unit tests failed — nothing was built or deployed"; exit 1; }

# Rule book section 2: the shares hold the analytics DB, users, sessions and profiles; copy them all and check
# the copy before anything is built. Same backup folder as OPS Hub deploys, so each is checked against the last.
echo "==> [1b/4] Back up the Azure Files shares"
BACKUP_ROOT="${BACKUP_ROOT:-../OPSHUB/deploy/backups}"
BACKUP_DIR="$BACKUP_ROOT/$(date +%Y-%m-%d_%H%M)_nativeai-$TAG"
export AZURE_STORAGE_ACCOUNT="orbithubstorage"
# The key goes in an environment variable that az reads, never on a command line (it would show in process lists)
AZURE_STORAGE_KEY=$(az storage account keys list --account-name "$AZURE_STORAGE_ACCOUNT" -g ops-hub-rg   --query "[0].value" -o tsv | tr -d '\r')
export AZURE_STORAGE_KEY
for share in opshub-sessions opshub-config opshub-skills; do
  mkdir -p "$BACKUP_DIR/$share"
  az storage file download-batch --source "$share" --destination "$BACKUP_DIR/$share" --output none
done
unset AZURE_STORAGE_KEY
"$PY" azure/verify_backup.py "$BACKUP_DIR" --backups-root "$BACKUP_ROOT" || {
  echo "STOP: the backup is incomplete (see above) — nothing was built or deployed. Run the release again."; exit 1; }
echo "    backup kept in $BACKUP_DIR"
if [ "${BACKUP_ONLY:-0}" = "1" ]; then
  echo "BACKUP_ONLY=1: backup taken and checked; nothing was built or deployed."; exit 0
fi

echo "==> [2/4] Build image ops-native-ai:$TAG in ACR"
az acr build -r tomtomopshub -t "ops-native-ai:$TAG" . --no-logs

echo "==> [3/4] Update the job (secrets are read from .env and Azure; values are never printed)"
"$PY" azure/deploy_job.py --image "$TAG" --mode "$MODE"

echo "==> [4/4] Sanity check (read-only)"
# The job update returns while Azure is still provisioning; checking at once fails "Job provisioned".
for _ in $(seq 1 24); do
  state=$(az containerapp job show -n ops-native-ai-trigger -g ops-hub-rg --query properties.provisioningState -o tsv 2>/dev/null | tr -d '\r')
  [ "$state" = "InProgress" ] || break
  echo "    job still provisioning, waiting 10 s…"; sleep 10
done
"$PY" azure/sanity_check.py --image "$TAG" --mode "$MODE" || {
  echo "SANITY CHECK FAILED — roll back: python azure/deploy_job.py --image <previous tag> --mode $MODE"; exit 1; }

echo "Released ops-native-ai:$TAG ($MODE). Watch the next run report email, then commit test_reports/."
