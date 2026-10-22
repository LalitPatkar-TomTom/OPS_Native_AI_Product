"""Pre-deploy gate for the OPS Native AI engine: unit tests + profile check, kept as release evidence.

    python scripts/run_checks.py            # exit code 0 only when every unit test passed

Writes test_reports/<date>_<time>_<commit>_unit.md (committed with the release). azure/release.sh
calls it before building the image. The unit tests are offline (no Jira, Confluence, Databricks,
Graph mail); the profile check only reads the SKILL.md files and reports issues as warnings.
"""
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "test_reports"


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True).stdout.strip()


def main() -> int:
    try:
        import pytest  # noqa: F401
    except ImportError:
        print("pytest is not installed: pip install -r requirements-dev.txt")
        return 2
    commit = git("rev-parse", "--short", "HEAD") or "nogit"
    dirty = bool(git("status", "--porcelain", "--untracked-files=no"))
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / "junit.xml"
        rc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:warnings",
                             f"--junitxml={junit}"], cwd=ROOT).returncode
        cases = []
        if junit.exists():
            for tc in ET.parse(junit).getroot().iter("testcase"):
                failed = tc.find("failure") is not None or tc.find("error") is not None
                cases.append((f'{tc.get("classname", "")}::{tc.get("name", "")}', not failed))
    passed = sum(ok for _, ok in cases)
    ok = rc == 0 and cases and passed == len(cases)

    # profiles: separate process so the engine modules load with a temporary output folder
    prof = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_profiles.py")], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    profile_lines = [l for l in prof.stdout.splitlines() if l.startswith("[")]

    now = datetime.now()
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"{now:%Y-%m-%d_%H%M}_{commit}_unit.md"
    lines = [f"# OPS Native AI unit tests — {'PASSED' if ok else 'FAILED'}", "",
             f"- Date: {now:%Y-%m-%d %H:%M} (local time)",
             f"- Commit: {commit}{' + uncommitted changes' if dirty else ''}",
             f"- Result: {passed} of {len(cases)} tests passed", "",
             "| Test | Result |", "|---|---|"]
    lines += [f"| `{name}` | {'pass' if good else '**FAIL**'} |" for name, good in cases]
    lines += ["", "## Profile check (repo copy, warnings only)", "",
              "The Azure job reads the profiles from the OPS Hub share; this checks the copy in the repo.", ""]
    lines += [f"- {l}" for l in profile_lines] or ["- (no profiles found)"]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    warns = sum(l.startswith(("[WARN]", "[FAIL]")) for l in profile_lines)
    print(f"{'PASSED' if ok else 'FAILED'}: {passed}/{len(cases)} tests; {len(profile_lines)} profiles, "
          f"{warns} with warnings - report {out.relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
