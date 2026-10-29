"""Per-user OAuth token store — one JSON file per user per provider.

Storage layout:
    tokens/
        lalit_patkar_at_tomtom_com_microsoft.json
        lalit_patkar_at_tomtom_com_slack.json
        ...
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_tokens_dir: Path | None = None


def init(tokens_dir: str | Path) -> None:
    global _tokens_dir
    _tokens_dir = Path(tokens_dir)
    _tokens_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Token store: %s", _tokens_dir)


def _path(email: str, provider: str) -> Path:
    if _tokens_dir is None:
        raise RuntimeError("token_store not initialised — call init() first")
    safe = email.replace("@", "_at_").replace(".", "_")
    return _tokens_dir / f"{safe}_{provider}.json"


def save(email: str, provider: str, data: dict) -> None:
    data["saved_at"] = datetime.now(timezone.utc).isoformat()
    p = _path(email, provider)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Token saved: %s / %s", email, provider)


def load(email: str, provider: str) -> dict | None:
    p = _path(email, provider)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def delete(email: str, provider: str) -> None:
    p = _path(email, provider)
    if p.exists():
        p.unlink()
        logger.info("Token deleted: %s / %s", email, provider)


def status(email: str) -> dict:
    """Return connection status for all providers."""
    ms = load(email, "microsoft")
    sl = load(email, "slack")
    return {
        "email": email,
        "microsoft": {
            "connected":    ms is not None,
            "covers":       ["Mail", "Teams", "Calendar"] if ms else [],
            "connected_at": ms.get("saved_at") if ms else None,
        },
        "slack": {
            "connected":    sl is not None,
            "team":         sl.get("team_name") if sl else None,
            "connected_at": sl.get("saved_at") if sl else None,
        },
    }
