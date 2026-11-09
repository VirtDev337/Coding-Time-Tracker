"""
Tests for TimeTracker Database Layer using standard unittest.
"""

import unittest
import tempfile
import os
from datetime import datetime

from timetracker.db import Database, format_duration


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db = Database(self.tmp.name)

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.remove(self.tmp.name)

    def test_record_heartbeat_and_stats(self):
        self.db.record_heartbeat(
            project_name="ProjectAlpha",
            category="coding",
            window_title="main.py - ProjectAlpha - Visual Studio Code",
            entity="main.py",
            duration_seconds=30
        )
        self.db.record_heartbeat(
            project_name="ProjectAlpha",
            category="collaboration",
            window_title="Antigravity - Pair Programming",
            entity="Antigravity",
            duration_seconds=20
        )
        self.db.record_heartbeat(
            project_name="ProjectAlpha",
            category="research",
            window_title="Python documentation - Google Chrome",
            entity="docs.python.org",
            duration_seconds=15
        )

        stats = self.db.get_today_stats()
        self.assertEqual(stats["total_seconds"], 65)
        self.assertEqual(stats["coding_seconds"], 30)
        self.assertEqual(stats["collaboration_seconds"], 20)
        self.assertEqual(stats["research_seconds"], 15)
        self.assertEqual(stats["project_count"], 1)

    def test_record_file_modifications(self):
        self.db.record_file_modification("ProjectAlpha", "src/main.py", count=3)
        self.db.record_file_modification("ProjectAlpha", "src/utils.py", count=1)

        top_files = self.db.get_top_files("ProjectAlpha")
        self.assertEqual(len(top_files), 2)
        self.assertEqual(top_files[0], ("src/main.py", 3))
        self.assertEqual(top_files[1], ("src/utils.py", 1))

    def test_get_report_data(self):
        self.db.record_heartbeat("ProjA", "coding", "title", "file.py", 3600)
        self.db.record_heartbeat("ProjA", "research", "title", "stackoverflow.com", 600)
        self.db.record_file_modification("ProjA", "file.py", 5)

        data = self.db.get_report_data()
        self.assertEqual(data["total_seconds"], 4200)
        self.assertEqual(data["total_coding_seconds"], 3600)
        self.assertEqual(data["total_research_seconds"], 600)
        self.assertEqual(len(data["projects"]), 1)
        self.assertEqual(data["projects"][0]["name"], "ProjA")
        self.assertEqual(len(data["projects"][0]["files"]), 1)

    def test_format_duration(self):
        self.assertEqual(format_duration(0), "0m")
        self.assertEqual(format_duration(45), "45s")
        self.assertEqual(format_duration(120), "2m")
        self.assertEqual(format_duration(3665), "1h 1m")


if __name__ == "__main__":
    unittest.main()
