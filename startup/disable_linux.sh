#!/usr/bin/env bash
# ==============================================================================
# TimeTracker v2 - Disable Startup on Linux
# Removes XDG Autostart entry and stops/disables systemd user service.
# ==============================================================================

echo "[TimeTracker] Disabling startup on Linux..."

# 1. Remove XDG Autostart entry
DESKTOP_FILE="$HOME/.config/autostart/timetracker.desktop"
if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    echo "[✓] Removed XDG desktop autostart: $DESKTOP_FILE"
fi

# 2. Stop and disable systemd service if present
if command -v systemctl >/dev/null 2>&1; then
    SERVICE_FILE="$HOME/.config/systemd/user/timetracker.service"
    if [ -f "$SERVICE_FILE" ]; then
        systemctl --user stop timetracker.service 2>/dev/null || true
        systemctl --user disable timetracker.service 2>/dev/null || true
        rm -f "$SERVICE_FILE"
        systemctl --user daemon-reload 2>/dev/null || true
        echo "[✓] Disabled and removed systemd user service: $SERVICE_FILE"
    fi
fi

# 3. Kill any remaining daemon background instances
pkill -f "timetracker daemon" 2>/dev/null || true

echo "[✓] TimeTracker startup successfully disabled on Linux."
