"""
send_preview_to_users.py — Send preview briefing emails to ALL real users.

Emails go to each user's actual address (no redirect).
A yellow preview banner is added at the top of every email asking for feedback.

Usage:
    cd MultiAgent_Briefing
    python send_preview_to_users.py

Remove this script (or just don't run it) after going live.
The PREVIEW_MODE flag is removed automatically in normal production runs.
"""
import os
import sys
import time
from pathlib import Path

# Preview mode ON — adds the feedback banner; no test redirect
os.environ["PREVIEW_MODE"] = "1"
# Make sure test redirect is cleared in case it was set in environment
os.environ.pop("TEST_RECIPIENT_OVERRIDE", None)

sys.path.insert(0, str(Path(__file__).parent))

from config import SKILLS_DIR
from orchestrator import run_uc1

profiles = sorted(SKILLS_DIR.glob("*_skill.md"))

print("=" * 65)
print(f"  UC1 Preview Send — {len(profiles)} profiles")
print(f"  Emails go to REAL users with preview banner")
print("=" * 65)

results = []

for i, skill_file in enumerate(profiles, 1):
    name = skill_file.name
    user = name.replace("_skill.md", "")
    print(f"\n[{i}/{len(profiles)}] {user}")
    print("-" * 55)
    try:
        out = run_uc1(skill_file)
        results.append({"profile": name, "status": "OK"})
        print(f"  -> Sent to {user}")
    except Exception as exc:
        results.append({"profile": name, "status": f"FAILED: {exc}"})
        print(f"  -> FAILED: {exc}")
    if i < len(profiles):
        time.sleep(2)

print("\n" + "=" * 65)
print("  SUMMARY")
print("=" * 65)
ok     = [r for r in results if r["status"] == "OK"]
failed = [r for r in results if r["status"] != "OK"]
print(f"  Sent    : {len(ok)}/{len(profiles)}")
if failed:
    print(f"  Failed  : {len(failed)}")
    for r in failed:
        print(f"    - {r['profile']}: {r['status']}")
print("=" * 65)
