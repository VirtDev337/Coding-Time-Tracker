"""
TimeTracker Command Line Interface.
Provides subcommands to monitor, view statistics, manage projects,
and generate customizable PDF reports.
"""

from __future__ import annotations
import argparse
import os
import subprocess
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

from timetracker.config import load_config, save_config, ReportConfig
from timetracker.db import Database, format_duration
from timetracker.window_tracker import WindowTracker
from timetracker.daemon import TimeTrackerDaemon
from timetracker.reports.pdf_report import PDFReportGenerator


# ANSI terminal colors
BOLD = "\033[1m"
GREEN = "\033[32m"
BLUE = "\033[34m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
YELLOW = "\033[33m"
DIM = "\033[2m"
RESET = "\033[0m"


def cmd_status(args, config, db):
    """Show current tracking status and today's summary."""
    wt = WindowTracker(config)
    win = wt.get_active_window()

    print(f"\n{BOLD}{BLUE}=== TimeTracker Status ==={RESET} {DIM}(VirtDev x Antigravity){RESET}")
    if win:
        if win.category == "collaboration":
            cat_color = MAGENTA
            cat_label = "AI COLLABORATION (Antigravity)"
        elif win.category == "coding":
            cat_color = GREEN
            cat_label = "CODING"
        elif win.category == "research":
            cat_color = CYAN
            cat_label = "RESEARCH"
        else:
            cat_color = YELLOW
            cat_label = win.category.upper()

        print(f"  {BOLD}Active Window:{RESET}  {win.window_title[:60]}")
        print(f"  {BOLD}Application:{RESET}    {win.app_name}")
        print(f"  {BOLD}Category:{RESET}       {cat_color}{cat_label}{RESET}")
        if win.project_name:
            print(f"  {BOLD}Active Project:{RESET} {win.project_name}")
    else:
        print(f"  {DIM}No active IDE or development browser detected.{RESET}")

    stats = db.get_today_stats()
    print(f"\n{BOLD}=== Today's Summary ==={RESET}")
    print(f"  {BOLD}Total Time:{RESET}      {format_duration(stats['total_seconds'])}")
    print(f"  {BOLD}Coding Time:{RESET}     {format_duration(stats['coding_seconds'])}")
    print(f"  {BOLD}AI Collaboration:{RESET} {MAGENTA}{format_duration(stats.get('collaboration_seconds', 0))}{RESET}")
    print(f"  {BOLD}Research Time:{RESET}   {format_duration(stats['research_seconds'])}")
    print(f"  {BOLD}Projects Active:{RESET} {stats['project_count']}\n")


def cmd_projects(args, config, db):
    """List all tracked projects and durations."""
    projects = db.get_all_projects()
    print(f"\n{BOLD}{BLUE}=== Tracked Projects ({len(projects)}) ==={RESET}\n")
    if not projects:
        print(f"  {DIM}No projects recorded yet. Run 'timetracker daemon' to start tracking.{RESET}\n")
        return

    header = f"  {'Project Name':<26} {'Coding':<11} {'AI Collab':<12} {'Research':<11} {'Total':<11} {'Last Active'}"
    print(BOLD + header + RESET)
    print("  " + "-" * 88)

    for p in projects:
        c_fmt = format_duration(p["coding_seconds"])
        ai_fmt = format_duration(p.get("collaboration_seconds", 0))
        r_fmt = format_duration(p["research_seconds"])
        t_fmt = format_duration(p["total_seconds"])
        last_dt = str(p["last_active_at"])[:16] if p["last_active_at"] else "N/A"
        print(f"  {p['name']:<26} {c_fmt:<11} {ai_fmt:<12} {r_fmt:<11} {BOLD}{t_fmt:<11}{RESET} {DIM}{last_dt}{RESET}")
    print()


def cmd_delete(args, config, db):
    """Delete a project and its history."""
    proj = args.project
    confirm = input(f"Are you sure you want to delete project '{proj}' and all its tracked history? (y/N): ")
    if confirm.lower() == 'y':
        db.delete_project(proj)
        print(f"{GREEN}Project '{proj}' deleted successfully.{RESET}")
    else:
        print("Cancelled.")


