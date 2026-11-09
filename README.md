# TimeTracker v2

**TimeTracker v2** is an ambient developer time-tracking system designed for coders. It automatically logs time spent coding in IDEs as well as research conducted in web browsers without requiring manual timer clicks.

---

## Key Features

1. **Ambient, Zero-Intervention Tracking**:
   * Uses Linux X11 active foreground window inspection (`xprop`) to detect when your IDE or browser actually has focus.
   * Extracts workspace and project names automatically from window titles (VSCode, VSCodium, RStudio, PyCharm, Cursor, Windsurf, Zed).
2. **Intelligent Browser Research Linking**:
   * Inspects browser window titles for technical documentation, dev sites, and search queries (Stack Overflow, GitHub, MDN, Python Docs, PyPI, etc.).
   * Automatically attributes browser research to the project you were just working on.
   * Filters out non-development distraction sites (YouTube, social media).
3. **Idle Detection**:
   * Pauses tracking automatically when you walk away or stop typing/moving the mouse, preventing false 24/7 logging.
4. **Crash-Resilient SQLite Database**:
   * Stores time slices in WAL-mode SQLite (`~/.codetime/timetracker.db`).
   * Never loses data on unexpected shutdowns or IDE crashes.
5. **Scoped File Modification Watching**:
   * Uses `watchdog` strictly scoped to active project directories with intelligent ignore filters (`.git`, `node_modules`, `venv`, `__pycache__`), avoiding system `inotify` watcher exhaustion.
6. **Customizable Executive PDF Reports**:
   * Built with **ReportLab Platypus** for clean document typography.
   * Executive KPI metric cards (Total Time, Coding Time, Research Time, Estimated Billable Value).
   * Project breakdown tables, daily activity timelines, and drill-down tables for modified files and research domains.
   * Fully customizable: hourly billing rate, accent colors, logo, and detail toggles.
7. **Dual Interfaces**:
   * Rich CLI with ANSI terminal formatting.
   * GTK3 desktop interface (`timetracker-gui`).

---

## Directory Structure

```
TimeTrackerv2/
├── assets/
│   └── icon.jpg               # Application icon
├── pyproject.toml             # Modern package build configuration
├── requirements.txt           # Python dependencies
├── setup.py                   # Setup script with CLI entry points
├── sample_report.pdf          # Example generated PDF report
├── README.md
├── src/
│   └── timetracker/
│       ├── __init__.py
│       ├── config.py          # User settings manager (~/.codetime/config.json)
│       ├── db.py              # SQLite storage & aggregation queries
│       ├── window_tracker.py  # X11 active window focus & idle detection
│       ├── file_watcher.py    # Project-scoped watchdog file observer
│       ├── daemon.py          # Background tracking engine
│       ├── cli.py             # Full CLI command suite
│       ├── gui.py             # GTK3 graphical desktop application
│       └── reports/
│           ├── __init__.py
│           └── pdf_report.py  # ReportLab Platypus customizable PDF engine
└── tests/
    ├── test_db.py             # Database & query unit tests
    ├── test_window_tracker.py # Window & browser parser unit tests
    └── test_reports.py        # PDF generator unit tests
```

---

## Installation & Distribution

TimeTracker v2 provides standalone installers for Linux and Windows that automatically configure isolated environments, system PyGObject/GTK3 bindings, and desktop shortcuts.

### 1. Linux Standalone Installer (Recommended)
Automatically checks for system GTK3 & PyGObject dependencies, builds an isolated virtual environment with `--system-site-packages`, and configures CLI wrappers and application menu launchers:
```bash
./installation/install.sh
```
To uninstall at any time:
```bash
./installation/uninstall.sh
```

### 2. Debian / Ubuntu Package (`.deb`)
To build and install a native `.deb` package with dependencies declared for `apt`:
```bash
# Build the .deb package:
./package/build_deb.sh

# Install:
sudo apt install ./dist/timetrackerv2_2.0.0_all.deb
```

### 3. Windows Standalone Installer
Run the batch installer in Command Prompt:
```cmd
installation\install.bat
```
This automatically sets up Python 3 in `%LOCALAPPDATA%\TimeTracker`, configures PATH wrappers, creates a Desktop shortcut (`TimeTracker v2`), adds a Start Menu entry, and prompts for automatic background startup at login. To uninstall:
```cmd
installation\uninstall.bat
```

### 4. Developer / Editable Installation
For development directly in a cloned checkout:
```bash
pip install -e .
```

---

## Usage

### 1. View Current Status
Check which window is currently focused and review today's tracked metrics:
```bash
timetracker status
```

### 2. Automatic Startup at Login (Linux & Windows)

You can enable or disable automatic background tracking at login in three easy ways:

