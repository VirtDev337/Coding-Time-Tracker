"""
TimeTracker Background Daemon.
Monitors active application focus, links research sessions to active projects,
and logs heartbeats to SQLite with idle detection.
"""

from __future__ import annotations
import os
import signal
import sys
import time
from datetime import datetime
from typing import Optional

from timetracker.config import load_config, TrackerConfig
from timetracker.db import Database
from timetracker.window_tracker import WindowTracker, WindowInfo, get_idle_seconds
from timetracker.file_watcher import ProjectWatcher


class TimeTrackerDaemon:
    def __init__(self, config: Optional[TrackerConfig] = None):
        self.config = config or load_config()
        self.db = Database(self.config.db_path)
        self.window_tracker = WindowTracker(self.config)
        self.file_watcher = ProjectWatcher(self.db)

        self.running = False
        self.last_active_project = ""
        self.last_active_project_dir = ""
        self.last_project_seen_time = 0.0

    def start(self, verbose: bool = False):
        """Run the main tracking loop until interrupted."""
        self.running = True
        self.file_watcher.start()

        def handle_signal(sig, frame):
            if verbose:
                print("\n[TimeTracker] Shutting down daemon gracefully...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        interval = max(1, self.config.poll_interval_seconds)

        if verbose:
            print(f"[TimeTracker] Daemon running. Polling every {interval}s. DB: {self.config.db_path}")

        while self.running:
            start_loop = time.time()
            try:
                self.tick(interval, verbose)
            except Exception as e:
                if verbose:
                    print(f"[TimeTracker] Error in tracking loop: {e}", file=sys.stderr)

            elapsed = time.time() - start_loop
            sleep_time = max(0.5, interval - elapsed)
            time.sleep(sleep_time)

    def tick(self, duration: int, verbose: bool = False):
        """Single sampling step."""
        # 1. Idle detection
        idle_secs = get_idle_seconds()
        if idle_secs > self.config.idle_threshold_seconds:
            if verbose:
                print(f"[Idle] User away ({idle_secs:.0f}s). Skipping heartbeat.")
            return

        # 2. Get active window
        info = self.window_tracker.get_active_window()
        if not info:
            return

        now = time.time()

        # 3. Handle Antigravity / AI Collaboration focus
        if info.category == "collaboration" or info.is_ai_collab:
            is_recent_project = (now - self.last_project_seen_time) < 1800 and bool(self.last_active_project)
            target_project = info.project_name or (self.last_active_project if is_recent_project else "Antigravity Collaboration")

            self.db.record_heartbeat(
                project_name=target_project,
                category="collaboration",
                window_title=info.window_title,
                entity=info.research_domain or "Antigravity Pair Programming",
                duration_seconds=duration
            )
            if verbose:
                print(f"[AI Collab] Project: {target_project} | Tool: Antigravity")

        # 4. Handle IDE focus
        elif info.is_ide and info.project_name:
            self.last_active_project = info.project_name
            self.last_active_project_dir = info.project_dir
            self.last_project_seen_time = now

            self.db.record_heartbeat(
                project_name=info.project_name,
                category="coding",
                window_title=info.window_title,
                entity=info.file_name,
                duration_seconds=duration
            )

            # Update the filesystem watcher to this project's directory
            if info.project_dir:
                self.file_watcher.update_watch(info.project_name, info.project_dir)

            # If a specific file is in focus, record touch
            if info.file_name:
                self.db.record_file_modification(info.project_name, info.file_name, count=1)

            if verbose:
                print(f"[Coding] Project: {info.project_name} | File: {info.file_name or 'N/A'} | Dir: {info.project_dir or 'N/A'}")

        # 5. Handle Browser focus
        elif info.is_browser:
            # Attribute to current project if IDE was active within last 30 minutes
            is_recent_project = (now - self.last_project_seen_time) < 1800 and bool(self.last_active_project)
            target_project = self.last_active_project if is_recent_project else "General Research"

            if info.category == "research":
                self.db.record_heartbeat(
                    project_name=target_project,
                    category="research",
                    window_title=info.window_title,
                    entity=info.research_domain or info.research_topic,
                    duration_seconds=duration
                )
                if verbose:
                    print(f"[Research] Project: {target_project} | Domain: {info.research_domain}")
            elif info.category == "distraction":
                if verbose:
                    print(f"[Distraction] {info.research_domain} (Not logged as dev time)")

        # 6. Handle Terminal focus
        elif info.is_terminal:
            is_recent = (now - self.last_project_seen_time) < 600 and bool(self.last_active_project)
            if is_recent:
                self.db.record_heartbeat(
                    project_name=self.last_active_project,
                    category="coding",
                    window_title=info.window_title,
                    entity="terminal",
                    duration_seconds=duration
                )
                if verbose:
                    print(f"[Terminal] Active for project {self.last_active_project}")

    def stop(self):
        """Stop tracking and cleanup."""
        self.running = False
        self.file_watcher.stop()


def main():
    daemon = TimeTrackerDaemon()
    daemon.start(verbose=True)


if __name__ == "__main__":
    main()
