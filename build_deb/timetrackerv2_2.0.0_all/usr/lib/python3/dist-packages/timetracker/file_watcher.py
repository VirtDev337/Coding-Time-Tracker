"""
File Watcher module.
Monitors file modifications within active project directories using Watchdog.
Safely ignores hidden/temporary files and avoids whole-system inotify exhaustion.
"""

from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from timetracker.db import Database


IGNORED_DIRECTORIES = {
    ".git", ".svn", ".hg", "__pycache__", ".vscode", ".idea",
    "node_modules", "venv", ".venv", "env", ".env", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "build", "dist", ".cache"
}

IGNORED_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".swp", ".swo", "~", ".tmp", ".log",
    ".DS_Store", ".sqlite", ".sqlite-journal", ".db-wal", ".db-shm"
}


class ProjectFileHandler(FileSystemEventHandler):
    def __init__(self, db: Database, project_name: str, base_dir: str):
        super().__init__()
        self.db = db
        self.project_name = project_name
        self.base_dir = os.path.abspath(base_dir)
        self.last_event_time: dict[str, float] = {}

    def should_ignore(self, path_str: str) -> bool:
        """Check if path is inside ignored folders or has ignored extension."""
        path = Path(path_str)
        # Check parts
        for part in path.parts:
            if part in IGNORED_DIRECTORIES or (part.startswith(".") and len(part) > 1 and not part.endswith(path.suffix)):
                return True
        if path.suffix in IGNORED_EXTENSIONS:
            return True
        return False

    def on_modified(self, event):
        if event.is_directory:
            return

        src = event.src_path
        if self.should_ignore(src):
            return

        now = time.time()
        # Debounce rapid save events on same file within 2.0s
        if src in self.last_event_time and (now - self.last_event_time[src]) < 2.0:
            return

        self.last_event_time[src] = now
        try:
            rel_path = os.path.relpath(src, self.base_dir)
        except ValueError:
            rel_path = src

        self.db.record_file_modification(self.project_name, rel_path, count=1)


class ProjectWatcher:
    """Manages active directory file watching for TimeTracker."""
    def __init__(self, db: Database):
        self.db = db
        self.observer: Optional[Observer] = None
        self.current_project: str = ""
        self.current_dir: str = ""

    def start(self):
        if not self.observer:
            self.observer = Observer()
            self.observer.start()

    def update_watch(self, project_name: str, project_dir: str):
        """Update observer to watch project_dir if it changed."""
        if not project_dir or not os.path.isdir(project_dir):
            return

        abs_dir = os.path.abspath(project_dir)
        if self.current_project == project_name and self.current_dir == abs_dir:
            return  # Already watching this project directory

        self.stop()
        self.current_project = project_name
        self.current_dir = abs_dir

        self.observer = Observer()
        handler = ProjectFileHandler(self.db, project_name, abs_dir)
        self.observer.schedule(handler, abs_dir, recursive=True)
        self.observer.start()

    def stop(self):
        if self.observer and self.observer.is_alive():
            try:
                self.observer.stop()
                self.observer.join(timeout=2.0)
            except Exception:
                pass
            self.observer = None
        self.current_project = ""
        self.current_dir = ""
