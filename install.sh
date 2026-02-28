#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

install -Dm755 "$ROOT_DIR/nvidia_eject_helper.py" /usr/local/libexec/nvidia-eject-helper
install -Dm644 "$ROOT_DIR/com.github.anlorsp.nvidia-tray.policy" /usr/share/polkit-1/actions/com.github.anlorsp.nvidia-tray.policy
install -Dm755 "$ROOT_DIR/nvidia_tray.py" /usr/local/bin/nvidia-tray
install -Dm644 "$ROOT_DIR/nvidia-tray.service" /usr/lib/systemd/user/nvidia-tray.service

echo "Installed:"
echo "  /usr/local/bin/nvidia-tray"
echo "  /usr/local/libexec/nvidia-eject-helper"
echo "  /usr/share/polkit-1/actions/com.github.anlorsp.nvidia-tray.policy"
echo "  /usr/lib/systemd/user/nvidia-tray.service"
echo ""
echo "To enable autostart:"
echo "  systemctl --user enable --now nvidia-tray.service"
