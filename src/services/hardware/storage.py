"""
Storage type detection per SPEC_v3 Section 4.6.2.

Detects storage interface type (NVMe, SATA SSD, HDD) for model directories.
Storage speed significantly impacts model loading times.

| Storage Type | Sequential Read | 10GB Model Load |
|--------------|-----------------|-----------------|
| NVMe Gen 4   | 7,000 MB/s      | 1.4 seconds     |
| NVMe Gen 3   | 3,500 MB/s      | 2.9 seconds     |
| SATA SSD     | 600 MB/s        | 16.7 seconds    |
| HDD          | 120-160 MB/s    | 83 seconds      |

NEW in Phase 1 - does not replace existing code.
See: docs/MIGRATION_PROTOCOL.md Section 3
"""

import os
import platform
import subprocess
import re
from enum import Enum
from typing import Optional
from pathlib import Path

from src.utils.logger import log


class StorageType(Enum):
    """Storage interface types."""
    NVME_GEN4 = "nvme_gen4"
    NVME_GEN3 = "nvme_gen3"
    NVME = "nvme"          # NVMe, unknown generation
    SATA_SSD = "sata_ssd"
    HDD = "hdd"
    UNKNOWN = "unknown"


def detect_storage_type(path: str = ".") -> StorageType:
    """
    Detect storage interface type for a given path.

    Args:
        path: Path to check (default: current directory)

    Returns:
        StorageType enum value

    Example:
        storage = detect_storage_type("/models")
        if storage == StorageType.HDD:
            print("Warning: Model loading will be slow")
    """
    path = os.path.abspath(path)

    if platform.system() == "Windows":
        return _detect_windows(path)
    elif platform.system() == "Darwin":
        return _detect_macos(path)
    elif platform.system() == "Linux":
        return _detect_linux(path)
    else:
        return StorageType.UNKNOWN


def _detect_windows(path: str) -> StorageType:
    """
    Detect storage type on Windows using PowerShell/WMI.

    Uses Get-PhysicalDisk to determine media type.
    """
    try:
        # Get the drive letter from path
        drive = os.path.splitdrive(path)[0]
        if not drive:
            drive = "C:"

        # PowerShell command to get disk info
        # First, get the disk number for the volume
        ps_script = f'''
$volume = Get-Volume -DriveLetter '{drive[0]}'
$partition = Get-Partition -DriveLetter '{drive[0]}'
$disk = Get-PhysicalDisk | Where-Object {{ $_.DeviceId -eq $partition.DiskNumber }}
$disk | Select-Object MediaType, BusType | ConvertTo-Json
'''
        result = subprocess.check_output(
            ["powershell", "-Command", ps_script],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stderr=subprocess.DEVNULL,
            timeout=10
        ).decode()

        # Parse JSON output
        import json
        disk_info = json.loads(result)

        media_type = disk_info.get("MediaType", "").upper()
        bus_type = disk_info.get("BusType", "").upper()

        # Determine storage type
        if "NVME" in bus_type:
            return StorageType.NVME
        elif "SSD" in media_type:
            if "SATA" in bus_type:
                return StorageType.SATA_SSD
            return StorageType.NVME  # Assume NVMe if SSD but not SATA
        elif "HDD" in media_type or "UNSPECIFIED" in media_type:
            return StorageType.HDD

        return StorageType.UNKNOWN

    except subprocess.TimeoutExpired:
        log.warning("Storage detection timed out on Windows")
        return StorageType.UNKNOWN
    except Exception as e:
        log.debug(f"Windows storage detection failed: {e}")
        return StorageType.UNKNOWN


def _detect_macos(path: str) -> StorageType:
    """
    Detect storage type on macOS using diskutil.

    Apple Silicon Macs always have NVMe, but external drives may vary.
    """
    try:
        # Get the mount point for the path
        result = subprocess.check_output(
            ["df", path],
            stderr=subprocess.DEVNULL
        ).decode()

        # Parse df output to get device
        lines = result.strip().split('\n')
        if len(lines) < 2:
            return StorageType.UNKNOWN

        device = lines[1].split()[0]  # e.g., /dev/disk1s1

        # Get disk info via diskutil
        result = subprocess.check_output(
            ["diskutil", "info", device],
            stderr=subprocess.DEVNULL
        ).decode()

        # Check for NVMe
        if "NVMe" in result or "Apple SSD" in result:
            return StorageType.NVME

        # Check for SSD vs HDD
        if "Solid State" in result or "SSD" in result:
            # Check protocol for SATA vs NVMe
            if "SATA" in result:
                return StorageType.SATA_SSD
            return StorageType.NVME

        if "Rotational" in result or "HDD" in result:
            return StorageType.HDD

        # Apple Silicon internal storage is always NVMe
        if "Internal" in result and platform.machine() == "arm64":
            return StorageType.NVME

        return StorageType.UNKNOWN

    except Exception as e:
        log.debug(f"macOS storage detection failed: {e}")

        # Fallback: Apple Silicon Macs have NVMe
        if platform.machine() == "arm64":
            return StorageType.NVME

        return StorageType.UNKNOWN


