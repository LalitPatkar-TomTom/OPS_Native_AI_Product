"""
Pull personal skill.md files from the Azure Files share that OPS Hub writes to.

Users onboard via the OPS Hub form in Azure; the merged profile lands in
opshub-skills/Personal Skills/. This script runs before every scheduled
trigger run and copies those profiles into the local SKILLS_DIR.

Rules (safe by design):
  - add files that exist only on the share
  - replace a local file only if the share copy is newer AND different;
    the old local copy is backed up first
  - never delete local files
  - any failure is logged and the run carries on with the local files

Needs SKILLS_SYNC_URL and SKILLS_SYNC_SAS (read+list SAS) in the root .env.
"""
import logging
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import httpx

from config import SKILLS_DIR

log = logging.getLogger("sync_skills")
# httpx logs full request URLs at INFO — those carry the SAS token
logging.getLogger("httpx").setLevel(logging.WARNING)

_REMOTE_DIR = "Personal Skills"
_API_VERSION = "2023-11-03"
_SUFFIX = "@tomtom.com_skill.md"


def _url(base: str, sas: str, path: str, query: str = "") -> str:
    q = f"{query}&{sas}" if query else sas
    return f"{base.rstrip('/')}/{quote(path)}?{q}"


def _check(r: httpx.Response, what: str) -> None:
    """raise_for_status() without the SAS-bearing URL in the message."""
    if r.status_code >= 400:
        raise RuntimeError(f"{what}: HTTP {r.status_code} {r.reason_phrase}")


def _list_remote(client: httpx.Client, base: str, sas: str) -> list[str]:
    names, marker = [], ""
    while True:
        query = "restype=directory&comp=list" + (f"&marker={quote(marker)}" if marker else "")
        r = client.get(_url(base, sas, _REMOTE_DIR, query))
        _check(r, "list share")
        root = ET.fromstring(r.content)
        names += [e.findtext("Name") for e in root.iter("File")]
        marker = root.findtext("NextMarker") or ""
        if not marker:
            return [n for n in names if n and n.lower().endswith(_SUFFIX)]


def sync() -> dict:
    base = os.getenv("SKILLS_SYNC_URL", "")
    sas = os.getenv("SKILLS_SYNC_SAS", "").lstrip("?")
    if not base or not sas:
        log.warning("Skills sync skipped — SKILLS_SYNC_URL / SKILLS_SYNC_SAS not set")
        return {"skipped": True}

    stats = {"added": [], "updated": [], "unchanged": 0, "local_newer": [], "failed": []}
    backup_dir = SKILLS_DIR.parent / f"Personal Skills.backup_sync_{datetime.now():%Y-%m-%d}"
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=30, headers={"x-ms-version": _API_VERSION}) as client:
        for name in _list_remote(client, base, sas):
            try:
                r = client.get(_url(base, sas, f"{_REMOTE_DIR}/{name}"))
                _check(r, "download")
                remote_bytes = r.content
                remote_ts = parsedate_to_datetime(r.headers["Last-Modified"]).timestamp()
                local = SKILLS_DIR / name

                if local.exists():
                    if local.read_bytes() == remote_bytes:
                        stats["unchanged"] += 1
                        continue
                    if local.stat().st_mtime >= remote_ts:
                        # Edited locally after the share copy — keep the local one
                        stats["local_newer"].append(name)
                        continue
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(local, backup_dir / name)
                    stats["updated"].append(name)
                else:
                    stats["added"].append(name)

                tmp = local.with_suffix(".md.tmp")
                tmp.write_bytes(remote_bytes)
                os.replace(tmp, local)
                os.utime(local, (remote_ts, remote_ts))
            except (RuntimeError, httpx.HTTPError, OSError, KeyError) as exc:
                stats["failed"].append(name)
                log.error("Skills sync failed for %s: %s", name, type(exc).__name__ if isinstance(exc, httpx.HTTPError) else exc)

    log.info(
        "Skills sync: %d added %s, %d updated %s, %d unchanged, %d kept (local newer) %s, %d failed",
        len(stats["added"]), stats["added"], len(stats["updated"]), stats["updated"],
        stats["unchanged"], len(stats["local_newer"]), stats["local_newer"], len(stats["failed"]),
    )
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  [%(levelname)-8s]  %(message)s")
    try:
        sync()
    except Exception as exc:  # never block the trigger run
        msg = type(exc).__name__ if isinstance(exc, httpx.HTTPError) else exc   # httpx errors embed the URL
        log.error("Skills sync aborted — using local skill files: %s", msg)
    sys.exit(0)
