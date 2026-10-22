"""Post-deploy sanity check for the OPS Native AI Azure job — read-only.

    python azure/sanity_check.py [--image <tag>] [--mode live|parallel]

Run after azure/deploy_job.py (azure/release.sh calls it), with `az login` and PIM active. It only
reads the job definition and its recent executions; it never starts a run and never sends email.
Setting values are not read, only names, except the non-secret switches listed in SWITCHES.

Checks: the schedule, no automatic retry (a retry could send emails twice), owner-only delivery
(EMAIL_CC=off), the mode (EMAIL_PARALLEL_TO only in parallel mode), Graph mail settings, the share
mounts, the expected image, and that the last scheduled runs succeeded.

Writes test_reports/<date>_<time>_<commit>_sanity.md. Exit code 1 when a check FAILS.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RG, JOB = "ops-hub-rg", "ops-native-ai-trigger"
CRON = "30 3,7,11,15 * * *"                      # 09:00, 13:00, 17:00, 21:00 IST
REQUIRED_ENV = ["EMAIL_TRANSPORT", "MAIL_SENDER", "MAIL_CLIENT_ID", "MAIL_TENANT_ID", "MAIL_CLIENT_SECRET",
                "EMAIL_CC", "OPS_SKILLS_DIR", "RUN_REPORT_TO", "JIRA_API_TOKEN", "DATABRICKS_HOST"]
SWITCHES = {"EMAIL_CC", "EMAIL_TRANSPORT", "EMAIL_PARALLEL_TO", "OPS_SKILLS_DIR"}   # values read (not secrets)
TEST_SWITCHES = ["TEST_RECIPIENT_OVERRIDE", "FORCE_UC4_ALERT", "PREVIEW_MODE", "OPS_AUDIT_TEST"]

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool | None, detail: str = "", warn_only: bool = False) -> None:
    status = "PASS" if ok else ("WARN" if warn_only or ok is None else "FAIL")
    results.append((status, name, detail))
    print(f"  [{status}] {name}{' - ' + detail if detail else ''}")


def az(*args: str):
    r = subprocess.run(["az", *args, "-o", "json"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", shell=(sys.platform == "win32"),
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[-300:])
    return json.loads(r.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", help="expected image tag, e.g. v2026-10-22-1")
    ap.add_argument("--mode", choices=["live", "parallel"], default="live")
    a = ap.parse_args()
    print(f"OPS Native AI sanity check - job {JOB}")

    job = az("containerapp", "job", "show", "-n", JOB, "-g", RG)
    props, cfg = job["properties"], job["properties"]["configuration"]
    c = props["template"]["containers"][0]
    check("Job provisioned", props.get("provisioningState") == "Succeeded", props.get("provisioningState", ""))
    check("Schedule 09/13/17/21 IST", (cfg.get("scheduleTriggerConfig") or {}).get("cronExpression") == CRON,
          (cfg.get("scheduleTriggerConfig") or {}).get("cronExpression", ""))
    check("No automatic retry (no double emails)", cfg.get("replicaRetryLimit") == 0, f"retry={cfg.get('replicaRetryLimit')}")
    check("One run at a time", (cfg.get("scheduleTriggerConfig") or {}).get("parallelism") == 1)
    image = c.get("image", "")
    check("Image", a.image is None or image.endswith(f":{a.image}"), image)

    env = {e["name"]: e for e in c.get("env", [])}
    val = lambda n: env.get(n, {}).get("value") if n in SWITCHES else None
    missing = [n for n in REQUIRED_ENV if n not in env]
    check("Required settings present", not missing, "missing: " + ", ".join(missing) if missing else "all present")
    check("Owner-only delivery (EMAIL_CC=off)", val("EMAIL_CC") == "off", f"EMAIL_CC={val('EMAIL_CC')}")
    check("Mail through Microsoft Graph", val("EMAIL_TRANSPORT") == "graph", f"EMAIL_TRANSPORT={val('EMAIL_TRANSPORT')}")
    parallel = "EMAIL_PARALLEL_TO" in env
    check(f"Mode is {a.mode}", parallel == (a.mode == "parallel"), "EMAIL_PARALLEL_TO " + ("set" if parallel else "not set"))
    tests_on = [n for n in TEST_SWITCHES if n in env]
    check("No test switches", not tests_on, ", ".join(tests_on) or "none")
    for n in ("MAIL_CLIENT_SECRET", "JIRA_API_TOKEN"):
        if n in env:
            check(f"{n} comes from a secret", "secretRef" in env[n])
    mounts = [m.get("mountPath") for m in c.get("volumeMounts", [])]
    check("Share mounts (profiles, analytics DB)", {"/data/skills", "/data/config"} <= set(mounts), ", ".join(mounts))

    runs = az("containerapp", "job", "execution", "list", "-n", JOB, "-g", RG)
    runs = sorted(runs, key=lambda r: r["properties"].get("startTime", ""), reverse=True)[:4]
    detail = ", ".join(f'{r["properties"].get("startTime", "")[:16]} {r["properties"].get("status")}' for r in runs)
    check("Recent runs succeeded", bool(runs) and all(r["properties"].get("status") in ("Succeeded", "Running")
                                                       for r in runs), detail, warn_only=True)

    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip() or "nogit"
    failed = [r for r in results if r[0] == "FAIL"]
    now = datetime.now()
    out = ROOT / "test_reports" / f"{now:%Y-%m-%d_%H%M}_{commit}_sanity.md"
    out.parent.mkdir(exist_ok=True)
    lines = [f"# OPS Native AI post-deploy sanity check — {'FAILED' if failed else 'PASSED'}", "",
             f"- Date: {now:%Y-%m-%d %H:%M} (local time)", f"- Commit: {commit}", f"- Job: {JOB} ({RG})",
             f"- Image: {image}", f"- Expected mode: {a.mode}", "",
             "| Result | Check | Detail |", "|---|---|---|"]
    lines += [f"| {s} | {n} | {d.replace('|', '/')} |" for s, n, d in results]
    lines += ["", "The first scheduled run after the deploy is confirmed by the run report email "
              "(`[OPS Native AI run OK]`, azure/run_report.py)."]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{'FAILED' if failed else 'PASSED'} ({len(failed)} failed) - report {out.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