def _detect_linux(path: str) -> StorageType:
    """
    Detect storage type on Linux using /sys/block/.

    Checks rotational flag and transport type.
    """
    try:
        # Get the device for the path
        result = subprocess.check_output(
            ["df", path],
            stderr=subprocess.DEVNULL
        ).decode()

        lines = result.strip().split('\n')
        if len(lines) < 2:
            return StorageType.UNKNOWN

        device_path = lines[1].split()[0]  # e.g., /dev/sda1 or /dev/nvme0n1p1

        # Extract base device name
        device_name = os.path.basename(device_path)

        # Handle partition numbers (sda1 -> sda, nvme0n1p1 -> nvme0n1)
        if device_name.startswith("nvme"):
            # NVMe devices: nvme0n1p1 -> nvme0n1
            match = re.match(r"(nvme\d+n\d+)", device_name)
            if match:
                device_name = match.group(1)
            return StorageType.NVME
        else:
            # Traditional devices: sda1 -> sda
            device_name = re.sub(r'\d+$', '', device_name)

        # Check rotational flag
        rotational_path = f"/sys/block/{device_name}/queue/rotational"
        if os.path.exists(rotational_path):
            with open(rotational_path, 'r') as f:
                is_rotational = f.read().strip() == "1"

            if is_rotational:
                return StorageType.HDD
            else:
                # Check if NVMe or SATA SSD
                transport_path = f"/sys/block/{device_name}/device/transport"
                if os.path.exists(transport_path):
                    with open(transport_path, 'r') as f:
                        transport = f.read().strip().lower()
                    if "nvme" in transport:
                        return StorageType.NVME
                    elif "sata" in transport:
                        return StorageType.SATA_SSD

                # Check device symlink for transport
                device_link = f"/sys/block/{device_name}"
                if os.path.islink(device_link):
                    real_path = os.path.realpath(device_link)
                    if "nvme" in real_path:
                        return StorageType.NVME
                    elif "ata" in real_path or "sata" in real_path:
                        return StorageType.SATA_SSD

                return StorageType.SATA_SSD  # Assume SATA SSD if non-rotational

        return StorageType.UNKNOWN

    except Exception as e:
        log.debug(f"Linux storage detection failed: {e}")
        return StorageType.UNKNOWN


def get_storage_warning(storage_type: StorageType) -> Optional[str]:
    """
    Get user-facing warning message for storage type.

    Per SPEC_v3 Section 4.6.2:
    - HDD: Display prominent warning
    - SATA SSD with low RAM: Recommend NVMe upgrade

    Args:
        storage_type: Detected storage type

    Returns:
        Warning message string, or None if no warning needed
    """
    if storage_type == StorageType.HDD:
        return (
            "HDD storage detected. AI model loading will be extremely slow "
            "(~80+ seconds for a 10GB model). Consider using an SSD for models."
        )
    elif storage_type == StorageType.UNKNOWN:
        return "Could not detect storage type. Performance may vary."
    return None


def get_estimated_load_time(storage_type: StorageType, model_size_gb: float) -> float:
    """
    Estimate model load time based on storage type.

    Args:
        storage_type: Detected storage type
        model_size_gb: Model file size in GB

    Returns:
        Estimated load time in seconds
    """
    # Approximate read speeds in MB/s
    speeds = {
        StorageType.NVME_GEN4: 7000,
        StorageType.NVME_GEN3: 3500,
        StorageType.NVME: 3500,       # Assume Gen 3 as baseline
        StorageType.SATA_SSD: 550,
        StorageType.HDD: 140,
        StorageType.UNKNOWN: 550,     # Assume SATA SSD as conservative estimate
    }

    speed = speeds.get(storage_type, 550)
    size_mb = model_size_gb * 1024

    return size_mb / speed
