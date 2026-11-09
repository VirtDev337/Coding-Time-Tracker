"""
SQLite Database Layer for TimeTracker.
Stores heartbeats, project metadata, and file modifications with high reliability.
"""

from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS projects (
    name TEXT PRIMARY KEY,
    directory TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS heartbeats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    project_name TEXT NOT NULL,
    category TEXT NOT NULL,
    window_title TEXT,
    entity TEXT,
    duration_seconds INTEGER NOT NULL,
    FOREIGN KEY(project_name) REFERENCES projects(name) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_heartbeats_time ON heartbeats(timestamp);
CREATE INDEX IF NOT EXISTS idx_heartbeats_proj ON heartbeats(project_name);
CREATE INDEX IF NOT EXISTS idx_heartbeats_cat ON heartbeats(category);

CREATE TABLE IF NOT EXISTS file_modifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    project_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    modification_count INTEGER DEFAULT 1,
    FOREIGN KEY(project_name) REFERENCES projects(name) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_file_mods ON file_modifications(project_name, file_path);
"""


class Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(
            str(self.db_path),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            timeout=10.0
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create tables and indices if they do not exist."""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA)

    def get_or_create_project(self, name: str, directory: str = "") -> None:
        """Ensure project exists in the database and update its last_active_at."""
        local_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (name, directory, created_at, last_active_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    last_active_at = excluded.last_active_at,
                    directory = CASE WHEN ? != '' THEN ? ELSE directory END
                """,
                (name, directory, local_now, local_now, directory, directory)
            )

    def record_heartbeat(
        self,
        project_name: str,
        category: str,
        window_title: str,
        entity: str,
        duration_seconds: int,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Record an active duration slice for a project."""
        if not project_name:
            project_name = "General / Untracked"

        self.get_or_create_project(project_name)

        with self.get_connection() as conn:
            if timestamp:
                ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(timestamp, datetime) else str(timestamp)
            else:
                # Use local time explicitly — SQLite CURRENT_TIMESTAMP is UTC
                ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                INSERT INTO heartbeats (timestamp, project_name, category, window_title, entity, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ts_str, project_name, category, window_title, entity, duration_seconds)
            )

    def record_file_modification(self, project_name: str, file_path: str, count: int = 1) -> None:
        """Record a file modification event."""
        if not project_name:
            return
        self.get_or_create_project(project_name)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO file_modifications (project_name, file_path, modification_count)
                VALUES (?, ?, ?)
                """,
                (project_name, file_path, count)
            )

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Return list of all projects with their total tracked time."""
        query = """
            SELECT 
                p.name,
                p.directory,
                p.created_at,
                p.last_active_at,
                COALESCE(SUM(h.duration_seconds), 0) AS total_seconds,
                COALESCE(SUM(CASE WHEN h.category = 'coding' THEN h.duration_seconds ELSE 0 END), 0) AS coding_seconds,
                COALESCE(SUM(CASE WHEN h.category = 'collaboration' THEN h.duration_seconds ELSE 0 END), 0) AS collaboration_seconds,
                COALESCE(SUM(CASE WHEN h.category = 'research' THEN h.duration_seconds ELSE 0 END), 0) AS research_seconds
            FROM projects p
            LEFT JOIN heartbeats h ON p.name = h.project_name
            GROUP BY p.name
            ORDER BY p.last_active_at DESC
        """
        with self.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]

    def get_today_stats(self) -> Dict[str, Any]:
        """Return today's summary metrics."""
        today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
        query = """
            SELECT 
                COALESCE(SUM(duration_seconds), 0) AS total_seconds,
                COALESCE(SUM(CASE WHEN category = 'coding' THEN duration_seconds ELSE 0 END), 0) AS coding_seconds,
                COALESCE(SUM(CASE WHEN category = 'collaboration' THEN duration_seconds ELSE 0 END), 0) AS collaboration_seconds,
                COALESCE(SUM(CASE WHEN category = 'research' THEN duration_seconds ELSE 0 END), 0) AS research_seconds,
                COUNT(DISTINCT project_name) as project_count
            FROM heartbeats
            WHERE timestamp >= ?
        """
        with self.get_connection() as conn:
            row = conn.execute(query, (today_start,)).fetchone()
            return dict(row) if row else {
                "total_seconds": 0, "coding_seconds": 0, "collaboration_seconds": 0, "research_seconds": 0, "project_count": 0
            }

    def get_top_files(
        self,
        project_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 15
    ) -> List[Tuple[str, int]]:
        """Get top modified files for a project or all projects."""
        clauses = []
        params = []
        if project_name:
            clauses.append("project_name = ?")
            params.append(project_name)
        if start_date:
            clauses.append("timestamp >= ?")
            params.append(f"{start_date} 00:00:00")
        if end_date:
            clauses.append("timestamp <= ?")
            params.append(f"{end_date} 23:59:59")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT file_path, SUM(modification_count) as total_mods
            FROM file_modifications
            {where}
            GROUP BY file_path
            ORDER BY total_mods DESC
            LIMIT ?
        """
        params.append(limit)
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [(r["file_path"], r["total_mods"]) for r in rows]

    def get_top_research(
        self,
        project_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 15
    ) -> List[Tuple[str, int]]:
        """Get top research domains/entities and duration in seconds."""
        clauses = ["category = 'research'", "entity IS NOT NULL", "entity != ''"]
        params = []
        if project_name:
            clauses.append("project_name = ?")
            params.append(project_name)
        if start_date:
            clauses.append("timestamp >= ?")
            params.append(f"{start_date} 00:00:00")
        if end_date:
            clauses.append("timestamp <= ?")
            params.append(f"{end_date} 23:59:59")

        where = f"WHERE {' AND '.join(clauses)}"
        query = f"""
            SELECT entity, SUM(duration_seconds) as total_seconds
            FROM heartbeats
            {where}
            GROUP BY entity
            ORDER BY total_seconds DESC
            LIMIT ?
        """
        params.append(limit)
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [(r["entity"], r["total_seconds"]) for r in rows]

    def get_daily_timeline(
        self,
        project_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get daily time breakdown."""
        clauses = []
        params = []
        if project_name:
            clauses.append("project_name = ?")
            params.append(project_name)
        if start_date:
            clauses.append("timestamp >= ?")
            params.append(f"{start_date} 00:00:00")
        if end_date:
            clauses.append("timestamp <= ?")
            params.append(f"{end_date} 23:59:59")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT 
                DATE(timestamp, 'localtime') as day,
                SUM(CASE WHEN category = 'coding' THEN duration_seconds ELSE 0 END) as coding_seconds,
                SUM(CASE WHEN category = 'collaboration' THEN duration_seconds ELSE 0 END) as collaboration_seconds,
                SUM(CASE WHEN category = 'research' THEN duration_seconds ELSE 0 END) as research_seconds,
                SUM(duration_seconds) as total_seconds
            FROM heartbeats
            {where}
            GROUP BY day
            ORDER BY day ASC
        """
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_report_data(
        self,
        project_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Aggregate all metrics required for the comprehensive PDF report."""
        clauses = []
        params = []
        if project_name:
            clauses.append("project_name = ?")
            params.append(project_name)
        if start_date:
            clauses.append("timestamp >= ?")
            params.append(f"{start_date} 00:00:00")
        if end_date:
            clauses.append("timestamp <= ?")
            params.append(f"{end_date} 23:59:59")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        # Aggregate per project
        query = f"""
            SELECT 
                project_name,
                SUM(CASE WHEN category = 'coding' THEN duration_seconds ELSE 0 END) as coding_seconds,
                SUM(CASE WHEN category = 'collaboration' THEN duration_seconds ELSE 0 END) as collaboration_seconds,
                SUM(CASE WHEN category = 'research' THEN duration_seconds ELSE 0 END) as research_seconds,
                SUM(duration_seconds) as total_seconds
            FROM heartbeats
            {where}
            GROUP BY project_name
            ORDER BY total_seconds DESC
        """
        with self.get_connection() as conn:
            project_rows = conn.execute(query, params).fetchall()

        projects_data = []
        grand_coding = 0
        grand_collab = 0
        grand_research = 0
        grand_total = 0

        for r in project_rows:
            p_name = r["project_name"]
            c_sec = r["coding_seconds"]
            collab_sec = r["collaboration_seconds"]
            r_sec = r["research_seconds"]
            t_sec = r["total_seconds"]
            grand_coding += c_sec
            grand_collab += collab_sec
            grand_research += r_sec
            grand_total += t_sec

            files = self.get_top_files(p_name, start_date, end_date, limit=8)
            research = self.get_top_research(p_name, start_date, end_date, limit=8)

            projects_data.append({
                "name": p_name,
                "coding_seconds": c_sec,
                "collaboration_seconds": collab_sec,
                "research_seconds": r_sec,
                "total_seconds": t_sec,
                "coding_formatted": format_duration(c_sec),
                "collaboration_formatted": format_duration(collab_sec),
                "research_formatted": format_duration(r_sec),
                "total_formatted": format_duration(t_sec),
                "files": files,
                "research_topics": [(item[0], format_duration(item[1])) for item in research]
            })

        daily_timeline = self.get_daily_timeline(project_name, start_date, end_date)

        return {
            "project_filter": project_name,
            "start_date": start_date,
            "end_date": end_date,
            "total_coding_seconds": grand_coding,
            "total_collaboration_seconds": grand_collab,
            "total_research_seconds": grand_research,
            "total_seconds": grand_total,
            "total_formatted": format_duration(grand_total),
            "coding_formatted": format_duration(grand_coding),
            "collaboration_formatted": format_duration(grand_collab),
            "research_formatted": format_duration(grand_research),
            "projects": projects_data,
            "timeline": daily_timeline
        }

    def delete_project(self, project_name: str) -> None:
        """Delete all records for a project."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM file_modifications WHERE project_name = ?", (project_name,))
            conn.execute("DELETE FROM heartbeats WHERE project_name = ?", (project_name,))
            conn.execute("DELETE FROM projects WHERE name = ?", (project_name,))


def format_duration(seconds: int) -> str:
    """Format duration in seconds to a human-readable 'Xh Ym' or 'Xm Ys'."""
    if seconds <= 0:
        return "0m"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m"
    return f"{secs}s"
