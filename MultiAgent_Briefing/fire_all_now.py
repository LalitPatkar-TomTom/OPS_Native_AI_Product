"""
fire_all_now.py — Non-interactive batch trigger for Windows Task Scheduler.

Fires all active UCs for every user whose skill file exists in Personal Skills/.
Smart UC selection based on time-of-day:

  09:00  → UC1 (morning briefing) + UC2 + UC4
  13:00  → UC2 + UC4
  17:00  → UC2 + UC4 + UC3 (if Friday)
  21:00  → UC2 + UC4

Run manually to test:
    python fire_all_now.py
    python fire_all_now.py --dry-run
"""
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

import pytz

sys.path.insert(0, str(Path(__file__).parent))

from config import SKILLS_DIR, OUTPUT_DIR
from skill_registry import load_skill

log_file = OUTPUT_DIR / "fire_all_now.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file), encoding="utf-8"),
    ],
)
log = logging.getLogger("fire_all_now")

IST = pytz.timezone("Asia/Kolkata")


def _which_ucs(hour_ist: int, weekday: int) -> list[str]:
    """Return list of UC IDs to fire based on IST hour and weekday (0=Mon, 4=Fri)."""
    ucs = []
    if hour_ist < 11:           # 09:00 slot — morning briefing
        ucs.append("UC1")
    ucs.append("UC2")           # Jira SLA check every slot
    ucs.append("UC4")           # Quality alert every slot (has built-in dedup)
    if weekday == 4 and hour_ist >= 16:   # Friday afternoon — weekly report
        ucs.append("UC3")
    return ucs


def fire_for_user(skill_file: Path, ucs: list[str], dry_run: bool):
    try:
        skill = load_skill(skill_file)
    except Exception as exc:
        log.error(f"  Could not load skill {skill_file.name}: {exc}")
        return

    user = skill.get("user", skill_file.stem)
    active_uc_ids = {uc["uc_id"] for uc in skill.get("use_cases", []) if uc.get("active")}

    log.info(f"\n  User: {user}  |  Active UCs: {sorted(active_uc_ids)}")

    for uc_id in ucs:
        if uc_id not in active_uc_ids:
            log.info(f"    SKIP {uc_id} — not active in skill profile")
            continue

        if dry_run:
            log.info(f"    DRY-RUN  {uc_id} would fire for {user}")
            continue

        log.info(f"    FIRE {uc_id} for {user}")
        try:
            _dispatch(uc_id, skill, skill_file, user)
        except Exception as exc:
            log.error(f"    ERROR {uc_id} [{user}]: {exc}", exc_info=True)


def _dispatch(uc_id: str, skill: dict, skill_file: Path, user: str):
    """
    Run one UC via the trigger engine's job — the single implementation of
    each UC (per-metric UC4 thresholds + directions, CC lists, UC3 Word
    attachment, audit log) and of the quiet-hours guard (UC4 may break it).
    """
    import trigger_engine
    trigger_engine._make_job(uc_id, skill, skill_file)()


def main():
    parser = argparse.ArgumentParser(description="OPS Native AI — batch trigger all users")
    parser.add_argument("--dry-run", action="store_true", help="Print what would run without executing")
    parser.add_argument("--uc", default=None, choices=["UC1","UC2","UC3","UC4"],
                        help="Force a specific UC regardless of time (e.g. --uc UC1)")
    args = parser.parse_args()

    now_ist  = datetime.now(IST)
    hour_ist = now_ist.hour
    weekday  = now_ist.weekday()
    ucs      = [args.uc] if args.uc else _which_ucs(hour_ist, weekday)

    log.info("=" * 60)
    log.info(f"fire_all_now starting — {now_ist.strftime('%Y-%m-%d %H:%M %Z')}")
    log.info(f"UCs to fire this slot: {ucs}  {'(DRY RUN)' if args.dry_run else ''}")
    log.info("=" * 60)

    skill_files = sorted([f for f in SKILLS_DIR.glob("*_skill.md") if "@" in f.name])
    if not skill_files:
        log.error(f"No skill files found in {SKILLS_DIR}")
        sys.exit(1)

    log.info(f"Users found: {len(skill_files)}")
    for sf in skill_files:
        fire_for_user(sf, ucs, dry_run=args.dry_run)

    log.info("\n" + "=" * 60)
    log.info("fire_all_now complete.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
