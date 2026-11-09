#!/usr/bin/env bash
# ==============================================================================
# TimeTracker v2 - Universal Linux Installer
# Automatically installs dependencies, creates an isolated environment with
# system PyGObject bindings, and sets up CLI & Desktop menu integration.
# ==============================================================================

set -e

# Terminal colors
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
RESET="\033[0m"

echo -e "\n${BOLD}${BLUE}=== TimeTracker v2 Linux Installer ===${RESET}\n"

# Directory configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$HOME/.local/share/timetracker"
VENV_DIR="$APP_DIR/venv"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

# ------------------------------------------------------------------------------
# 1. Check for Package Manager and System PyGObject / GTK3 Dependencies
# ------------------------------------------------------------------------------
echo -e "${BOLD}[1/5] Checking system GTK3 & PyGObject prerequisites...${RESET}"

MISSING_PKGS=()

if command -v apt-get >/dev/null 2>&1; then
    for pkg in python3-gi python3-gi-cairo gir1.2-gtk-3.0 x11-utils xprintidle python3-pip python3-venv; do
        if ! dpkg -s "$pkg" >/dev/null 2>&1; then
            MISSING_PKGS+=("$pkg")
        fi
    done

    if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
        echo -e "${YELLOW}Missing recommended system packages: ${MISSING_PKGS[*]}${RESET}"
        read -rp "Would you like to install them now with sudo? [Y/n] " install_choice
        install_choice=${install_choice:-Y}
        if [[ "$install_choice" =~ ^[Yy]$ ]]; then
            sudo apt-get update && sudo apt-get install -y "${MISSING_PKGS[@]}"
        else
            echo -e "${YELLOW}Continuing without installing system packages. Note: PyGObject may fail if missing.${RESET}"
        fi
    else
        echo -e "${GREEN}✓ All required system GTK3 & PyGObject packages are installed.${RESET}"
    fi

elif command -v dnf >/dev/null 2>&1; then
    echo -e "${CYAN}Fedora/RHEL system detected.${RESET}"
    if ! rpm -q python3-gobject gtk3 xorg-x11-utils >/dev/null 2>&1; then
        echo -e "${YELLOW}To ensure PyGObject works, please run:${RESET}"
        echo "  sudo dnf install -y python3-gobject gtk3 xorg-x11-utils python3-pip"
    fi

elif command -v pacman >/dev/null 2>&1; then
    echo -e "${CYAN}Arch Linux system detected.${RESET}"
    if ! pacman -Qi python-gobject gtk3 >/dev/null 2>&1; then
        echo -e "${YELLOW}To ensure PyGObject works, please run:${RESET}"
        echo "  sudo pacman -S --needed python-gobject gtk3 xorg-xprop python-pip"
    fi
fi

# ------------------------------------------------------------------------------
# 2. Find Python Interpreter with Working PyGObject
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[2/5] Locating Python interpreter with PyGObject...${RESET}"

PY_CMD=""
# Test standard candidates in order of preference
for cand in "/usr/bin/python3" "/usr/bin/python3.10" "/usr/bin/python3.11" "/usr/bin/python3.12" "$(which python3 2>/dev/null)"; do
    if [ -n "$cand" ] && [ -x "$cand" ]; then
        if "$cand" -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" >/dev/null 2>&1; then
            PY_CMD="$cand"
            break
        fi
    fi
done

if [ -z "$PY_CMD" ]; then
    echo -e "${YELLOW}Warning: Could not find a python with PyGObject installed.${RESET}"
    echo -e "Falling back to default python3: $(which python3)"
    PY_CMD="$(which python3)"
else
    echo -e "${GREEN}✓ Found compatible Python with PyGObject:${RESET} $PY_CMD"
fi

# ------------------------------------------------------------------------------
# 3. Setup Dedicated Virtual Environment with System Site Packages
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[3/5] Setting up isolated application environment...${RESET}"
mkdir -p "$APP_DIR"
mkdir -p "$BIN_DIR"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtualenv with system-site-packages in $VENV_DIR..."
    "$PY_CMD" -m venv --system-site-packages "$VENV_DIR"
fi

# Upgrade pip and install package
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null 2>&1 || true

echo "Installing TimeTracker v2 and Python dependencies..."
"$VENV_DIR/bin/pip" install -e "$PROJECT_ROOT"

# Copy application assets
if [ -f "$PROJECT_ROOT/assets/icon.jpg" ]; then
    cp "$PROJECT_ROOT/assets/icon.jpg" "$APP_DIR/icon.jpg"
fi

# ------------------------------------------------------------------------------
# 4. Install Executable Launchers into ~/.local/bin
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[4/5] Installing command line wrappers to $BIN_DIR...${RESET}"

# timetracker CLI
cat << EOF > "$BIN_DIR/timetracker"
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" -m timetracker.cli "\$@"
EOF
chmod +x "$BIN_DIR/timetracker"

# timetracker-gui
cat << EOF > "$BIN_DIR/timetracker-gui"
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" -m timetracker.gui "\$@"
EOF
chmod +x "$BIN_DIR/timetracker-gui"

# timetracker-daemon
cat << EOF > "$BIN_DIR/timetracker-daemon"
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" -m timetracker.daemon "\$@"
EOF
chmod +x "$BIN_DIR/timetracker-daemon"

echo -e "${GREEN}✓ Created wrappers for: timetracker, timetracker-gui, timetracker-daemon${RESET}"

# ------------------------------------------------------------------------------
# 5. Create Desktop Entry (.desktop)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[5/5] Creating application launcher...${RESET}"
mkdir -p "$DESKTOP_DIR"

ICON_PATH="$APP_DIR/icon.jpg"

cat << EOF > "$DESKTOP_DIR/timetracker.desktop"
[Desktop Entry]
Type=Application
Version=2.0
Name=TimeTracker v2
Comment=Ambient developer time tracking & PDF reporting
Exec=$BIN_DIR/timetracker-gui
Icon=$ICON_PATH
Terminal=false
Categories=Development;Utility;
Keywords=coding;time;tracking;report;
StartupNotify=true
EOF
chmod 644 "$DESKTOP_DIR/timetracker.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo -e "${GREEN}✓ Desktop launcher installed:${RESET} $DESKTOP_DIR/timetracker.desktop"

# ------------------------------------------------------------------------------
# Verification & PATH Check
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${GREEN}===============================================${RESET}"
echo -e "${BOLD}${GREEN}  TimeTracker v2 Installation Successful!     ${RESET}"
echo -e "${BOLD}${GREEN}===============================================${RESET}\n"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}Notice: $BIN_DIR is not currently in your PATH.${RESET}"
    echo "To add it, append this line to your ~/.bashrc or ~/.zshrc:"
    echo -e "  ${BOLD}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}\n"
fi

echo -e "Quick Commands:"
echo -e "  ${CYAN}timetracker status${RESET}     - Check current tracking & today's hours"
echo -e "  ${CYAN}timetracker gui${RESET}        - Open GTK3 desktop interface"
echo -e "  ${CYAN}timetracker projects${RESET}   - List tracked projects"
echo -e "  ${CYAN}timetracker report${RESET}     - Generate customized PDF report"
echo -e "  ${CYAN}timetracker autostart enable${RESET} - Start automatically at login\n"
