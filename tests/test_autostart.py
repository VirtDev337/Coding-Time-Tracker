"""
Tests for Autostart Manager (Linux and Windows).
"""

import unittest
from timetracker.autostart import (
    is_autostart_enabled,
    enable_autostart,
    disable_autostart,
    get_startup_script_dir
)


class TestAutostart(unittest.TestCase):
    def test_startup_scripts_exist(self):
        script_dir = get_startup_script_dir()
        self.assertTrue(script_dir.is_dir())
        self.assertTrue((script_dir / "enable_linux.sh").is_file())
        self.assertTrue((script_dir / "disable_linux.sh").is_file())
        self.assertTrue((script_dir / "enable_windows.bat").is_file())
        self.assertTrue((script_dir / "disable_windows.bat").is_file())

    def test_enable_and_disable_lifecycle(self):
        # Enable
        success, msg = enable_autostart()
        self.assertTrue(success)
        self.assertTrue(is_autostart_enabled())

        # Disable
        success, msg = disable_autostart()
        self.assertTrue(success)
        self.assertFalse(is_autostart_enabled())


if __name__ == "__main__":
    unittest.main()
