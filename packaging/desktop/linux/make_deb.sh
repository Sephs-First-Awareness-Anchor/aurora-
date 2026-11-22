#!/usr/bin/env bash
# Build a .deb after packaging/desktop/build.py has produced dist/AuroraDesktop.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
APP="$ROOT/dist/AuroraDesktop"
OUT="$ROOT/dist/Aurora-Linux-amd64.deb"
[[ -f "$APP/AuroraDesktop" ]] || { echo "Missing PyInstaller output" >&2; exit 1; }
STAGE="$ROOT/build/aurora-deb"
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$STAGE/opt/aurora" "$STAGE/usr/bin" "$STAGE/usr/share/applications"
cp -a "$APP/." "$STAGE/opt/aurora/"
cat > "$STAGE/usr/bin/aurora-desktop" <<'SH'
#!/bin/sh
# Keep native Qt/PyInstaller startup diagnostics available without a terminal.
# Logs are private to the current user, never stored inside the installed app.
umask 077
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/aurora"
mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="${TMPDIR:-/tmp}"
LOG="$LOG_DIR/desktop-launch.log"
if /opt/aurora/AuroraDesktop "$@" >>"$LOG" 2>&1; then
    exit 0
else
    code=$?
    message="Aurora could not start (exit $code).\n\nStartup details were saved to:\n$LOG\n\nPlease share only the error lines, not private credentials."
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="Aurora could not open" --width=470 --text="$message" 2>/dev/null || true
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --error "$message" --title "Aurora could not open" 2>/dev/null || true
    elif command -v xmessage >/dev/null 2>&1; then
        xmessage -center "$message" 2>/dev/null || true
    fi
    exit "$code"
fi
SH
cat > "$STAGE/usr/share/applications/aurora.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Aurora
Comment=Aurora's persistent Subsurface and desktop Hub
Exec=aurora-desktop
Icon=applications-science
Terminal=false
Categories=Utility;Science;
StartupNotify=true
DESKTOP
cat > "$STAGE/DEBIAN/control" <<'CONTROL'
Package: aurora-desktop
Version: 0.1.0
Architecture: amd64
Depends: libc6 (>= 2.35), libgl1, libegl1, libnss3, libgbm1, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-keysyms1, libxcb-shape0, libxcomposite1, libxdamage1, libxrandr2, libasound2 | libasound2t64
Maintainer: Aurora Project
Section: science
Priority: optional
Description: Aurora desktop resident and native Hub
 One shared canonical Aurora runtime and an integrated local UI.
 Historical state is stored in the user's home directory, not the package.
CONTROL
chmod +x "$STAGE/usr/bin/aurora-desktop" "$STAGE/opt/aurora/AuroraDesktop"
dpkg-deb --root-owner-group --build "$STAGE" "$OUT"
echo "Built $OUT"