def cmd_daemon(args, config, db):
    """Run tracking daemon."""
    daemon = TimeTrackerDaemon(config)
    daemon.start(verbose=not args.quiet)


def cmd_report(args, config, db):
    """Generate a customizable PDF activity report."""
    # Build report config overrides
    rep_cfg = config.report
    if args.theme:
        rep_cfg.accent_color = args.theme
    if args.rate is not None:
        rep_cfg.hourly_rate = float(args.rate)
    if args.dev_name:
        rep_cfg.developer_name = args.dev_name
    if args.logo:
        rep_cfg.logo_path = args.logo
    if args.detailed:
        rep_cfg.include_details = True
    elif args.summary:
        rep_cfg.include_details = False

    # Date range parsing
    start_date = args.start_date
    end_date = args.end_date

    if args.today:
        start_date = date.today().isoformat()
        end_date = start_date
    elif args.week:
        start_date = (date.today() - timedelta(days=7)).isoformat()
        end_date = date.today().isoformat()
    elif args.month:
        start_date = (date.today() - timedelta(days=30)).isoformat()
        end_date = date.today().isoformat()

    data = db.get_report_data(
        project_name=args.project,
        start_date=start_date,
        end_date=end_date
    )

    output = args.output
    if not output:
        proj_slug = args.project.replace(" ", "_") if args.project else "all_projects"
        date_slug = f"{start_date or 'earliest'}_to_{end_date or 'latest'}"
        output = f"TimeTracker_{proj_slug}_{date_slug}.pdf"

    output_path = os.path.abspath(output)
    generator = PDFReportGenerator(output_path, rep_cfg)
    pdf_file = generator.generate(data)

    print(f"\n{BOLD}{GREEN}✓ PDF Report Generated Successfully!{RESET}")
    print(f"  {BOLD}File:{RESET}        {pdf_file}")
    print(f"  {BOLD}Total Hours:{RESET} {data['total_formatted']}")
    print(f"  {BOLD}Coding:{RESET}      {data['coding_formatted']}")
    print(f"  {BOLD}Research:{RESET}    {data['research_formatted']}")
    print(f"  {BOLD}Projects:{RESET}    {len(data['projects'])}\n")

    if args.open:
        try:
            if sys.platform == "win32":
                os.startfile(pdf_file)
            elif sys.platform == "darwin":
                subprocess.run(["open", pdf_file], check=False)
            else:
                subprocess.run(["xdg-open", pdf_file], check=False)
        except Exception:
            pass


def cmd_autostart(args, config, db):
    """Enable, disable, or check startup status."""
    from timetracker.autostart import is_autostart_enabled, enable_autostart, disable_autostart

    action = getattr(args, "action", "status") or "status"

    if action in ("enable", "on", "install"):
        success, msg = enable_autostart()
        if success:
            print(f"\n{BOLD}{GREEN}✓ TimeTracker startup enabled.{RESET}")
            print(f"  {msg}\n")
        else:
            print(f"\n{BOLD}\033[31m✗ Failed to enable startup:{RESET} {msg}\n")
    elif action in ("disable", "off", "uninstall"):
        success, msg = disable_autostart()
        if success:
            print(f"\n{BOLD}{GREEN}✓ TimeTracker startup disabled.{RESET}")
            print(f"  {msg}\n")
        else:
            print(f"\n{BOLD}\033[31m✗ Failed to disable startup:{RESET} {msg}\n")
    else:
        # Check current status
        enabled = is_autostart_enabled()
        status_str = f"{BOLD}{GREEN}ENABLED{RESET} (starts automatically in background on login)" if enabled else f"{BOLD}{YELLOW}DISABLED{RESET}"
        print(f"\n{BOLD}{BLUE}=== TimeTracker Autostart Status ==={RESET}")
        print(f"  Status:    {status_str}")
        print(f"  Platform:  {sys.platform}")
        print(f"\n  {BOLD}Commands:{RESET}")
        print(f"    Enable:  {BOLD}timetracker autostart enable{RESET}")
        print(f"    Disable: {BOLD}timetracker autostart disable{RESET}\n")


