"""
Manual Trigger — OPS Native AI
Run this to fire any use case immediately without waiting for the scheduler.

Usage:
    python run_now.py                  # interactive menu
    python run_now.py --uc UC1         # fire UC1 for the first skill found
    python run_now.py --uc UC1 --skill "john.doe@tomtom.com_skill.md"
"""
import sys
import argparse
from pathlib import Path

# Allow imports from this package
sys.path.insert(0, str(Path(__file__).parent))

from config import SKILLS_DIR, OUTPUT_DIR
from skill_registry import load_skill


UC_LABELS = {
    "UC1": "Daily Operational Briefing  (email + Teams)",
    "UC2": "Jira SLA Alert             (fires only if breaches found)",
    "UC4": "FTA Quality Alert          (fires only if FTA below threshold)",
}


def _pick_skill_file() -> Path:
    """List personal skill files and let user pick one interactively."""
    files = sorted([f for f in SKILLS_DIR.glob("*_skill.md") if "@" in f.name])
    if not files:
        print(f"\n  No personal skill files found in:\n    {SKILLS_DIR}")
        print("  Complete the onboarding form first to generate your skill profile.")
        sys.exit(1)

    if len(files) == 1:
        print(f"\n  Using skill file: {files[0].name}")
        return files[0]

    print("\n  Available skill profiles:")
    for i, f in enumerate(files, 1):
        try:
            s = load_skill(f)
            label = f"  {i}. {f.name}  ({s.get('project_name', '')})"
        except Exception:
            label = f"  {i}. {f.name}"
        print(label)

    while True:
        choice = input("\n  Select profile number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(files):
            return files[int(choice) - 1]
        print("  Invalid choice — enter a number from the list.")


def _pick_uc() -> str:
    """Interactive use case selection."""
    print("\n  Use cases:")
    for key, label in UC_LABELS.items():
        print(f"    {key}  —  {label}")

    while True:
        choice = input("\n  Select use case (UC1 / UC2 / UC4): ").strip().upper()
        if choice in UC_LABELS:
            return choice
        print("  Invalid — enter UC1, UC2, or UC4.")


def run(uc_id: str, skill_file: Path):
    from orchestrator import run_uc1, run_uc2, run_uc4

    skill = load_skill(skill_file)
    print(f"\n  Firing {uc_id} for: {skill['user']}")
    print(f"  Project : {skill.get('project_name', '')}  ({skill.get('jira_project', '')})")
    print(f"  Output  : {OUTPUT_DIR}")
    print("  " + "-" * 50)

    if uc_id == "UC1":
        out = run_uc1(skill_file)
        print(f"\n  Briefing saved -> {out}")

    elif uc_id == "UC2":
        out = run_uc2(skill_file)
        if out:
            print(f"\n  SLA alert saved -> {out}")
        else:
            print("\n  All Jira tickets on track — no SLA alert sent.")

    elif uc_id == "UC4":
        out = run_uc4(skill_file)
        if out:
            print(f"\n  FTA alert saved -> {out}")
        else:
            print("\n  FTA is healthy — no alert sent.")

    print("\n  Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OPS Native AI — Manual Trigger")
    parser.add_argument("--uc",    default=None, choices=["UC1", "UC2", "UC4"],
                        help="Use case to run")
    parser.add_argument("--skill", default=None,
                        help="Skill filename (e.g. john.doe@tomtom.com_skill.md) — default: interactive pick")
    args = parser.parse_args()

    print("=" * 55)
    print("  OPS Native AI — Manual Trigger")
    print("=" * 55)

    # Resolve skill file
    if args.skill:
        sf = SKILLS_DIR / args.skill if not Path(args.skill).is_absolute() else Path(args.skill)
        if not sf.exists():
            print(f"\n  Skill file not found: {sf}")
            sys.exit(1)
    else:
        sf = _pick_skill_file()

    # Resolve UC
    uc = args.uc if args.uc else _pick_uc()

    run(uc, sf)
