#!/usr/bin/env bash
# BRK File Association Installer for Linux
#
# BRK is NOT a universal lossless compressor.
# BRK does not break Shannon's theorem.
#
# Usage:
#   System-wide:  sudo ./install-association.sh
#   User-local:   ./install-association.sh --user
#   Uninstall:    ./install-association.sh --uninstall
#                 ./install-association.sh --uninstall --user

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIME_XML="$SCRIPT_DIR/brk.xml"
DESKTOP_FILE="$SCRIPT_DIR/brk-inspect.desktop"

USER_MODE=false
UNINSTALL=false

for arg in "$@"; do
    case "$arg" in
        --user) USER_MODE=true ;;
        --uninstall) UNINSTALL=true ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

if [ "$UNINSTALL" = true ]; then
    echo "[BRK] Uninstalling file association..."
    if [ "$USER_MODE" = true ]; then
        rm -f ~/.local/share/mime/packages/brk.xml
        rm -f ~/.local/share/applications/brk-inspect.desktop
        update-mime-database ~/.local/share/mime 2>/dev/null || true
        update-desktop-database ~/.local/share/applications 2>/dev/null || true
    else
        sudo rm -f /usr/share/mime/packages/brk.xml
        sudo rm -f /usr/share/applications/brk-inspect.desktop
        sudo update-mime-database /usr/share/mime 2>/dev/null || true
        sudo update-desktop-database /usr/share/applications 2>/dev/null || true
    fi
    echo "[BRK] Uninstalled."
    exit 0
fi

echo "[BRK] Installing .brk file association..."

# Install MIME type
if [ "$USER_MODE" = true ]; then
    mkdir -p ~/.local/share/mime/packages
    cp "$MIME_XML" ~/.local/share/mime/packages/brk.xml
    update-mime-database ~/.local/share/mime 2>/dev/null || true

    mkdir -p ~/.local/share/applications
    cp "$DESKTOP_FILE" ~/.local/share/applications/
    update-desktop-database ~/.local/share/applications 2>/dev/null || true
else
    sudo mkdir -p /usr/share/mime/packages
    sudo cp "$MIME_XML" /usr/share/mime/packages/brk.xml
    sudo update-mime-database /usr/share/mime 2>/dev/null || true

    sudo mkdir -p /usr/share/applications
    sudo cp "$DESKTOP_FILE" /usr/share/applications/
    sudo update-desktop-database /usr/share/applications 2>/dev/null || true
fi

echo "[BRK] Installation complete!"
echo ""
echo "  Extension : .brk"
echo "  MIME type : application/vnd.brk"
echo "  Double-click .brk file -> Inspect in terminal"
echo ""
echo "  To uninstall: $0 --uninstall $([ "$USER_MODE" = true ] && echo '--user')"
