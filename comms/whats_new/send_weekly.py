"""Send the weekly "What's new" email from opsai@ (MAIL_SENDER, Graph) — run by the Azure job on Fridays.

entrypoint.sh calls this after the Friday 17:00 IST run. It:
  1. takes the notes dated after the last email (marker on the share; first time: the last 7 days);
  2. stops without sending when there are none, or when this Friday was already sent;
  3. sends to every beta user (profile owners on the skills share) + the stakeholders, CC as configured;
  4. writes the marker, so a re-run never sends twice.
Usage (in the job): python /app/comms/whats_new/send_weekly.py [--dry-run] [--today YYYY-MM-DD]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import whats_new as W  # noqa: E402

DATA = Path(os.getenv("OPS_DATA_DIR", "/data/config/native-ai"))
MARKER = DATA / "whats_new_sent.json"


def profile_emails(skills_dir: Path) -> list[str]:
    """Owner email of every profile (file name '<email>_skill.md')."""
    return sorted({p.name[: -len("_skill.md")].lower() for p in skills_dir.glob("*_skill.md") if "@" in p.name})


def skills_dir() -> Path:
    """The profiles the job uses: OPS_SKILLS_DIR, else the mounted share."""
    return Path(os.getenv("OPS_SKILLS_DIR") or "/data/skills/Personal Skills")


def last_sent(marker: Path = MARKER) -> date | None:
    """The Friday of the last email sent, from the marker on the share."""
    try:
        return date.fromisoformat(json.loads(marker.read_text(encoding="utf-8"))["friday"])
    except Exception:
        return None


def plan(today: date, data: dict, users: list[str], sent: date | None) -> dict:
    """What to do this Friday: {"send": bool, "why": str, ...}; pure, for the tests."""
    if today.weekday() != 4:
        return {"send": False, "why": "not a Friday"}
    if sent and sent >= today:
        return {"send": False, "why": f"already sent for {sent}"}
    since = sent if sent and (today - sent).days <= 21 else None
    notes = W.week_notes(data, today, since)
    if not notes:
        return {"send": False, "why": "no notes this week"}
    to, cc = W.recipients(users)
    label = W.period(today, since)
    return {"send": True, "why": f"{len(notes)} notes", "to": to, "cc": cc, "subject": W.subject(today, since),
            "html": W.build(notes, data.get("coming_next", []), label), "notes": len(notes)}


def main(argv: list[str]) -> int:
    """Run the Friday send; prints one line for the run log. Exit 0 also when nothing is sent."""
    today = date.fromisoformat(argv[argv.index("--today") + 1]) if "--today" in argv else datetime.now().date()
    p = plan(today, W.load_notes(), profile_emails(skills_dir()), last_sent())
    if not p["send"]:
        print(f"What's new: not sent ({p['why']})")
        return 0
    if "--dry-run" in argv:
        print(f"What's new (dry run): {p['why']}, to {len(p['to'])}, cc {len(p['cc'])}: {p['subject']}")
        return 0
    sys.path.insert(0, "/app/MultiAgent_Briefing")
    import delivery
    ok = delivery._send_graph(";".join(p["to"]), p["subject"], p["html"], cc_emails=p["cc"])
    if ok:
        MARKER.parent.mkdir(parents=True, exist_ok=True)
        MARKER.write_text(json.dumps({"friday": today.isoformat(), "sent_at": datetime.now(timezone.utc).isoformat(),
                                      "to": len(p["to"]), "cc": len(p["cc"]), "notes": p["notes"]}), encoding="utf-8")
    print(f"What's new: {'sent' if ok else 'FAILED'} — {p['why']}, to {len(p['to'])}, cc {len(p['cc'])}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
