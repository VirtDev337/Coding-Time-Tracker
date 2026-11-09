"""
Window & Process Tracker.
Detects the active foreground window, classifies the application (IDE, Browser, Terminal),
extracts the project name/active file, and handles idle detection.
"""

from __future__ import annotations
import ctypes
import ctypes.util
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
    project_dir: str = ""  # Resolved filesystem directory for the active project


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

        # Parse title — xprop already outputs a decoded UTF-8 string; use it directly.
        # Only unescape backslash-escaped quotes that xprop wraps around the value.
        title_match = re.search(r'_NET_WM_NAME\(UTF8_STRING\) = "(.*?)(?<!\\)"', prop_out)
        if not title_match:
            title_match = re.search(r'WM_NAME\([A-Z0-9_]+\) = "(.*?)(?<!\\)"', prop_out)
        title = title_match.group(1).replace('\\"', '"').replace("\\\\", "\\") if title_match else ""

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


def _get_x11_idle_via_xss() -> Optional[float]:
    """
    Query X11 idle time in seconds via libXss (XScreenSaver extension).
    Returns idle seconds as float, or None if unavailable.
    Used as a fallback when xprintidle is not installed.
    """
    try:
        x11_path = ctypes.util.find_library("X11")
        xss_path = ctypes.util.find_library("Xss")
        if not x11_path or not xss_path:
            return None

        x11 = ctypes.cdll.LoadLibrary(x11_path)
        xss = ctypes.cdll.LoadLibrary(xss_path)

        class XScreenSaverInfo(ctypes.Structure):
            _fields_ = [
                ("window",       ctypes.c_ulong),
                ("state",        ctypes.c_int),
                ("kind",         ctypes.c_int),
                ("til_or_since", ctypes.c_ulong),
                ("idle",         ctypes.c_ulong),
            ]

        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x11.XDefaultRootWindow.restype = ctypes.c_ulong
        x11.XFree.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]

        xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(XScreenSaverInfo)
        xss.XScreenSaverQueryInfo.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(XScreenSaverInfo)
        ]
        xss.XScreenSaverQueryInfo.restype = ctypes.c_int

        display = x11.XOpenDisplay(None)
        if not display:
            return None
        try:
            root = x11.XDefaultRootWindow(display)
            info = xss.XScreenSaverAllocInfo()
            if not info:
                return None
            try:
                if xss.XScreenSaverQueryInfo(display, root, info):
                    return float(info.contents.idle) / 1000.0
            finally:
                x11.XFree(info)
        finally:
            x11.XCloseDisplay(display)
    except Exception:
        pass
    return None


def get_idle_seconds() -> float:
    """
    Detect user idle time in seconds across Windows and Linux.
    On Linux tries xprintidle first, then the native libXss ctypes fallback.
    Returns 0.0 when no idle information is available (tracking continues).
    """
    if sys.platform == "win32":
        return get_windows_idle_seconds()

    if os.environ.get("DISPLAY"):
        # Preferred: xprintidle (smallest dependency, most accurate)
        if shutil.which("xprintidle"):
            try:
                ms_str = subprocess.check_output(
                    ["xprintidle"], stderr=subprocess.DEVNULL, timeout=1.0
                ).decode().strip()
                return float(ms_str) / 1000.0
            except Exception:
                pass

        # Fallback: native libXss via ctypes (no extra binary needed)
        result = _get_x11_idle_via_xss()
        if result is not None:
            return result

    return 0.0


# IDE editor suffix patterns used in title stripping.
# en-dash (U+2013) and em-dash (U+2014) are both included as separators.
_IDE_SUFFIX_RE = re.compile(
    r'[\s\-\u2013\u2014]+(Visual Studio Code|VSCodium|Code - OSS|Code|'
    r'Cursor|Windsurf|Zed|RStudio|'
    r'PyCharm(?:\s+\w+)*|IntelliJ IDEA(?:\s+\w+)*|CLion|GoLand|WebStorm|Rider|'
    r'Sublime Text\s*\d*|Atom|Notepad\+\+)$',
    flags=re.IGNORECASE
)

# Separator for project/file splitting inside IDE titles.
# Matches ASCII hyphen, en-dash (U+2013), and em-dash (U+2014).
_IDE_SPLIT_RE = re.compile(r'\s+[-\u2013\u2014]\s+')

# Browser suffix patterns.
_BROWSER_SUFFIX_RE = re.compile(
    r'[\s\-\u2013\u2014]+(Google Chrome|Mozilla Firefox|Firefox Developer Edition|'
    r'Firefox Nightly|Firefox|Brave|Chromium|Microsoft Edge|Opera|Vivaldi|Safari)$',
    flags=re.IGNORECASE
)

# AI web services whose browser tabs count as collaboration, not generic research.
_AI_BROWSER_DOMAINS = frozenset(["antigravity", "gemini", "chatgpt", "claude"])