#### A. Via CLI:
```bash
# Check status:
timetracker autostart status

# Enable autostart:
timetracker autostart enable

# Disable autostart:
timetracker autostart disable
```

#### B. Via GUI:
Launch the desktop interface (`timetracker gui`) and simply toggle the **"Autostart at login"** switch in the bottom toolbar.

#### C. Via OS Startup Scripts (under `startup/`):
* **Linux (bash)**:
  ```bash
  # Enable:
  ./startup/enable_linux.sh
  # Disable:
  ./startup/disable_linux.sh
  ```
* **Windows (batch)**:
  ```cmd
  REM Enable (runs silently via pythonw on user login):
  startup\enable_windows.bat
  REM Disable:
  startup\disable_windows.bat
  ```

---

### 3. Run the Background Daemon Manually
Run the tracker in the foreground or in a terminal session:
```bash
timetracker daemon
```
To run quietly in the background:
```bash
nohup timetracker daemon -q > /dev/null 2>&1 &
```

---

### 4. Generate Customizable PDF Reports

#### A. Full summary for all projects:
```bash
timetracker report -o my_report.pdf
```

#### B. Filter by project and custom date range:
```bash
timetracker report -p TimeTrackerv2 -s 2026-10-01 -e 2026-10-28 -o time_tracker_october.pdf
```

#### C. Custom themes, developer name, and hourly billing:
```bash
timetracker report \
  --project TimeTrackerv2 \
  --rate 95.00 \
  --dev-name "VirtDev" \
  --theme "#059669" \
  --detailed \
  --open
```

#### Available Report Flags:
| Flag | Description |
| :--- | :--- |
| `-p, --project <NAME>` | Filter report to a specific project |
| `-s, --start-date <YYYY-MM-DD>` | Filter by starting date |
| `-e, --end-date <YYYY-MM-DD>` | Filter by ending date |
| `--today` | Quick shortcut for today's activity |
| `--week` | Quick shortcut for the last 7 days |
| `--month` | Quick shortcut for the last 30 days |
| `-o, --output <FILE.pdf>` | Custom destination path for the PDF |
| `--theme <HEX>` | Custom accent color (e.g. `#1E40AF`, `#059669`, `#7C3AED`) |
| `--rate <AMOUNT>` | Hourly rate (calculates estimated billable earnings) |
| `--dev-name <NAME>` | Developer / company name displayed on header |
| `--logo <PATH>` | Path to image logo displayed in header |
| `--summary` | Output summary KPI and project tables only |
| `--detailed` | Include modified files and research domain breakdown |
| `--open` | Automatically open the PDF in default viewer upon generation |

### 4. List All Tracked Projects
```bash
timetracker projects
```

### 5. Launch the Desktop GUI
```bash
timetracker gui
# or directly
timetracker-gui
```

---

## Configuration

Preferences are stored in `~/.codetime/config.json`. You can inspect settings anytime with:
```bash
timetracker config
```

Example `~/.codetime/config.json`:
```json
{
  "db_path": "/home/virtdev/.codetime/timetracker.db",
  "poll_interval_seconds": 5,
  "idle_threshold_seconds": 180,
  "supported_ides": [
    "code", "codium", "rstudio", "pycharm", "cursor", "windsurf", "zed"
  ],
  "supported_browsers": [
    "firefox", "chrome", "google-chrome", "brave", "chromium", "microsoft-edge"
  ],
  "report": {
    "developer_name": "VirtDev",
    "hourly_rate": 85.0,
    "currency": "USD",
    "accent_color": "#1E40AF",
    "include_details": true,
    "include_research": true,
    "include_modified_files": true,
    "logo_path": ""
  }
}
```

---

## Running the Unit Tests

Execute the test suite using Python's built-in `unittest`:
```bash
cd /mnt/vault/Development/Workspace/Code/Projects/python/TimeTrackerv2
PYTHONPATH=src:tests:. python3 -m unittest discover tests
```

---

## Authorship & Acknowledgments

* **Creator, Architect & Original Codebase**: [VirtDev](https://github.com/VirtDev337)
  * Conceived the vision of ambient, zero-interaction developer time tracking across both IDEs and browser research.
  * Designed the core domain models (projects, file modifications, research links, and PDF reports) and created the original codebase, architecture documents, and early prototypes in the initial `TimeTracker` project.
* **Pair Programming & Systems Implementation**: **Antigravity** (Google DeepMind's agentic AI coding assistant)
  * Collaborated with VirtDev on the Version 2 implementation, translating the architectural vision into cross-platform system hooks (Linux X11 & Windows Win32), crash-resilient SQLite WAL heartbeat persistence, scoped filesystem observers, and the ReportLab Platypus PDF reporting engine.
