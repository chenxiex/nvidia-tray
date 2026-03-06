#!/usr/bin/env python3
import glob
import os
import re
import subprocess
import sys
from typing import List, Tuple

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


def check_nvidia_processes() -> List[Tuple[int, str]]:
    """Check for processes using NVIDIA GPU. Returns list of (pid, process_name) tuples."""
    processes = []
    
    # Try nvidia-smi first (most reliable)
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        try:
                            pid = int(parts[0].strip())
                            name = parts[1].strip()
                            processes.append((pid, name))
                        except ValueError:
                            pass
            return processes
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Fallback: check /dev/nvidia* device files with fuser
    nvidia_devices = glob.glob("/dev/nvidia[0-9]*")
    if nvidia_devices:
        try:
            result = subprocess.run(
                ["fuser"] + nvidia_devices,
                capture_output=True,
                text=True,
                timeout=5,
            )
            # fuser returns PIDs on stdout
            if result.stdout.strip():
                pids = []
                for pid_str in result.stdout.strip().split():
                    try:
                        pid = int(pid_str.rstrip(":").strip())
                        pids.append(pid)
                    except ValueError:
                        pass
                
                # Get process names from /proc
                for pid in pids:
                    try:
                        with open(f"/proc/{pid}/comm", "r") as f:
                            name = f.read().strip()
                            processes.append((pid, name))
                    except (FileNotFoundError, PermissionError):
                        processes.append((pid, f"PID {pid}"))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    
    return processes


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
    
    # Check for running processes using the GPU
    processes = check_nvidia_processes()
    if processes:
        process_list = ", ".join([f"{name} (PID {pid})" for pid, name in processes[:5]])
        if len(processes) > 5:
            process_list += f" 和其他 {len(processes) - 5} 个进程"
        fail(f"无法弹出 GPU：以下进程正在使用 NVIDIA 显卡：{process_list}")
    
    unbind_nvidia_driver_if_needed(pci_id)
    remove_pci_device_if_possible(pci_id)
    print(f"Ejected NVIDIA GPU: {pci_id}")


if __name__ == "__main__":
    main()
