"""
Window & Process Tracker.
Detects the active foreground window, classifies the application (IDE, Browser, Terminal),
extracts the project name/active file, and handles idle detection.
"""

from __future__ import annotations
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional, Tuple
import psutil

from timetracker.config import TrackerConfig


@dataclass
class WindowInfo:
    app_name: str
    window_title: str
    pid: Optional[int]
    is_ide: bool
    is_browser: bool
    is_terminal: bool
    is_ai_collab: bool
    project_name: str
    file_name: str
    research_topic: str
    research_domain: str
    category: str  # 'coding', 'collaboration', 'research', 'distraction', 'terminal', 'other'


def get_x11_active_window() -> Optional[Tuple[str, str, Optional[int]]]:
    """
    Query active window on Linux X11 using xprop.
    Returns (window_title, wm_class, pid) or None.
    """
    if not os.environ.get("DISPLAY"):
        return None

    try:
        # 1. Get active window ID
        out = subprocess.check_output(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
            stderr=subprocess.DEVNULL,
            timeout=1.5
        ).decode("utf-8", errors="ignore")

        match = re.search(r"_NET_ACTIVE_WINDOW.*#\s+(0x[0-9a-fA-F]+)", out)
        if not match:
            return None
        win_id = match.group(1)
        if win_id == "0x0":
            return None

        # 2. Get window properties
        prop_out = subprocess.check_output(
            ["xprop", "-id", win_id, "_NET_WM_NAME", "WM_NAME", "WM_CLASS", "_NET_WM_PID"],
            stderr=subprocess.DEVNULL,
            timeout=1.5
        ).decode("utf-8", errors="ignore")

        # Parse title
        title_match = re.search(r'_NET_WM_NAME\(UTF8_STRING\) = "(.*?)(?<!\\)"', prop_out)
        if not title_match:
            title_match = re.search(r'WM_NAME\([A-Z0-9_]+\) = "(.*?)(?<!\\)"', prop_out)
        title = title_match.group(1).encode('utf-8').decode('unicode_escape', errors='ignore') if title_match else ""

        # Parse WM_CLASS
        class_match = re.search(r'WM_CLASS\([A-Z0-9_]+\) = "(.*?)", "(.*?)"', prop_out)
        wm_class = class_match.group(2).lower() if class_match else ""

        # Parse PID
        pid_match = re.search(r"_NET_WM_PID\([A-Z0-9_]+\) = (\d+)", prop_out)
        pid = int(pid_match.group(1)) if pid_match else None

        return title, wm_class, pid
    except Exception:
        return None


def get_windows_active_window() -> Optional[Tuple[str, str, Optional[int]]]:
    """
    Query active foreground window on Windows using user32.dll (ctypes).
    Returns (window_title, app_name, pid) or None.
    """
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return None
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        app_name = "unknown"
        if pid.value:
            try:
                proc = psutil.Process(pid.value)
                app_name = proc.name().lower().replace(".exe", "")
            except Exception:
                pass

        return title, app_name, pid.value if pid.value else None
    except Exception:
        return None


def get_windows_idle_seconds() -> float:
    """
    Query user idle time on Windows using GetLastInputInfo.
    """
    try:
        import ctypes
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return 0.0


def get_idle_seconds() -> float:
    """
    Detect user idle time in seconds across Windows and Linux.
    """
    if sys.platform == "win32":
        return get_windows_idle_seconds()

    if shutil.which("xprintidle") and os.environ.get("DISPLAY"):
        try:
            ms_str = subprocess.check_output(["xprintidle"], stderr=subprocess.DEVNULL, timeout=1.0).decode().strip()
            return float(ms_str) / 1000.0
        except Exception:
            pass
    return 0.0


