# nvidia-tray

Linux tray application that detects NVIDIA PCI devices and provides an "Eject NVIDIA GPU" menu item.

[中文说明](README.zh-CN.md)

## Features

- Automatically detects NVIDIA PCI devices (vendor ID: `0x10de`)
- Only shows display controllers (PCI class `0x03`), filters out audio devices
- Tray icon is only shown when an NVIDIA device is present
- Tray icon is automatically hidden after the NVIDIA device is removed
- Menu item to eject (unbind + remove) individual PCI devices
- **Checks for processes using the GPU before ejecting** — refuses to eject and lists offending processes if any are found
- Authorizes privileged operations via `pkexec` + `polkit`

## Dependencies

- Python 3
- `python3-gi`
- `python3-pyudev`
- `gir1.2-ayatanaappindicator3-0.1` or `gir1.2-appindicator3-0.1`
- `policykit-1`
- `python3-notify2`
- `gettext` (for locale file compilation, build-time only)

Arch Linux: use the provided PKGBUILD.

## Installation

```bash
cd /path/to/nvidia-tray
sudo ./install.sh
```

Arch Linux: use the provided PKGBUILD.

## Usage

Run manually:

```bash
nvidia-tray
```

Enable autostart (recommended):

```bash
systemctl --user enable --now nvidia-tray.service
```

Disable autostart:

```bash
systemctl --user disable --now nvidia-tray.service
```

## Notes

- The helper only accepts well-formed PCI IDs and verifies that the device vendor is NVIDIA.
- **GPU usage is checked before ejecting**:
  - Uses `fuser` to detect processes with open `/dev/nvidia*` device files
  - If any processes are found, ejection is refused and their names and PIDs are shown
- **Eject procedure**:
  - Writes to the PCI device's `remove` sysfs interface to remove the device from the bus
  - Attempts to unload NVIDIA kernel modules (`nvidia_uvm`, `nvidia_drm`, `nvidia_modeset`, `nvidia`)
- The default polkit policy requires administrator authentication (cached for active sessions).

## Localization

Translations are stored as gettext `.po` files under `locales/`. Compiled `.mo` files are included in the repository.

To add a new language:
1. Create `locales/<lang>/LC_MESSAGES/nvidia-tray.po` based on the existing `zh_CN` file
2. Compile: `msgfmt locales/<lang>/LC_MESSAGES/nvidia-tray.po -o locales/<lang>/LC_MESSAGES/nvidia-tray.mo`
3. Update `install.sh` and `PKGBUILD` to install the new locale file
