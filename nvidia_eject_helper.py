#!/usr/bin/env python3
import os
import re
import sys

PCI_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]$")


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()


def write_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def validate_pci_id(pci_id: str) -> str:
    if not PCI_ID_PATTERN.match(pci_id):
        fail(f"Invalid PCI ID format: {pci_id}")
    return pci_id.lower()


def ensure_nvidia_device(pci_id: str) -> None:
    device_dir = f"/sys/bus/pci/devices/{pci_id}"
    vendor_file = os.path.join(device_dir, "vendor")
    if not os.path.exists(device_dir):
        fail(f"PCI device not found: {pci_id}")
    if not os.path.exists(vendor_file):
        fail(f"Vendor file missing for device: {pci_id}")
    vendor = read_file(vendor_file)
    if vendor.lower() != "0x10de":
        fail(f"Device is not NVIDIA (vendor={vendor}): {pci_id}")


def unbind_nvidia_driver_if_needed(pci_id: str) -> None:
    bound_link = f"/sys/bus/pci/drivers/nvidia/{pci_id}"
    unbind_path = "/sys/bus/pci/drivers/nvidia/unbind"
    if os.path.exists(bound_link) and os.path.exists(unbind_path):
        write_file(unbind_path, f"{pci_id}\n")


def remove_pci_device_if_possible(pci_id: str) -> None:
    remove_path = f"/sys/bus/pci/devices/{pci_id}/remove"
    if os.path.exists(remove_path):
        write_file(remove_path, "1\n")
    else:
        fail(f"Remove interface not found: {remove_path}")


def main() -> None:
    if os.geteuid() != 0:
        fail("This helper must run as root (use pkexec).")

    if len(sys.argv) != 2:
        fail("Usage: nvidia_eject_helper.py <PCI_ID>")

    pci_id = validate_pci_id(sys.argv[1])
    ensure_nvidia_device(pci_id)
    unbind_nvidia_driver_if_needed(pci_id)
    remove_pci_device_if_possible(pci_id)
    print(f"Ejected NVIDIA GPU: {pci_id}")


if __name__ == "__main__":
    main()
