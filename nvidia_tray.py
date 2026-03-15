#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import threading
from typing import List, Optional

import gi
import notify2
import pyudev

from i18n import _

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402


def list_nvidia_pci_ids() -> List[str]:
    base = "/sys/bus/pci/devices"
    result: List[str] = []
    if not os.path.isdir(base):
        return result

    for device_id in sorted(os.listdir(base)):
        vendor_path = os.path.join(base, device_id, "vendor")
        class_path = os.path.join(base, device_id, "class")
        if not os.path.exists(vendor_path):
            continue
        try:
            with open(vendor_path, "r", encoding="utf-8") as file:
                vendor = file.read().strip().lower()
        except OSError:
            continue
        if vendor != "0x10de":
            continue

        # Only include display controllers (class 0x03xxxx), not audio (0x04xxxx)
        try:
            with open(class_path, "r", encoding="utf-8") as file:
                device_class = file.read().strip().lower()
        except OSError:
            continue
        if device_class.startswith("0x03"):
            result.append(device_id)
    return result


class NvidiaTrayApp:
    def __init__(self) -> None:
        notify2.init("nvidia-tray")
        
        self.indicator = self._create_indicator()
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem="pci")
        self.monitor.start()

        self.monitor_channel = GLib.IOChannel.unix_new(self.monitor.fileno())
        GLib.io_add_watch(
            self.monitor_channel,
            GLib.IO_IN,
            self._on_udev_event,
        )

        self.refresh_ui()

    def _create_indicator(self):
        try:
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import AyatanaAppIndicator3

            indicator = AyatanaAppIndicator3.Indicator.new(
                "nvidia-tray",
                "video-display",
                AyatanaAppIndicator3.IndicatorCategory.HARDWARE,
            )
            indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.PASSIVE)
            self._indicator_mod = AyatanaAppIndicator3
            return indicator
        except (ImportError, ValueError):
            gi.require_version("AppIndicator3", "0.1")
            from gi.repository import AppIndicator3

            indicator = AppIndicator3.Indicator.new(
                "nvidia-tray",
                "video-display",
                AppIndicator3.IndicatorCategory.HARDWARE,
            )
            indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
            self._indicator_mod = AppIndicator3
            return indicator

    def _indicator_set_visible(self, visible: bool) -> None:
        status_enum = self._indicator_mod.IndicatorStatus
        self.indicator.set_status(status_enum.ACTIVE if visible else status_enum.PASSIVE)

    def _build_menu(self, pci_ids: List[str]) -> Gtk.Menu:
        menu = Gtk.Menu()

        if pci_ids:
            for pci_id in pci_ids:
                item = Gtk.MenuItem(label=_("Eject NVIDIA GPU (%s)") % pci_id)
                item.connect("activate", self._on_eject_clicked, pci_id)
                menu.append(item)
        else:
            item = Gtk.MenuItem(label=_("No NVIDIA GPU detected"))
            item.set_sensitive(False)
            menu.append(item)

        separator = Gtk.SeparatorMenuItem()
        menu.append(separator)

        quit_item = Gtk.MenuItem(label=_("Quit"))
        quit_item.connect("activate", self._on_quit)
        menu.append(quit_item)

        menu.show_all()
        return menu

    def _on_eject_clicked(self, _menu_item: Gtk.MenuItem, pci_id: str) -> None:
        threading.Thread(target=self._run_eject, args=(pci_id,), daemon=True).start()

    def _find_helper(self) -> Optional[str]:
        # 1. Search in PATH
        helper = shutil.which("nvidia-eject-helper")
        if helper:
            return helper

        # 2. Check common install locations
        common_paths = [
            "/usr/lib/nvidia-tray/nvidia-eject-helper",
            "/usr/local/lib/nvidia-tray/nvidia-eject-helper",
            "/usr/libexec/nvidia-eject-helper",
            "/usr/local/libexec/nvidia-eject-helper",
        ]
        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        # 3. Fall back to development version in script directory
        local_helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nvidia_eject_helper.py")
        if os.path.isfile(local_helper):
            return local_helper

        return None

    def _run_eject(self, pci_id: str) -> None:
        helper_path = self._find_helper()
        if not helper_path:
            self._send_notification(
                _("NVIDIA GPU operation failed"),
                _("Error: nvidia-eject-helper not found"),
                notify2.URGENCY_CRITICAL,
            )
            return

        cmd = ["pkexec", helper_path, pci_id]
        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0:
            error = completed.stderr.strip() or completed.stdout.strip()
            self._send_notification(
                _("NVIDIA GPU operation failed"),
                error,
                notify2.URGENCY_CRITICAL,
            )
        else:
            # Show output messages from helper (warnings, success info, etc.)
            message = completed.stdout.strip()
            if message:
                self._send_notification(
                    _("NVIDIA GPU operation completed"),
                    message,
                    notify2.URGENCY_NORMAL,
                )
        GLib.idle_add(self.refresh_ui)

    def _send_notification(self, title: str, body: str, urgency: int = notify2.URGENCY_NORMAL) -> None:
        """Send a system desktop notification."""
        try:
            notification = notify2.Notification(title, body, icon="video-display")
            notification.set_urgency(urgency)
            notification.timeout = 5000 if urgency == notify2.URGENCY_NORMAL else 10000
            notification.show()
        except Exception as e:
            print(f"Warning: Failed to send notification: {e}", file=sys.stderr)

    def _on_quit(self, _menu_item: Gtk.MenuItem) -> None:
        Gtk.main_quit()

    def _on_udev_event(self, _source, condition) -> bool:
        if condition & GLib.IO_IN:
            while True:
                device = self.monitor.poll(timeout=0)
                if device is None:
                    break
                action = device.action
                if action in {"add", "remove", "change", "bind", "unbind"}:
                    self.refresh_ui()
        return True

    def refresh_ui(self) -> bool:
        pci_ids = list_nvidia_pci_ids()
        menu = self._build_menu(pci_ids)
        self.indicator.set_menu(menu)
        self._indicator_set_visible(bool(pci_ids))
        return False


def main() -> None:
    NvidiaTrayApp()
    Gtk.main()


if __name__ == "__main__":
    main()
