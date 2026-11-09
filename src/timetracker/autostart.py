"""
Autostart Manager for TimeTracker.
Enables or disables automatic startup at login on Linux and Windows.
Provides native Python implementations and acts as backend for both CLI and GUI.
"""

from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple


def get_startup_script_dir() -> Path:
    """Return the absolute path to the project's startup/ directory."""
    # Assuming this file is at src/timetracker/autostart.py
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "startup"


def is_autostart_enabled() -> bool:
    """Check if TimeTracker is configured to start automatically at login."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return False
        startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        vbs_file = startup_dir / "TimeTrackerStartup.vbs"
        bat_file = startup_dir / "TimeTrackerStartup.bat"
        return vbs_file.is_file() or bat_file.is_file()

    # Linux: check XDG autostart or systemd user service
    desktop_file = Path.home() / ".config" / "autostart" / "timetracker.desktop"
    if desktop_file.is_file():
        return True

    # Check systemd user service
    if shutil.which("systemctl"):
        try:
            res = subprocess.run(
                ["systemctl", "--user", "is-enabled", "timetracker.service"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            if res.returncode == 0 and "enabled" in res.stdout:
                return True
        except Exception:
            pass

    return False


def enable_autostart() -> Tuple[bool, str]:
    """Enable automatic startup at user login."""
    if sys.platform == "win32":
        script_path = get_startup_script_dir() / "enable_windows.bat"
        if script_path.is_file():
            try:
                res = subprocess.run([str(script_path)], capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    return True, "Enabled autostart in Windows Startup folder."
            except Exception as e:
                pass

        # Native Python fallback for Windows
        try:
            appdata = os.environ.get("APPDATA", "")
            if not appdata:
                return False, "APPDATA environment variable not found."
            startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            startup_dir.mkdir(parents=True, exist_ok=True)
            vbs_file = startup_dir / "TimeTrackerStartup.vbs"
            vbs_content = (
                'Set WshShell = CreateObject("WScript.Shell")\r\n'
                'WshShell.Run "pythonw -m timetracker.daemon", 0, False\r\n'
            )
            vbs_file.write_text(vbs_content, encoding="utf-8")
            return True, f"Created Windows startup launcher: {vbs_file}"
        except Exception as e:
            return False, f"Failed to enable Windows autostart: {e}"

    # Linux implementation
    script_path = get_startup_script_dir() / "enable_linux.sh"
    if script_path.is_file() and os.access(script_path, os.X_OK):
        try:
            res = subprocess.run([str(script_path)], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return True, "Enabled startup via systemd and XDG autostart."
        except Exception:
            pass

    # Native Python fallback for Linux
    try:
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)
        desktop_file = autostart_dir / "timetracker.desktop"

        bin_path = shutil.which("timetracker") or f"{Path.home()}/.local/bin/timetracker"

        content = f"""[Desktop Entry]
Type=Application
Version=1.0
Name=TimeTracker Daemon
Comment=Ambient developer time tracker for IDEs and browser research
Exec={bin_path} daemon -q
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
Categories=Development;Utility;
"""
        desktop_file.write_text(content, encoding="utf-8")
        desktop_file.chmod(0o644)
        return True, f"Created XDG desktop autostart entry: {desktop_file}"
    except Exception as e:
        return False, f"Failed to enable Linux autostart: {e}"


def disable_autostart() -> Tuple[bool, str]:
    """Disable automatic startup."""
    if sys.platform == "win32":
        script_path = get_startup_script_dir() / "disable_windows.bat"
        if script_path.is_file():
            try:
                res = subprocess.run([str(script_path)], capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    return True, "Disabled autostart in Windows Startup folder."
            except Exception:
                pass

        # Native fallback
        try:
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
                for fname in ["TimeTrackerStartup.vbs", "TimeTrackerStartup.bat"]:
                    fpath = startup_dir / fname
                    if fpath.is_file():
                        fpath.unlink()
            return True, "Removed Windows startup launchers."
        except Exception as e:
            return False, f"Failed to disable Windows autostart: {e}"

    # Linux implementation
    script_path = get_startup_script_dir() / "disable_linux.sh"
    if script_path.is_file() and os.access(script_path, os.X_OK):
        try:
            res = subprocess.run([str(script_path)], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return True, "Disabled autostart and stopped service on Linux."
        except Exception:
            pass

    # Native Python fallback for Linux
    try:
        desktop_file = Path.home() / ".config" / "autostart" / "timetracker.desktop"
        if desktop_file.is_file():
            desktop_file.unlink()

        if shutil.which("systemctl"):
            subprocess.run(["systemctl", "--user", "stop", "timetracker.service"], check=False)
            subprocess.run(["systemctl", "--user", "disable", "timetracker.service"], check=False)
            service_file = Path.home() / ".config" / "systemd" / "user" / "timetracker.service"
            if service_file.is_file():
                service_file.unlink()

        return True, "Removed autostart entries and stopped service."
    except Exception as e:
        return False, f"Failed to disable Linux autostart: {e}"
