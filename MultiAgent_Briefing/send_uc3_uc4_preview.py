"""
send_uc3_uc4_preview.py — Send UC3 (Weekly Report) and UC4 (Quality Alert)
to real user inboxes as a preview.

Rules:
  - Emails go to the actual user (no TEST_RECIPIENT_OVERRIDE)
  - PREVIEW_MODE=1  — yellow preview banner asking for feedback
  - FORCE_UC4_ALERT=1 — alert fires for every user regardless of metric health
  - Real metric values shown (no fake numbers)
  - UC4 state is cleared so suppression doesn't block the preview

Usage:
    cd MultiAgent_Briefing
    python send_uc3_uc4_preview.py
"""
import os
import sys
import time
from pathlib import Path

os.environ["FORCE_UC4_ALERT"] = "1"
os.environ["PREVIEW_MODE"]    = "1"

sys.path.insert(0, str(Path(__file__).parent))

from config import SKILLS_DIR
from skill_registry import load_skill
from trigger_engine import _run_uc3, _run_uc4

from agents.uc4_state import clear_for_testing
clear_for_testing()

profiles = sorted(p for p in SKILLS_DIR.glob("*_skill.md") if "@" in p.name)

print("=" * 65)
print(f"  UC3 + UC4 Preview — sending to {len(profiles)} real users")
print(f"  UC4 in FORCE mode (fires even when metrics healthy)")
print(f"  PREVIEW banner enabled — real metric values shown")
print("=" * 65)

uc3_results = []
uc4_results = []

for skill_file in profiles:
    skill = load_skill(skill_file)
    user  = skill["user"]
    ucs   = {uc["uc_id"]: uc["active"] for uc in skill["use_cases"]}

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
    print(f"    Sent : {len(ok)}/{len(uc3_results)}")
    for r in uc3_results:
        status = "OK" if r["status"] == "OK" else f"FAILED — {r['status']}"
        print(f"    [{status}] {r['user']}")
else:
    print("    No users with UC3 Active.")

print(f"\n  UC4 Quality Alert (force mode — real values):")
if uc4_results:
    ok = [r for r in uc4_results if r["status"] == "OK"]
    print(f"    Sent : {len(ok)}/{len(uc4_results)} (FTA + CoQ alert per user)")
    for r in uc4_results:
        status = "OK" if r["status"] == "OK" else f"FAILED — {r['status']}"
        print(f"    [{status}] {r['user']}")
else:
    print("    No users with UC4 Active.")

print("=" * 65)
