"""
GTK3 Graphical User Interface for TimeTracker v2.
Provides live status, projects breakdown, and an interactive PDF report generator.
"""

from __future__ import annotations
import os
import sys
import subprocess
from datetime import date, timedelta
from typing import Optional


def _ensure_pygobject():
    """Ensure PyGObject is available; if not in current Python, re-exec with system python3.10."""
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, GLib
        return Gtk, GLib
    except (ImportError, ValueError):
        import shutil
        for py_candidate in ["/usr/bin/python3.10", "/usr/bin/python3", shutil.which("python3.10")]:
            if py_candidate and os.path.exists(py_candidate) and py_candidate != sys.executable:
                test_cmd = [py_candidate, "-c", "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk"]
                if subprocess.run(test_cmd, capture_output=True).returncode == 0:
                    env = os.environ.copy()
                    os.execve(py_candidate, [py_candidate, "-m", "timetracker.gui"] + sys.argv[1:], env)
        try:
            import pgi
            pgi.require_version('Gtk', '3.0')
            from pgi.repository import Gtk, GLib
            return Gtk, GLib
        except Exception as e:
            raise RuntimeError(f"PyGObject (python3-gi) is required to run the GTK3 interface: {e}")


Gtk, GLib = _ensure_pygobject()


def _make_label(text: str = "") -> Gtk.Label:
    """Helper to create left-aligned GTK3 labels cleanly."""
    lbl = Gtk.Label(label=text)
    lbl.set_xalign(0.0)
    return lbl

from timetracker.config import load_config, TrackerConfig, ReportConfig
from timetracker.db import Database, format_duration
from timetracker.window_tracker import WindowTracker
from timetracker.reports.pdf_report import PDFReportGenerator


class MainWindow(Gtk.Window):
    def __init__(self, config: Optional[TrackerConfig] = None):
        super().__init__(title="TimeTracker v2")
        self.config = config or load_config()
        self.db = Database(self.config.db_path)
        self.window_tracker = WindowTracker(self.config)

        self.set_default_size(680, 500)
        self.set_border_width(12)

        # Main vertical container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(vbox)

        # 1. Header / Status Card
        status_frame = Gtk.Frame(label="Live Tracking Status")
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        status_box.set_border_width(10)

        self.status_label = _make_label("Detecting active environment...")
        self.today_label = _make_label("Today's Total: 0m | Coding: 0m | Research: 0m")
        
        status_box.pack_start(self.status_label, False, False, 0)
        status_box.pack_start(self.today_label, False, False, 0)
        status_frame.add(status_box)
        vbox.pack_start(status_frame, False, False, 0)

        # 2. Projects List Table
        proj_frame = Gtk.Frame(label="Tracked Projects")
        proj_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        proj_box.set_border_width(8)

        # Model: [ProjectName, CodingTime, AICollabTime, ResearchTime, TotalTime, LastActive]
        self.liststore = Gtk.ListStore(str, str, str, str, str, str)
        self.treeview = Gtk.TreeView(model=self.liststore)

        cols = [
            ("Project", 0, 160),
            ("Coding Time", 1, 95),
            ("AI Collab", 2, 95),
            ("Research Time", 3, 95),
            ("Total Time", 4, 95),
            ("Last Active", 5, 130)
        ]
        for title, col_idx, width in cols:
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=col_idx)
            column.set_min_width(width)
            column.set_resizable(True)
            self.treeview.append_column(column)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(220)
        scroll.add(self.treeview)
        proj_box.pack_start(scroll, True, True, 0)
        proj_frame.add(proj_box)
        vbox.pack_start(proj_frame, True, True, 0)

        # 3. Actions Toolbar
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        btn_report = Gtk.Button(label="Generate PDF Report...")
        btn_report.connect("clicked", self.on_report_clicked)
        actions_box.pack_start(btn_report, False, False, 0)

        btn_refresh = Gtk.Button(label="Refresh")
        btn_refresh.connect("clicked", lambda w: self.refresh_data())
        actions_box.pack_start(btn_refresh, False, False, 0)

        # Autostart toggle switch
        from timetracker.autostart import is_autostart_enabled
        autostart_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        autostart_lbl = Gtk.Label(label="Autostart at login:")
        self.autostart_switch = Gtk.Switch()
        self.autostart_switch.set_active(is_autostart_enabled())
        self.autostart_switch.connect("state-set", self.on_autostart_toggled)
        autostart_box.pack_start(autostart_lbl, False, False, 0)
        autostart_box.pack_start(self.autostart_switch, False, False, 0)
        actions_box.pack_start(autostart_box, False, False, 12)

        btn_quit = Gtk.Button(label="Quit")
        btn_quit.connect("clicked", Gtk.main_quit)
        actions_box.pack_end(btn_quit, False, False, 0)

        vbox.pack_start(actions_box, False, False, 0)

        # Initial load and setup timer
        self.refresh_data()
        GLib.timeout_add_seconds(3, self.on_timer_tick)

    def refresh_data(self):
        """Reload project stats and update table."""
        self.liststore.clear()
        projects = self.db.get_all_projects()
        for p in projects:
            self.liststore.append([
                p["name"],
                format_duration(p["coding_seconds"]),
                format_duration(p.get("collaboration_seconds", 0)),
                format_duration(p["research_seconds"]),
                format_duration(p["total_seconds"]),
                str(p["last_active_at"])[:16] if p["last_active_at"] else "N/A"
            ])

        stats = self.db.get_today_stats()
        self.today_label.set_text(
            f"Today's Total: {format_duration(stats['total_seconds'])} | "
            f"Coding: {format_duration(stats['coding_seconds'])} | "
            f"AI Collab: {format_duration(stats.get('collaboration_seconds', 0))} | "
            f"Research: {format_duration(stats['research_seconds'])}"
        )

    def on_timer_tick(self):
        """Poll active window status every few seconds."""
        win = self.window_tracker.get_active_window()
        if win and (win.is_ide or win.is_browser or win.is_ai_collab):
            if win.is_ai_collab:
                app_type = "AI Collab (Antigravity)"
            elif win.is_ide:
                app_type = "Coding"
            else:
                app_type = "Research"
            proj_str = f" | Project: {win.project_name}" if win.project_name else ""
            self.status_label.set_text(f"Active: [{app_type}] {win.window_title[:50]}{proj_str}")
        else:
            self.status_label.set_text("Active: Other / Idle (Tracking pauses when idle)")
        return True  # Keep timeout running

    def on_autostart_toggled(self, switch, state):
        """Handle toggling the autostart switch."""
        from timetracker.autostart import enable_autostart, disable_autostart
        if state:
            enable_autostart()
        else:
            disable_autostart()
        return False

    def on_report_clicked(self, widget):
        dialog = ReportDialog(self, self.db, self.config)
        dialog.run()
        dialog.destroy()


