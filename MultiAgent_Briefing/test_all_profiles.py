"""
test_all_profiles.py — Run UC1 briefing for every personal skill profile
and deliver all emails to TEST_RECIPIENT_OVERRIDE (lalit.patkar@tomtom.com).

Usage:
    cd MultiAgent_Briefing
    python test_all_profiles.py

All 8 emails land in Lalit's inbox, each subject prefixed with
[TEST -> actual_recipient@tomtom.com] so you can see which profile it belongs to.
"""
import os
import sys
import time
from pathlib import Path

# Set test override BEFORE importing anything that reads env
os.environ["TEST_RECIPIENT_OVERRIDE"] = "lalit.patkar@tomtom.com"

sys.path.insert(0, str(Path(__file__).parent))

from config import SKILLS_DIR
from orchestrator import run_uc1

SKILLS_DIR_PATH = SKILLS_DIR

profiles = sorted(SKILLS_DIR_PATH.glob("*_skill.md"))

print("=" * 65)
print(f"  UC1 Test Run — {len(profiles)} profiles")
print(f"  All emails -> lalit.patkar@tomtom.com")
print("=" * 65)

results = []

for i, skill_file in enumerate(profiles, 1):
    name = skill_file.name
    print(f"\n[{i}/{len(profiles)}] {name}")
    print("-" * 55)
    try:
        out = run_uc1(skill_file)
        results.append({"profile": name, "status": "OK", "output": str(out)})
        print(f"  -> OK  {out.name}")
    except Exception as exc:
        results.append({"profile": name, "status": f"FAILED: {exc}", "output": ""})
        print(f"  -> FAILED: {exc}")
    # Small pause between sends to avoid Outlook rate-limit
    if i < len(profiles):
        time.sleep(2)

print("\n" + "=" * 65)
print("  SUMMARY")
print("=" * 65)
ok    = [r for r in results if r["status"] == "OK"]
failed = [r for r in results if r["status"] != "OK"]
print(f"  Passed : {len(ok)}/{len(profiles)}")
if failed:
    print(f"  Failed : {len(failed)}")
    for r in failed:
        print(f"    - {r['profile']}: {r['status']}")
print(f"\n  Check lalit.patkar@tomtom.com inbox for {len(ok)} test email(s).")
print("=" * 65)