class WindowTracker:
    def __init__(self, config: TrackerConfig):
        self.config = config

    def parse_ide_title(self, title: str, app_name: str) -> Tuple[str, str]:
        """
        Extract (project_name, file_name) from IDE title.
        Supports VSCode, VSCodium, RStudio, PyCharm/JetBrains, Cursor, Windsurf,
        Zed, Sublime Text, Atom, and similar editors.
        """
        # Remove editor name suffix (handles hyphen, en-dash, and em-dash separators)
        clean = _IDE_SUFFIX_RE.sub("", title).strip()

        # Remove dirty file indicators (e.g. '● ', '* ')
        clean = clean.lstrip("●* ")

        # Special handling for RStudio
        if "rstudio" in app_name.lower():
            clean = re.sub(r'^RStudio\s*-\s*', '', clean)
            return clean or "RStudio Project", ""

        # Standard VSCode/JetBrains format: 'file_name – project_name' or just 'project_name'
        # Uses _IDE_SPLIT_RE which covers ASCII hyphen, en-dash, and em-dash.
        parts = [p.strip() for p in _IDE_SPLIT_RE.split(clean) if p.strip()]
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
        # Clean browser name suffix (handles Firefox Developer Edition etc.)
        clean = _BROWSER_SUFFIX_RE.sub("", title).strip()

        lower_clean = clean.lower()
        parts = [p.strip() for p in re.split(r'\s*[-\u2013\u2014|·]\s*|\s*:\s+', clean) if p.strip()]
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

    def _resolve_project_dir(self, pid: Optional[int], project_name: str) -> str:
        """
        Try to resolve the filesystem directory for the active project.
        Uses the PID's working directory when available and meaningful.
        """
        if pid:
            try:
                proc = psutil.Process(pid)
                cwd = proc.cwd()
                home = os.path.expanduser("~")
                if cwd and cwd != home and cwd != "/" and os.path.isdir(cwd):
                    return cwd
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return ""

    def get_active_window(self) -> Optional[WindowInfo]:
        """
        Get info about the currently active window.
        Works across Linux (X11) and Windows (Win32), falling back to process scan.

        Classification priority:
          1. IDE (project name extraction takes precedence)
          2. Known AI tool application (by WM_CLASS / process name)
          3. Browser (content classified as research / distraction / AI-collab / other)
          4. Terminal
        """
        win_info = get_windows_active_window() if sys.platform == "win32" else get_x11_active_window()
        if win_info:
            title, wm_class, pid = win_info
            app_lower = wm_class.lower()

            # --- Classification flags ---
            is_ide = any(ide in app_lower for ide in self.config.supported_ides)
            is_browser = any(br in app_lower for br in self.config.supported_browsers)
            is_terminal = any(
                term in app_lower
                for term in ["terminal", "alacritty", "kitty", "konsole", "terminator", "gnome-terminal"]
            )
            # AI collab: only flag when the *application itself* is an AI tool,
            # NOT when "antigravity" merely appears somewhere in a browser page title.
            is_ai_collab = any(ai in app_lower for ai in self.config.supported_ai_tools)

            project_name = ""
            file_name = ""
            research_topic = ""
            research_domain = ""
            category = "other"
            project_dir = ""

            if is_ide:
                # IDEs take top priority — extract project/file from title
                category = "coding"
                project_name, file_name = self.parse_ide_title(title, app_lower)
                project_dir = self._resolve_project_dir(pid, project_name)

            elif is_ai_collab:
                # Dedicated AI tool application (Antigravity, Cursor AI pane, etc.)
                category = "collaboration"
                research_topic = "Antigravity AI Assistance"
                research_domain = "Antigravity"
                # Pull project context from the title if the AI window embeds it
                if " - " in title or " \u2013 " in title or " \u2014 " in title:
                    project_name, file_name = self.parse_ide_title(title, app_lower)

            elif is_browser:
                research_domain, research_topic, browser_cat = self.parse_browser_title(title)
                # Upgrade browser tab to collaboration only when the page itself
                # is an authorised AI web service (ChatGPT, Claude, Gemini web UI, etc.)
                if any(ai_site in research_domain.lower() for ai_site in _AI_BROWSER_DOMAINS):
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
                category=category,
                project_dir=project_dir,
            )

        # Fallback to psutil process scan
        return self._fallback_psutil_scan()

    def _fallback_psutil_scan(self) -> Optional[WindowInfo]:
        """Fallback when no X11 active window is found (e.g. Wayland/headless)."""
        for p in psutil.process_iter(attrs=["pid", "name"]):
            try:
                name = p.info["name"].lower()
                is_ide = any(ide in name for ide in self.config.supported_ides)
                if is_ide:
                    try:
                        cwd = p.cwd()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        cwd = ""
                    home = os.path.expanduser("~")
                    proj_name = (
                        os.path.basename(cwd)
                        if cwd and cwd != home and cwd != "/"
                        else "Active IDE"
                    )
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
                        category="coding",
                        project_dir=cwd or "",
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
