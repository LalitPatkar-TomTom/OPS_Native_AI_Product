"""
UC4 alert state — one alert per metric per user per day.

Prevents the 30-min poller from spamming the same alert repeatedly.
State is stored in output/uc4_alert_state.json and resets automatically
when the date changes (no manual cleanup needed).
"""
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import OUTPUT_DIR

_STATE_FILE = OUTPUT_DIR / "uc4_alert_state.json"


def _load() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(state: dict) -> None:
    _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def already_alerted_today(user: str, metric: str) -> bool:
    """True if a UC4 alert for this user+metric was already sent today."""
    today = datetime.now().strftime("%Y-%m-%d")
    return _load().get(user, {}).get(metric) == today


def mark_alerted(user: str, metric: str) -> None:
    """Record that a UC4 alert was sent for this user+metric today."""
    state = _load()
    state.setdefault(user, {})[metric] = datetime.now().strftime("%Y-%m-%d")
    _save(state)


def clear_for_testing() -> None:
    """Wipe all state so test runs always fire the alert."""
    if _STATE_FILE.exists():
        _STATE_FILE.unlink()
