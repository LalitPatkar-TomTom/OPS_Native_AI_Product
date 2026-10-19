"""Azure job version of sync_skills.py: same rules, reading the mounted opshub-skills share.

  - add profiles that exist only on the share
  - replace a profile only if the share copy is newer AND different
  - never delete
"""
import filecmp
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "/app/MultiAgent_Briefing")
from config import SKILLS_DIR  # noqa: E402

SUFFIX = "@tomtom.com_skill.md"
share = Path(os.getenv("OPS_SKILLS_SHARE", "/data/skills")) / "Personal Skills"
if not share.is_dir():
    sys.exit(f"skills share not mounted at {share}")

SKILLS_DIR.mkdir(parents=True, exist_ok=True)
local = {p.name.lower(): p for p in SKILLS_DIR.glob("*_skill.md")}
added = updated = kept = 0
for remote in share.iterdir():
    if not remote.name.lower().endswith(SUFFIX):
        continue
    mine = local.get(remote.name.lower())
    if mine is None:
        shutil.copy2(remote, SKILLS_DIR / remote.name)
        added += 1
        print(f"added   {remote.name}")
    elif remote.stat().st_mtime > mine.stat().st_mtime and not filecmp.cmp(remote, mine, shallow=False):
        shutil.copy2(remote, mine)
        updated += 1
        print(f"updated {mine.name}")
    else:
        kept += 1
print(f"skills sync: {added} added, {updated} updated, {kept} unchanged — {len(list(SKILLS_DIR.glob('*_skill.md')))} profiles")
