"""
File watcher for the skills/uploads/ directory.

Behaviour:
  - On server start: scans uploads/ and merges any file that has no matching
    combined output or whose source is newer than the combined output.
  - At runtime: triggers an LLM merge whenever a .md file is created or
    modified inside uploads/.

Uses the watchdog library for cross-platform inotify/FSEvents/ReadDirectoryChanges.
"""
import logging
import threading
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import merge_skills

logger = logging.getLogger(__name__)


class _UploadHandler(FileSystemEventHandler):
    """Handles file system events in the uploads directory."""

    def __init__(self, uploads_dir: Path, domains_dir: Path, combined_dir: Path, settings, credential=None):
        self._uploads_dir = uploads_dir
        self._domains_dir = domains_dir
        self._combined_dir = combined_dir
        self._settings = settings
        self._credential = credential
        self._lock = threading.Lock()  # one merge at a time per process

    def _trigger(self, path: str) -> None:
        p = Path(path)
        if p.suffix.lower() != ".md" or not p.is_file():
            return
        with self._lock:
            try:
                merge_skills.merge_if_stale(
                    user_skill_path=p,
                    domains_dir=self._domains_dir,
                    combined_dir=self._combined_dir,
                    databricks_host=self._settings.databricks_host,
                    databricks_pat_token=self._settings.databricks_pat_token,
                    databricks_llm_model=self._settings.databricks_llm_model,
                    credential=self._credential,
                )
            except Exception:
                logger.exception("Merge failed for: %s", p.name)

    def on_created(self, event):
        if not event.is_directory:
            logger.info("New skill upload detected: %s", Path(event.src_path).name)
            self._trigger(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            logger.info("Skill upload updated: %s", Path(event.src_path).name)
            self._trigger(event.src_path)


class SkillWatcher:
    """
    Wraps watchdog Observer. Start/stop via the FastAPI lifespan hook.

    On start, performs a backfill scan so any files dropped while the server
    was offline are merged before the first real request arrives.
    """

    def __init__(
        self,
        uploads_dir: Path,
        domains_dir: Path,
        combined_dir: Path,
        settings,
        credential=None,
    ):
        uploads_dir.mkdir(parents=True, exist_ok=True)
        combined_dir.mkdir(parents=True, exist_ok=True)

        self._uploads_dir = uploads_dir
        self._domains_dir = domains_dir
        self._combined_dir = combined_dir
        self._settings = settings
        self._credential = credential

        self._handler = _UploadHandler(uploads_dir, domains_dir, combined_dir, settings, credential)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(uploads_dir), recursive=False)

    def _backfill(self) -> None:
        """Merge any upload that is missing or stale in combined/."""
        for upload in self._uploads_dir.glob("*.md"):
            combined = self._combined_dir / upload.name
            if not combined.exists() or upload.stat().st_mtime > combined.stat().st_mtime:
                logger.info("Backfill merge: %s", upload.name)
                try:
                    merge_skills.merge_if_stale(
                        user_skill_path=upload,
                        domains_dir=self._domains_dir,
                        combined_dir=self._combined_dir,
                        databricks_host=self._settings.databricks_host,
                        databricks_pat_token=self._settings.databricks_pat_token,
                        databricks_llm_model=self._settings.databricks_llm_model,
                        credential=self._credential,
                    )
                except Exception:
                    logger.exception("Backfill merge failed for: %s", upload.name)

    def start(self) -> None:
        self._backfill()
        self._observer.start()
        logger.info("Skill watcher started — watching: %s", self._uploads_dir)

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
        logger.info("Skill watcher stopped")
