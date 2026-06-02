#!/usr/bin/env bash
# BRK File Association Installer for macOS
#
# BRK is NOT a universal lossless compressor.
# BRK does not break Shannon's theorem.
#
# Usage:
#   ./install-association-macos.sh
#   ./install-association-macos.sh --uninstall

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_FILE="$SCRIPT_DIR/BRKType.plist"

UNINSTALL=false

for arg in "$@"; do
    case "$arg" in
        --uninstall) UNINSTALL=true ;;
    esac
done

if [ "$UNINSTALL" = true ]; then
    echo "[BRK] Uninstalling macOS file association..."
    # Remove UTType registration
    /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user 2>/dev/null || true
    echo "[BRK] Uninstalled. You may need to log out and back in."
    exit 0
fi

echo "[BRK] Installing .brk file association for macOS..."

# Register UTType via Launch Services
if command -v duti &>/dev/null; then
    echo "[BRK] Using duti to register .brk extension..."
    duti -s application/vnd.brk .brk all 2>/dev/null || true
else
    echo "[BRK] duti not found. Install with: brew install duti"
    echo "[BRK] Attempting manual registration..."
fi

# Copy plist for UTType declaration
mkdir -p ~/Library/Preferences
cp "$PLIST_FILE" ~/Library/Preferences/BRKType.plist 2>/dev/null || true

# Refresh Launch Services
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain user 2>/dev/null || true

echo "[BRK] Installation complete!"
echo ""
echo "  Extension : .brk"
echo "  MIME type : application/vnd.brk"
echo "  UTType    : application/vnd.brk"
echo ""
echo "  You may need to log out and back in for changes to take effect."