class WindowTracker:
    def __init__(self, config: TrackerConfig):
        self.config = config

    def parse_ide_title(self, title: str, app_name: str) -> Tuple[str, str]:
        """
        Extract (project_name, file_name) from IDE title.
        Supports VSCode, VSCodium, RStudio, PyCharm, Cursor, Windsurf, Zed, etc.
        """
        # Remove editor name suffix
        clean = re.sub(
            r'[\s\-—]+(Visual Studio Code|VSCodium|Code|Cursor|Windsurf|Zed|RStudio|PyCharm.*)$',
            '',
            title,
            flags=re.IGNORECASE
        ).strip()

        # Remove dirty file indicators (e.g. '● ', '* ')
        clean = clean.lstrip('●* ')

        # Special handling for RStudio
        if "rstudio" in app_name.lower():
            clean = re.sub(r'^RStudio\s*-\s*', '', clean)
            return clean or "RStudio Project", ""

        # VSCode / Codium standard format: 'file_name - project_name' or just 'project_name'
        parts = [p.strip() for p in re.split(r'\s+[-—]\s+', clean) if p.strip()]
        if len(parts) >= 2:
            return parts[-1], parts[0]
        elif len(parts) == 1:
            return parts[0], ""
        return "Unknown Project", ""

    def parse_browser_title(self, title: str) -> Tuple[str, str, str]:
        """
        Extract (research_domain, research_topic, category) from browser title.
        Categories: 'research', 'distraction', 'other'
        """
        # Clean browser name suffix
        clean = re.sub(
            r'[\s\-—]+(Google Chrome|Mozilla Firefox|Brave|Chromium|Microsoft Edge|Opera|Vivaldi)$',
            '',
            title,
            flags=re.IGNORECASE
        ).strip()

        lower_clean = clean.lower()
        parts = [p.strip() for p in re.split(r'\s*[-—|·]\s*|\s*:\s+', clean) if p.strip()]
        site_candidate = parts[-1] if len(parts) > 1 else clean

        # Check for distraction domains or brand names first
        for dist in self.config.distraction_domains:
            if dist in lower_clean:
                return site_candidate, clean, "distraction"
            base_name = dist.replace(".com", "").replace(".org", "")
            if len(base_name) > 2 and re.search(r'\b' + re.escape(base_name) + r'\b', lower_clean):
                return site_candidate, clean, "distraction"

        # Check for dev research domains or brand names
        for res in self.config.research_domains:
            if res in lower_clean:
                return site_candidate, clean, "research"
            base_name = res.replace(".com", "").replace(".org", "").replace(".ai", "").replace("docs.", "")
            if len(base_name) > 2 and re.search(r'\b' + re.escape(base_name) + r'\b', lower_clean):
                return site_candidate, clean, "research"

        # Check common dev keywords in title
        dev_keywords = [
            "python", "javascript", "typescript", "rust", "golang", "c++", "linux",
            "bash", "docker", "api", "git", "github", "gitlab", "stackoverflow",
            "documentation", "doc", "tutorial", "guide", "error", "exception",
            "traceback", "debug", "reportlab", "pandas", "numpy", "fastapi", "flask",
            "django", "react", "vue", "angular", "css", "html", "sql", "sqlite"
        ]
        for kw in dev_keywords:
            pattern = r'(?:^|\W)' + re.escape(kw) + r'(?:$|\W)'
            if re.search(pattern, lower_clean):
                domain = site_candidate if len(parts) > 1 else kw.title()
                return domain, clean, "research"

        domain = site_candidate if len(parts) > 1 else "Web Browser"
        return domain, clean, "other"

    def get_active_window(self) -> Optional[WindowInfo]:
        """
        Get info about the currently active window.
        Works across Linux (X11) and Windows (Win32), falling back to process scan.
        """
        win_info = get_windows_active_window() if sys.platform == "win32" else get_x11_active_window()
        if win_info:
            title, wm_class, pid = win_info
            app_lower = wm_class.lower()

            # Check if IDE
            is_ide = any(ide in app_lower for ide in self.config.supported_ides)
            # Check if Browser
            is_browser = any(br in app_lower for br in self.config.supported_browsers)
            # Check if Terminal
            is_terminal = any(term in app_lower for term in ["terminal", "alacritty", "kitty", "konsole", "terminator"])
            # Check if Antigravity / AI Collaboration
            is_ai_collab = (
                any(ai in app_lower for ai in self.config.supported_ai_tools)
                or any(ai in title.lower() for ai in ["antigravity", "agy", "gemini cli", "pair programming"])
            )

            project_name = ""
            file_name = ""
            research_topic = ""
            research_domain = ""
            category = "other"

            if is_ai_collab:
                category = "collaboration"
                research_topic = "Antigravity AI Assistance"
                research_domain = "Antigravity"
                # If Antigravity window title has project/file info, extract it
                if " - " in title:
                    project_name, file_name = self.parse_ide_title(title, app_lower)
            elif is_ide:
                category = "coding"
                project_name, file_name = self.parse_ide_title(title, app_lower)
            elif is_browser:
                research_domain, research_topic, browser_cat = self.parse_browser_title(title)
                # Check if browsing an AI assistant interface (ChatGPT, Claude, Gemini, Antigravity)
                if any(ai_site in research_domain.lower() for ai_site in ["antigravity", "gemini", "chatgpt", "claude"]):
                    category = "collaboration"
                    is_ai_collab = True
                else:
                    category = browser_cat
            elif is_terminal:
                category = "terminal"

            return WindowInfo(
                app_name=wm_class or "unknown",
                window_title=title,
                pid=pid,
                is_ide=is_ide,
                is_browser=is_browser,
                is_terminal=is_terminal,
                is_ai_collab=is_ai_collab,
                project_name=project_name,
                file_name=file_name,
                research_topic=research_topic,
                research_domain=research_domain,
                category=category
            )

        # Fallback to psutil process scan
        return self._fallback_psutil_scan()

    def _fallback_psutil_scan(self) -> Optional[WindowInfo]:
        """Fallback when no X11 active window is found (e.g. CLI/server/headless)."""
        for p in psutil.process_iter(attrs=["pid", "name"]):
            try:
                name = p.info["name"].lower()
                is_ide = any(ide in name for ide in self.config.supported_ides)
                if is_ide:
                    cwd = p.cwd() if hasattr(p, 'cwd') else ""
                    proj_name = os.path.basename(cwd) if cwd and cwd != os.path.expanduser("~") else "Active IDE"
                    return WindowInfo(
                        app_name=name,
                        window_title=f"{proj_name} (Process)",
                        pid=p.info["pid"],
                        is_ide=True,
                        is_browser=False,
                        is_terminal=False,
                        is_ai_collab=False,
                        project_name=proj_name,
                        file_name="",
                        research_topic="",
                        research_domain="",
                        category="coding"
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
