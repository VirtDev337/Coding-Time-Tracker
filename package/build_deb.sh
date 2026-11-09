#!/usr/bin/env bash
# ==============================================================================
# TimeTracker v2 - Debian/Ubuntu (.deb) Package Builder
# Builds a standalone .deb package that declares all required GTK3 and Python
# system dependencies for seamless installation via apt/dpkg.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PKG_NAME="timetrackerv2"
PKG_VERSION="2.0.0"
PKG_ARCH="all"
BUILD_DIR="$PROJECT_ROOT/build_deb/${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}"
OUTPUT_DIR="$PROJECT_ROOT/dist"

echo "Building Debian package for TimeTracker v2 (${PKG_VERSION})..."

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/lib/python3/dist-packages"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$OUTPUT_DIR"

# 1. Copy Python Package (excluding pycache)
cp -r "$PROJECT_ROOT/src/timetracker" "$BUILD_DIR/usr/lib/python3/dist-packages/"
find "$BUILD_DIR/usr/lib/python3/dist-packages" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR/usr/lib/python3/dist-packages" -name "*.pyc" -delete 2>/dev/null || true

# 2. Install Executables into /usr/bin
cat << 'EOF' > "$BUILD_DIR/usr/bin/timetracker"
#!/usr/bin/python3
from timetracker.cli import main
import sys
if __name__ == "__main__":
    sys.exit(main())
EOF
chmod 755 "$BUILD_DIR/usr/bin/timetracker"

cat << 'EOF' > "$BUILD_DIR/usr/bin/timetracker-gui"
#!/usr/bin/python3
from timetracker.gui import main
import sys
if __name__ == "__main__":
    sys.exit(main())
EOF
chmod 755 "$BUILD_DIR/usr/bin/timetracker-gui"

cat << 'EOF' > "$BUILD_DIR/usr/bin/timetracker-daemon"
#!/usr/bin/python3
from timetracker.daemon import main
import sys
if __name__ == "__main__":
    sys.exit(main())
EOF
chmod 755 "$BUILD_DIR/usr/bin/timetracker-daemon"

# 3. Application Icon
if [ -f "$PROJECT_ROOT/assets/icon.jpg" ]; then
    cp "$PROJECT_ROOT/assets/icon.jpg" "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps/timetracker.jpg"
fi

# 4. Desktop Entry
cat << EOF > "$BUILD_DIR/usr/share/applications/timetracker.desktop"
[Desktop Entry]
Type=Application
Version=2.0
Name=TimeTracker v2
Comment=Ambient developer time tracking & PDF reporting
Exec=/usr/bin/timetracker-gui
Icon=/usr/share/icons/hicolor/256x256/apps/timetracker.jpg
Terminal=false
Categories=Development;Utility;
Keywords=coding;time;tracking;report;
StartupNotify=true
EOF
chmod 644 "$BUILD_DIR/usr/share/applications/timetracker.desktop"

# 5. DEBIAN/control
cat << EOF > "$BUILD_DIR/DEBIAN/control"
Package: ${PKG_NAME}
Version: ${PKG_VERSION}
Section: utils
Priority: optional
Architecture: ${PKG_ARCH}
Depends: python3 (>= 3.8), python3-gi, python3-gi-cairo, gir1.2-gtk-3.0, x11-utils, xprintidle, python3-psutil, python3-watchdog, python3-reportlab, python3-pil
Maintainer: VirtDev <com.virtdev@gmail.com>
Homepage: https://github.com/VirtDev337
Description: Ambient developer time tracker for IDEs and browser research
 TimeTracker v2 automatically logs time spent coding in IDEs,
 researching technical topics in web browsers, and pair-programming
 with AI assistants, without requiring manual timers. Generates
 customizable executive PDF reports and includes both CLI and GTK3 GUI.
EOF

# 6. Post-install & Pre-remove hooks
cat << 'EOF' > "$BUILD_DIR/DEBIAN/postinst"
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
EOF
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

cat << 'EOF' > "$BUILD_DIR/DEBIAN/prerm"
#!/bin/sh
set -e
pkill -f "timetracker.daemon" 2>/dev/null || true
pkill -f "timetracker.gui" 2>/dev/null || true
EOF
chmod 755 "$BUILD_DIR/DEBIAN/prerm"

# 7. Build Package
dpkg-deb --build --root-owner-group "$BUILD_DIR" "$OUTPUT_DIR/${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}.deb"

echo ""
echo "✓ Package successfully created at:"
echo "  $OUTPUT_DIR/${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}.deb"
echo ""
echo "Installation command:"
echo "  sudo apt install ./dist/${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}.deb"
