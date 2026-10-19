"""Create or update the Azure Container Apps job that runs the OPS Native AI trigger engine.

Run by the user (it handles secrets; values are never printed or kept on disk):
    python azure/deploy_job.py --image v2026-10-19 --mode parallel
    python azure/deploy_job.py --image v2026-10-19 --mode live

Secrets come from the root .env (same values the laptop uses), the Graph mail secret from the
OPS Hub container app, and the registry password from ACR. Re-running is safe (PUT = replace).
--mode parallel  every email goes only to PARALLEL_TO, no CCs, subject shows the real recipients
--mode live      emails go to the real recipients
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import dotenv_values

SUB = "30f2c75d-dc73-41db-81d4-93ec5702b79b"
RG = "ops-hub-rg"
JOB = "ops-native-ai-trigger"
ENV_ID = f"/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.App/managedEnvironments/cae-opshub-tt-network"
ACR = "tomtomopshub"
CRON = "30 3,7,11,15 * * *"           # 09:00, 13:00, 17:00, 21:00 IST (UTC+5:30, no DST)
PARALLEL_TO = "lalit.patkar@tomtom.com"
MAIL = {"EMAIL_TRANSPORT": "graph",
        "MAIL_TENANT_ID": "374f8026-7b54-4a3a-b87d-328fa26ec10d",
        "MAIL_CLIENT_ID": "098df35d-6e3d-4e40-ba22-2fe69543c01c",   # ops-hub-easyauth (option 2)
        "MAIL_SENDER": "opsai@tomtom.com",
        "MAIL_REPLY_TO": "lalit.patkar@tomtom.com"}

# .env keys that stay on the laptop (test switches, laptop-only sync, unrelated apps)
SKIP = re.compile(r"^(TEST_RECIPIENT_OVERRIDE|PREVIEW_MODE|FORCE_UC4_ALERT|OPS_AUDIT_TEST|SKILLS_SYNC_.*"
                  r"|GRAPH_.*|SLACK_.*|PORT|TEAMS_WEBHOOK_URL|EMAIL_.*|MAIL_.*|OPS_.*)$")
# Non-secret settings passed as plain values; every other key becomes a secret
PLAIN = {"DATABRICKS_HOST", "DATABRICKS_SQL_WAREHOUSE_ID", "DATABRICKS_LLM_MODEL", "JIRA_EMAIL",
         "ATL_EMAIL", "JIRA_BASE_URL", "JIRA_PROJECT", "JIRA_PROJECT_NUMERIC_ID", "JIRA_ISSUE_TYPE_ID",
         "COMBINED_TABLE", "LOG_LEVEL", "ATLASSIAN_VIA_MCP", "MCP_REGISTRY"}


def az(*args: str) -> str:
    r = subprocess.run(["az", *args, "-o", "tsv"], capture_output=True, text=True,
                       shell=(sys.platform == "win32"))
    if r.returncode != 0:
        sys.exit(f"az {args[0]} {args[1]} failed: {r.stderr.strip()[-300:]}")
    return r.stdout.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="image tag in ACR, e.g. v2026-10-19")
    ap.add_argument("--mode", choices=["parallel", "live"], required=True)
    a = ap.parse_args()

    env_file = Path(__file__).resolve().parent.parent / ".env"
    values = {k: v for k, v in dotenv_values(env_file).items() if v and not SKIP.match(k)}
    secrets, env = [], []
    for k, v in sorted(values.items()):
        if k in PLAIN:
            env.append({"name": k, "value": v})
        else:
            name = k.lower().replace("_", "-")
            secrets.append({"name": name, "value": v})
            env.append({"name": k, "secretRef": name})

    secrets.append({"name": "mail-client-secret",
                    "value": az("containerapp", "secret", "show", "-n", "tomtom-ops-hub", "-g", RG,
                                "--secret-name", "microsoft-provider-authentication-secret", "--query", "value")})
    env.append({"name": "MAIL_CLIENT_SECRET", "secretRef": "mail-client-secret"})
    secrets.append({"name": "acr-password",
                    "value": az("acr", "credential", "show", "-n", ACR, "--query", "passwords[0].value")})
    env += [{"name": k, "value": v} for k, v in MAIL.items()]
    if a.mode == "parallel":
        env.append({"name": "EMAIL_PARALLEL_TO", "value": PARALLEL_TO})

    body = {
        "location": az("containerapp", "env", "show", "--ids", ENV_ID, "--query", "location"),
        "properties": {
            "environmentId": ENV_ID,
            "configuration": {
                "triggerType": "Schedule",
                "replicaTimeout": 3600,
                "replicaRetryLimit": 0,          # no automatic retry: a retry could send emails twice
                "scheduleTriggerConfig": {"cronExpression": CRON, "parallelism": 1, "replicaCompletionCount": 1},
                "secrets": secrets,
                "registries": [{"server": f"{ACR}.azurecr.io", "username": ACR, "passwordSecretRef": "acr-password"}],
            },
            "template": {
                "containers": [{
                    "name": "engine",
                    "image": f"{ACR}.azurecr.io/ops-native-ai:{a.image}",
                    "resources": {"cpu": 1, "memory": "2Gi"},
                    "env": env,
                    "volumeMounts": [{"volumeName": "skills-store", "mountPath": "/data/skills"},
                                     {"volumeName": "config-store", "mountPath": "/data/config"}],
                }],
                "volumes": [{"name": "skills-store", "storageName": "skills-store", "storageType": "AzureFile"},
                            {"name": "config-store", "storageName": "config-store", "storageType": "AzureFile",
                             "mountOptions": "nobrl"}],
            },
        },
    }
    url = (f"https://management.azure.com/subscriptions/{SUB}/resourceGroups/{RG}"
           f"/providers/Microsoft.App/jobs/{JOB}?api-version=2024-03-01")
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "job.json"
        f.write_text(json.dumps(body), encoding="utf-8")
        r = subprocess.run(["az", "rest", "--method", "put", "--url", url, "--body", f"@{f}",
                            "--query", "properties.provisioningState", "-o", "tsv"],
                           capture_output=True, text=True, shell=(sys.platform == "win32"))
    if r.returncode != 0:
        sys.exit(f"job deploy failed: {r.stderr.strip()[-500:]}")
    print(f"job {JOB}: {r.stdout.strip()} | image ops-native-ai:{a.image} | mode {a.mode} | schedule {CRON} UTC")
    print("secrets set (names only):", ", ".join(s["name"] for s in secrets))
    print("plain settings:", ", ".join(e["name"] for e in env if "value" in e))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
