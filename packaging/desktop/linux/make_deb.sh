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
exec /opt/aurora/AuroraDesktop "$@"
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
