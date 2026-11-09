"""
Tests for Window Tracker and Title Parsers using standard unittest.
"""

import unittest
from timetracker.config import TrackerConfig
from timetracker.window_tracker import WindowTracker


class TestWindowTracker(unittest.TestCase):
    def setUp(self):
        self.wt = WindowTracker(TrackerConfig())

    def test_parse_vscode_title(self):
        proj, filename = self.wt.parse_ide_title("● main.py - AwesomeApp - Visual Studio Code", "code")
        self.assertEqual(proj, "AwesomeApp")
        self.assertEqual(filename, "main.py")

        proj, filename = self.wt.parse_ide_title("AwesomeApp - Visual Studio Code", "code")
        self.assertEqual(proj, "AwesomeApp")
        self.assertEqual(filename, "")

        proj, filename = self.wt.parse_ide_title("script.R - Analysis - RStudio", "rstudio")
        self.assertTrue("Analysis" in proj or "script.R" in proj)

    def test_parse_browser_title_research(self):
        domain, topic, cat = self.wt.parse_browser_title("Python - How to do X - Stack Overflow - Google Chrome")
        self.assertEqual(cat, "research")
        self.assertTrue("Stack Overflow" in domain or "stackoverflow" in domain.lower())

        domain, topic, cat = self.wt.parse_browser_title("VirtDev337/TimeTracker: GitHub - Mozilla Firefox")
        self.assertEqual(cat, "research")
        self.assertTrue("github" in domain.lower())

    def test_parse_browser_title_distraction(self):
        domain, topic, cat = self.wt.parse_browser_title("Trending Videos - YouTube - Brave")
        self.assertEqual(cat, "distraction")
        self.assertTrue("youtube" in domain.lower())


if __name__ == "__main__":
    unittest.main()
