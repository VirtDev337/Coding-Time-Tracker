"""
Configuration manager for TimeTracker.
Stores and loads user preferences from ~/.codetime/config.json.
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any


DEFAULT_CONFIG_DIR = Path.home() / ".codetime"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_DB_PATH = DEFAULT_CONFIG_DIR / "timetracker.db"


@dataclass
class ReportConfig:
    developer_name: str = "VirtDev"
    hourly_rate: float = 75.0
    currency: str = "USD"
    accent_color: str = "#1E40AF"  # Classic deep blue
    secondary_color: str = "#0F172A"
    include_details: bool = True
    include_research: bool = True
    include_modified_files: bool = True
    logo_path: str = ""


@dataclass
class TrackerConfig:
    db_path: str = str(DEFAULT_DB_PATH)
    poll_interval_seconds: int = 5
    idle_threshold_seconds: int = 180  # 3 minutes of no user activity
    supported_ides: List[str] = field(default_factory=lambda: [
        "code", "codium", "rstudio", "pycharm", "sublime_text",
        "cursor", "windsurf", "zed", "atom"
    ])
    supported_browsers: List[str] = field(default_factory=lambda: [
        "firefox", "chrome", "google-chrome", "brave", "brave-browser",
        "chromium", "microsoft-edge", "edge", "opera", "vivaldi"
    ])
    supported_ai_tools: List[str] = field(default_factory=lambda: [
        "antigravity", "agy", "gemini", "cursor", "claude", "chatgpt"
    ])
    research_domains: List[str] = field(default_factory=lambda: [
        "stackoverflow.com", "stackexchange.com", "github.com", "gitlab.com",
        "developer.mozilla.org", "python.org", "pypi.org", "docs.",
        "arxiv.org", "w3schools.com", "geeksforgeeks.org", "chatgpt.com",
        "claude.ai", "gemini.google.com", "medium.com", "dev.to"
    ])
    distraction_domains: List[str] = field(default_factory=lambda: [
        "facebook.com", "twitter.com", "x.com", "instagram.com", "reddit.com",
        "youtube.com", "netflix.com", "tiktok.com", "linkedin.com", "pinterest.com"
    ])
    report: ReportConfig = field(default_factory=ReportConfig)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrackerConfig":
        report_data = data.pop("report", {})
        report_config = ReportConfig(**report_data) if isinstance(report_data, dict) else ReportConfig()
        return cls(report=report_config, **data)


def ensure_config_dir() -> Path:
    """Ensure ~/.codetime exists and return its path."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_DIR


def load_config(config_path: Path = DEFAULT_CONFIG_PATH) -> TrackerConfig:
    """Load configuration from file, or create default if not present."""
    ensure_config_dir()
    if not config_path.exists():
        cfg = TrackerConfig()
        save_config(cfg, config_path)
        return cfg

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return TrackerConfig.from_dict(data)
    except Exception as e:
        print(f"[Warning] Failed to read {config_path}: {e}. Using defaults.")
        return TrackerConfig()


def save_config(config: TrackerConfig, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Save configuration to JSON file."""
    ensure_config_dir()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=4)
