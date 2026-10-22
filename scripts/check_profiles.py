"""Read-only check of the personal SKILL.md profiles: does each one give the engine what it needs?

    python scripts/check_profiles.py ["<profiles folder>"]

Default folder: AI Architecture/skills/Personal Skills (the repo copy). The Azure job reads the
profiles from the OPS Hub share; pass that folder to check those. Nothing is sent or written —
the engine's output folder is pointed at a temporary directory. Prints one line per profile and
returns the list to scripts/run_checks.py, which puts it in the release report.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check_all(folder: Path) -> list[dict]:
    """Check each *_skill.md in folder: parses, valid recipient, an active UC, Jira key, UC4 alert level.

    Returns one row per profile (status OK/WARN/FAIL, issues). Sets OPS_OUTPUT_DIR to a temp dir if unset.
    """
    os.environ.setdefault("OPS_OUTPUT_DIR", tempfile.mkdtemp(prefix="profile-check-"))
    sys.path.insert(0, str(ROOT / "MultiAgent_Briefing"))
    from delivery import is_valid_recipient
    from skill_registry import load_skill

    rows = []
    for f in sorted(folder.glob("*_skill.md"), key=lambda p: p.name.lower()):
        issues = []
        try:
            s = load_skill(f)
        except Exception as exc:                       # a profile that cannot be read at all
            rows.append({"profile": f.name, "status": "FAIL", "issues": [f"cannot be parsed: {exc}"]})
            continue
        active = sorted(u["uc_id"] for u in s.get("use_cases", []) if u.get("active"))
        if not is_valid_recipient(s.get("user", "")):
            issues.append("file name is not a single @tomtom.com address — no email can be sent")
        if not active:
            issues.append("no use case marked Active")
        if {"UC1", "UC2", "UC3"} & set(active) and not s.get("jira_project"):
            issues.append("no Jira project key")
        if "UC4" in active and not any(v.get("alert") is not None for v in (s.get("metric_thresholds") or {}).values()):
            issues.append("UC4 active but no alert level")
        rows.append({"profile": f.name, "active": active, "status": "WARN" if issues else "OK", "issues": issues})
    return rows


if __name__ == "__main__":
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "AI Architecture" / "skills" / "Personal Skills"
    for r in check_all(folder):
        print(f"[{r['status']}] {r['profile']}  {' '.join(r.get('active', []))}  {'; '.join(r['issues'])}")
