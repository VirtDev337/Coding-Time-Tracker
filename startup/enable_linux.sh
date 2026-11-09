#!/usr/bin/env bash
# ==============================================================================
# TimeTracker v2 - Enable Startup on Linux
# Configures XDG Autostart and systemd user service.
# ==============================================================================

set -e

# Find executable path
TT_BIN=$(which timetracker 2>/dev/null || echo "")

if [ -z "$TT_BIN" ]; then
    # Fallback to local python user bin
    if [ -f "$HOME/.local/bin/timetracker" ]; then
        TT_BIN="$HOME/.local/bin/timetracker"
    else
        echo "[Error] 'timetracker' command not found in PATH."
        echo "Please install it first: pip install -e ."
        exit 1
    fi
fi

echo "[TimeTracker] Enabling startup using executable: $TT_BIN"

# 1. Configure XDG Autostart (works across GNOME, KDE, XFCE, MATE, i3, etc.)
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

DESKTOP_FILE="$AUTOSTART_DIR/timetracker.desktop"
cat << EOF > "$DESKTOP_FILE"
[Desktop Entry]
Type=Application
Version=1.0
Name=TimeTracker Daemon
Comment=Ambient developer time tracker for IDEs and browser research
Exec=$TT_BIN daemon -q
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
Categories=Development;Utility;
EOF
chmod 644 "$DESKTOP_FILE"
echo "[✓] Configured XDG desktop autostart: $DESKTOP_FILE"

# 2. Configure systemd user service (if systemd is running)
if command -v systemctl >/dev/null 2>&1 && systemctl --user list-units >/dev/null 2>&1; then
    SYSTEMD_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SYSTEMD_DIR"
    SERVICE_FILE="$SYSTEMD_DIR/timetracker.service"

    cat << EOF > "$SERVICE_FILE"
[Unit]
Description=TimeTracker Ambient Background Service
After=graphical-session.target

[Service]
Type=simple
ExecStart=$TT_BIN daemon -q
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable --now timetracker.service 2>/dev/null || true
    echo "[✓] Configured and started systemd user service: timetracker.service"
fi

echo "[✓] TimeTracker startup successfully enabled on Linux."
