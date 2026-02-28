#!/usr/bin/env python3
import os
import subprocess
import threading
from typing import List

import gi
import pyudev

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
        
        # Only include display controllers (class 0x03xxxx), skip audio devices (0x04xxxx)
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
                item = Gtk.MenuItem(label=f"弹出 NVIDIA GPU ({pci_id})")
                item.connect("activate", self._on_eject_clicked, pci_id)
                menu.append(item)
        else:
            item = Gtk.MenuItem(label="未检测到 NVIDIA GPU")
            item.set_sensitive(False)
            menu.append(item)

        separator = Gtk.SeparatorMenuItem()
        menu.append(separator)

        quit_item = Gtk.MenuItem(label="退出")
        quit_item.connect("activate", self._on_quit)
        menu.append(quit_item)

        menu.show_all()
        return menu

    def _on_eject_clicked(self, _menu_item: Gtk.MenuItem, pci_id: str) -> None:
        threading.Thread(target=self._run_eject, args=(pci_id,), daemon=True).start()

    def _run_eject(self, pci_id: str) -> None:
        installed_helper = "/usr/local/libexec/nvidia-eject-helper"
        local_helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nvidia_eject_helper.py")
        helper_path = installed_helper if os.path.exists(installed_helper) else local_helper
        cmd = ["pkexec", helper_path, pci_id]
        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0:
            error = completed.stderr.strip() or completed.stdout.strip() or "未知错误"
            GLib.idle_add(self._show_error_dialog, f"弹出失败: {error}")
        GLib.idle_add(self.refresh_ui)

    def _show_error_dialog(self, message: str) -> bool:
        dialog = Gtk.MessageDialog(
            parent=None,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text="NVIDIA 弹出失败",
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
        return False

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