class ReportDialog(Gtk.Dialog):
    def __init__(self, parent, db: Database, config: TrackerConfig):
        super().__init__(title="Customizable PDF Report Generator", transient_for=parent, flags=0)
        self.db = db
        self.config = config
        self.set_default_size(480, 420)
        self.set_border_width(12)

        content = self.get_content_area()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.add(vbox)

        # 1. Project Selection
        vbox.pack_start(_make_label("Select Project:"), False, False, 0)
        self.project_combo = Gtk.ComboBoxText()
        self.project_combo.append_text("All Projects")
        self.project_combo.set_active(0)

        projects = self.db.get_all_projects()
        for p in projects:
            self.project_combo.append_text(p["name"])
        vbox.pack_start(self.project_combo, False, False, 0)

        # 2. Date Range
        vbox.pack_start(_make_label("Date Range:"), False, False, 0)
        self.rb_all = Gtk.RadioButton.new_with_label_from_widget(None, "All Time")
        self.rb_today = Gtk.RadioButton.new_with_label_from_widget(self.rb_all, "Today")
        self.rb_week = Gtk.RadioButton.new_with_label_from_widget(self.rb_all, "Last 7 Days")
        self.rb_month = Gtk.RadioButton.new_with_label_from_widget(self.rb_all, "Last 30 Days")
        self.rb_month.set_active(True)

        date_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        date_box.pack_start(self.rb_today, False, False, 0)
        date_box.pack_start(self.rb_week, False, False, 0)
        date_box.pack_start(self.rb_month, False, False, 0)
        date_box.pack_start(self.rb_all, False, False, 0)
        vbox.pack_start(date_box, False, False, 0)

        # 3. Customization Options
        vbox.pack_start(_make_label("Report Customization:"), False, False, 0)
        self.cb_details = Gtk.CheckButton(label="Include Detailed Modified Files & Research Tables")
        self.cb_details.set_active(self.config.report.include_details)
        vbox.pack_start(self.cb_details, False, False, 0)

        # Color & Rate grid
        grid = Gtk.Grid(column_spacing=10, row_spacing=6)
        grid.attach(_make_label("Accent Color (Hex):"), 0, 0, 1, 1)
        self.entry_color = Gtk.Entry()
        self.entry_color.set_text(self.config.report.accent_color)
        grid.attach(self.entry_color, 1, 0, 1, 1)

        grid.attach(_make_label("Hourly Rate ($/hr):"), 0, 1, 1, 1)
        self.entry_rate = Gtk.Entry()
        self.entry_rate.set_text(str(self.config.report.hourly_rate))
        grid.attach(self.entry_rate, 1, 1, 1, 1)

        vbox.pack_start(grid, False, False, 0)

        # Result label
        self.lbl_result = _make_label("")
        vbox.pack_start(self.lbl_result, False, False, 4)

        # Dialog buttons
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        btn_gen = self.add_button("Generate PDF", Gtk.ResponseType.OK)
        btn_gen.connect("clicked", self.on_generate)

        self.show_all()

    def on_generate(self, widget):
        proj_text = self.project_combo.get_active_text()
        project_name = None if proj_text == "All Projects" else proj_text

        start_date = None
        end_date = None
        today = date.today()

        if self.rb_today.get_active():
            start_date = today.isoformat()
            end_date = today.isoformat()
        elif self.rb_week.get_active():
            start_date = (today - timedelta(days=7)).isoformat()
            end_date = today.isoformat()
        elif self.rb_month.get_active():
            start_date = (today - timedelta(days=30)).isoformat()
            end_date = today.isoformat()

        rep_cfg = ReportConfig(
            developer_name=self.config.report.developer_name,
            accent_color=self.entry_color.get_text() or "#1E40AF",
            hourly_rate=float(self.entry_rate.get_text() or 0.0),
            include_details=self.cb_details.get_active(),
            include_research=True,
            include_modified_files=True
        )

        data = self.db.get_report_data(project_name, start_date, end_date)
        
        proj_slug = (project_name or "all_projects").replace(" ", "_")
        date_slug = f"{start_date or 'earliest'}_to_{end_date or 'latest'}"
        filename = os.path.expanduser(f"~/TimeTracker_{proj_slug}_{date_slug}.pdf")

        generator = PDFReportGenerator(filename, rep_cfg)
        generator.generate(data)

        self.lbl_result.set_markup(f"<b>✓ Generated:</b> {filename}")
        try:
            if sys.platform == "win32":
                os.startfile(filename)
            elif sys.platform == "darwin":
                subprocess.run(["open", filename], check=False)
            else:
                subprocess.run(["xdg-open", filename], check=False)
        except Exception:
            pass


def main():
    win = MainWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
