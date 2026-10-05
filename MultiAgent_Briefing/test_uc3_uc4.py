"""
test_uc3_uc4.py — Test UC3 (Weekly Report) and UC4 (Quality Alert) for opted-in users.

Rules:
  - Only runs for users who have UC3 / UC4 marked ✅ Active in their skill file
  - All emails redirected to lalit.patkar@tomtom.com (TEST_RECIPIENT_OVERRIDE)
  - UC4 runs in FORCE mode so the alert fires even when metrics are healthy
  - UC4 state is cleared before the run so suppression doesn't block the test

Usage:
    cd MultiAgent_Briefing
    python test_uc3_uc4.py
"""
import os
import sys
import time
from pathlib import Path

# ── Test flags ─────────────────────────────────────────────────────────────────
os.environ["TEST_RECIPIENT_OVERRIDE"] = "lalit.patkar@tomtom.com"
os.environ["FORCE_UC4_ALERT"]         = "1"   # fire alert regardless of metric values
os.environ["PREVIEW_MODE"]            = "1"   # add preview banner

sys.path.insert(0, str(Path(__file__).parent))

from config import SKILLS_DIR
from skill_registry import load_skill
from trigger_engine import _run_uc3, _run_uc4

# Clear UC4 state so suppression doesn't block the test
from agents.uc4_state import clear_for_testing
clear_for_testing()

profiles = sorted(p for p in SKILLS_DIR.glob("*_skill.md") if "@" in p.name)

print("=" * 65)
print(f"  UC3 + UC4 Test Run — checking {len(profiles)} profiles")
print(f"  All emails -> lalit.patkar@tomtom.com")
print(f"  UC4 in FORCE mode (fires even when metrics healthy)")
print("=" * 65)

uc3_results = []
uc4_results = []

for skill_file in profiles:
    skill = load_skill(skill_file)
    user  = skill["user"]
    ucs   = {uc["uc_id"]: uc["active"] for uc in skill["use_cases"]}

    # ── UC3 ────────────────────────────────────────────────────────────────────
    if ucs.get("UC3"):
        print(f"\n[UC3] {user}")
        print("-" * 55)
        try:
            _run_uc3(skill, skill_file, user)
            uc3_results.append({"user": user, "status": "OK"})
            print(f"  -> OK")
        except Exception as exc:
            uc3_results.append({"user": user, "status": f"FAILED: {exc}"})
            print(f"  -> FAILED: {exc}")
        time.sleep(2)

    # ── UC4 ────────────────────────────────────────────────────────────────────
    if ucs.get("UC4"):
        print(f"\n[UC4] {user}")
        print("-" * 55)
        try:
            _run_uc4(skill, user)
            uc4_results.append({"user": user, "status": "OK"})
            print(f"  -> OK")
        except Exception as exc:
            uc4_results.append({"user": user, "status": f"FAILED: {exc}"})
            print(f"  -> FAILED: {exc}")
        time.sleep(2)

print("\n" + "=" * 65)
print("  SUMMARY")
print("=" * 65)

print(f"\n  UC3 Weekly Report:")
if uc3_results:
    ok = [r for r in uc3_results if r["status"] == "OK"]
    print(f"    Sent   : {len(ok)}/{len(uc3_results)}")
    for r in uc3_results:
        status = "OK" if r["status"] == "OK" else f"FAILED — {r['status']}"
        print(f"    [{status}] {r['user']}")
else:
    print("    No users with UC3 Active.")

print(f"\n  UC4 Quality Alert (force mode):")
if uc4_results:
    ok = [r for r in uc4_results if r["status"] == "OK"]
    print(f"    Sent   : {len(ok)}/{len(uc4_results)} (FTA + CoQ alert per user)")
    for r in uc4_results:
        status = "OK" if r["status"] == "OK" else f"FAILED — {r['status']}"
        print(f"    [{status}] {r['user']}")
else:
    print("    No users with UC4 Active.")

print(f"\n  Check lalit.patkar@tomtom.com inbox.")
print("=" * 65)