def cmd_config(args, config, db):
    """View configuration path and values."""
    print(f"\n{BOLD}{BLUE}=== TimeTracker Configuration ==={RESET}")
    print(f"  {BOLD}Database:{RESET}       {config.db_path}")
    print(f"  {BOLD}Poll Interval:{RESET}  {config.poll_interval_seconds}s")
    print(f"  {BOLD}Idle Threshold:{RESET} {config.idle_threshold_seconds}s")
    print(f"  {BOLD}Developer:{RESET}      {config.report.developer_name}")
    print(f"  {BOLD}Hourly Rate:{RESET}    ${config.report.hourly_rate:.2f}/hr")
    print(f"  {BOLD}Accent Color:{RESET}   {config.report.accent_color}")
    print(f"  {BOLD}Config File:{RESET}    ~/.codetime/config.json\n")


def cmd_gui(args, config, db):
    """Launch GTK3 graphical interface."""
    from timetracker.gui import main as gui_main
    gui_main()


def main():
    config = load_config()
    db = Database(config.db_path)

    parser = argparse.ArgumentParser(
        prog="timetracker",
        description="TimeTracker v2: Ambient coding & research tracker with customizable PDF reports."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # status
    p_status = subparsers.add_parser("status", help="Show current tracking status and today's summary")
    p_status.set_defaults(func=cmd_status)

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Run the background tracker daemon")
    p_daemon.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (no verbose tick output)")
    p_daemon.set_defaults(func=cmd_daemon)

    # projects
    p_projects = subparsers.add_parser("projects", help="List all tracked projects and times")
    p_projects.set_defaults(func=cmd_projects)

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a project from the database")
    p_delete.add_argument("project", type=str, help="Name of project to delete")
    p_delete.set_defaults(func=cmd_delete)

    # report
    p_report = subparsers.add_parser("report", help="Generate a customizable PDF report")
    p_report.add_argument("-p", "--project", type=str, help="Filter by project name")
    p_report.add_argument("-s", "--start-date", type=str, help="Start date (YYYY-MM-DD)")
    p_report.add_argument("-e", "--end-date", type=str, help="End date (YYYY-MM-DD)")
    p_report.add_argument("--today", action="store_true", help="Report for today only")
    p_report.add_argument("--week", action="store_true", help="Report for the last 7 days")
    p_report.add_argument("--month", action="store_true", help="Report for the last 30 days")
    p_report.add_argument("-o", "--output", type=str, help="Output PDF filename/path")
    p_report.add_argument("--theme", type=str, help="Hex color code for PDF accent (e.g. #059669)")
    p_report.add_argument("--rate", type=float, help="Hourly billing rate")
    p_report.add_argument("--dev-name", type=str, help="Developer name on report")
    p_report.add_argument("--logo", type=str, help="Path to logo image")
    p_report.add_argument("--detailed", action="store_true", help="Include full file & research lists")
    p_report.add_argument("--summary", action="store_true", help="Summary only (no drill-down tables)")
    p_report.add_argument("--open", action="store_true", help="Open PDF after generation")
    p_report.set_defaults(func=cmd_report)

    # config
    p_config = subparsers.add_parser("config", help="View configuration")
    p_config.set_defaults(func=cmd_config)

    # autostart
    p_autostart = subparsers.add_parser("autostart", help="Manage automatic startup at login (enable/disable/status)")
    p_autostart.add_argument(
        "action",
        nargs="?",
        default="status",
        choices=["status", "enable", "disable", "on", "off", "install", "uninstall"],
        help="Action to perform (default: status)"
    )
    p_autostart.set_defaults(func=cmd_autostart)

    # gui
    p_gui = subparsers.add_parser("gui", help="Launch the graphical interface")
    p_gui.set_defaults(func=cmd_gui)

    args = parser.parse_args()

    if not args.command:
        # Default to status if no command provided
        cmd_status(args, config, db)
    else:
        args.func(args, config, db)


if __name__ == "__main__":
    main()
