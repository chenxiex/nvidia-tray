#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

install -Dm755 "$ROOT_DIR/nvidia_eject_helper.py" /usr/lib/nvidia-tray/nvidia-eject-helper
install -Dm644 "$ROOT_DIR/i18n.py" /usr/lib/nvidia-tray/i18n.py
install -Dm644 "$ROOT_DIR/io.github.anlorsp.nvidia-tray.policy" /usr/share/polkit-1/actions/io.github.anlorsp.nvidia-tray.policy
install -Dm755 "$ROOT_DIR/nvidia_tray.py" /usr/lib/nvidia-tray/nvidia-tray
ln -sf /usr/lib/nvidia-tray/nvidia-tray /usr/bin/nvidia-tray
install -Dm644 "$ROOT_DIR/nvidia-tray.service" /usr/lib/systemd/user/nvidia-tray.service

# Install locale files
for po_file in "$ROOT_DIR"/locales/*/LC_MESSAGES/nvidia-tray.po; do
    lang=$(basename "$(dirname "$(dirname "$po_file")")")
    mo_dir="/usr/share/locale/$lang/LC_MESSAGES"
    mkdir -p "$mo_dir"
    msgfmt "$po_file" -o "$mo_dir/nvidia-tray.mo"
done

echo "Installed:"
echo "  /usr/bin/nvidia-tray -> /usr/lib/nvidia-tray/nvidia-tray"
echo "  /usr/lib/nvidia-tray/nvidia-eject-helper"
echo "  /usr/lib/nvidia-tray/i18n.py"
echo "  /usr/share/polkit-1/actions/io.github.anlorsp.nvidia-tray.policy"
echo "  /usr/lib/systemd/user/nvidia-tray.service"
echo "  locale files under /usr/share/locale/"
echo ""
echo "To enable autostart:"
echo "  systemctl --user enable --now nvidia-tray.service"
