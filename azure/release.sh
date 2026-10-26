#!/usr/bin/env bash
# ── Release the OPS Native AI engine to the Azure job: test → build → deploy → sanity check ──
# Run from the repo root with PIM active and on VPN:
#   bash azure/release.sh v2026-10-22-1 live        (or: parallel)
# Each step stops the release when it fails. Reports land in test_reports/ — commit them with the
# release. Never start a manual run of the job to "test" it: that sends real emails.
set -euo pipefail

TAG="${1:?usage: bash azure/release.sh <image-tag> <live|parallel>}"
MODE="${2:?usage: bash azure/release.sh <image-tag> <live|parallel>}"
PY="${PYTHON:-python}"
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> [1/4] Unit tests and profile check"
"$PY" scripts/run_checks.py || { echo "STOP: unit tests failed — nothing was built or deployed"; exit 1; }

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
