#!/usr/bin/env bash
# ==============================================================================
# TimeTracker v2 - Linux Uninstaller
# Cleans up virtual environment, wrappers, desktop shortcuts, and autostart.
# ==============================================================================

set -e

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "\n${BOLD}${RED}=== TimeTracker v2 Linux Uninstaller ===${RESET}\n"

# Stop any running instances
echo "Stopping any running TimeTracker processes..."
pkill -f "timetracker.daemon" 2>/dev/null || true
pkill -f "timetracker.gui" 2>/dev/null || true

# Remove binaries in ~/.local/bin
echo "Removing CLI wrappers from ~/.local/bin..."
rm -f "$HOME/.local/bin/timetracker"
rm -f "$HOME/.local/bin/timetracker-gui"
rm -f "$HOME/.local/bin/timetracker-daemon"

# Remove desktop launcher
echo "Removing desktop launcher..."
rm -f "$HOME/.local/share/applications/timetracker.desktop"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

# Remove autostart
echo "Removing autostart configurations..."
rm -f "$HOME/.config/autostart/timetracker.desktop"
if [ -d "$HOME/.config/systemd/user" ]; then
    systemctl --user stop timetracker.service 2>/dev/null || true
    systemctl --user disable timetracker.service 2>/dev/null || true
    rm -f "$HOME/.config/systemd/user/timetracker.service"
fi

# Remove venv and application data
APP_DIR="$HOME/.local/share/timetracker"
if [ -d "$APP_DIR" ]; then
    echo "Removing application virtualenv at $APP_DIR..."
    rm -rf "$APP_DIR"
fi

# Ask about database
DB_DIR="$HOME/.codetime"
if [ -d "$DB_DIR" ]; then
    echo ""
    read -rp "Would you also like to delete your tracked database and logs ($DB_DIR)? [y/N] " del_db
    if [[ "$del_db" =~ ^[Yy]$ ]]; then
        rm -rf "$DB_DIR"
        echo -e "${YELLOW}Deleted $DB_DIR${RESET}"
    else
        echo -e "${GREEN}Preserved tracking database at $DB_DIR${RESET}"
    fi
fi

echo -e "\n${BOLD}${GREEN}✓ TimeTracker v2 has been successfully uninstalled.${RESET}\n"
