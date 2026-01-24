"""SANE scanner control via scanimage."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from tarot_scan.config import (
    DEFAULT_DPI,
    DEFAULT_SCAN_FORMAT,
    DEFAULT_SCAN_MODE,
    get_sane_device,
)


@dataclass
class ScannerDevice:
    """Parsed scanner device info."""

    device_string: str
    name: str
    description: str


class ScannerError(Exception):
    """Scanner operation failed."""

    pass


def list_devices() -> list[ScannerDevice]:
    """List available SANE scanner devices.

    Returns:
        List of detected scanner devices

    Raises:
        ScannerError: If scanimage command fails
    """
    try:
        result = subprocess.run(
            ["scanimage", "-L"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise ScannerError("scanimage not found. Install sane-utils: sudo apt install sane-utils")
    except subprocess.TimeoutExpired:
        raise ScannerError("Scanner detection timed out")

    if result.returncode != 0 and "No scanners" in result.stderr:
        return []

    devices = []
    # Parse lines like: device `escl:https://192.168.1.160:443' is a Brother MFC-L3780CDW series
    pattern = r"device `([^']+)' is a (.+)"
    for line in result.stdout.splitlines() + result.stderr.splitlines():
        match = re.search(pattern, line)
        if match:
            device_string = match.group(1)
            description = match.group(2)
            # Extract short name from device string
            name = device_string.split(":")[-1] if ":" in device_string else device_string
            devices.append(ScannerDevice(device_string, name, description))

    return devices


def get_default_device() -> str:
    """Get the default scanner device string.

    Returns:
        Device string from env var or first detected device

    Raises:
        ScannerError: If no device configured or detected
    """
    env_device = get_sane_device()
    if env_device:
        return env_device

    devices = list_devices()
    if not devices:
        raise ScannerError(
            "No scanner detected. Check connection and run 'scanimage -L' to verify."
        )

    # Prefer escl or airscan:e1 over airscan:w0 (WSD tends to be less reliable)
    for d in devices:
        if d.device_string.startswith("escl:"):
            return d.device_string
    for d in devices:
        if "airscan:e1" in d.device_string:
            return d.device_string

    return devices[0].device_string


def scan_to_path(
    out_path: Path,
    device: str | None = None,
    dpi: int = DEFAULT_DPI,
    mode: str = DEFAULT_SCAN_MODE,
    fmt: str = DEFAULT_SCAN_FORMAT,
    progress_callback=None,
) -> Path:
    """Execute a flatbed scan and save to file.

    Args:
        out_path: Output file path
        device: SANE device string (None = auto-detect)
        dpi: Scan resolution
        mode: Color mode (Color, Gray, Lineart)
        fmt: Output format (png, tiff, jpeg)
        progress_callback: Optional callback(status_msg) for progress

    Returns:
        Path to scanned image

    Raises:
        ScannerError: If scan fails
    """
    device = device or get_default_device()

    # Ensure output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "scanimage",
        "-d",
        device,
        "--resolution",
        str(dpi),
        "--mode",
        mode,
        "--format",
        fmt,
        "-o",
        str(out_path),
    ]

    if progress_callback:
        progress_callback(f"Scanning at {dpi} DPI...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout for high-res scans
        )
    except subprocess.TimeoutExpired:
        raise ScannerError("Scan timed out after 120 seconds")

    if result.returncode != 0:
        # Clean up partial file
        if out_path.exists():
            out_path.unlink()
        raise ScannerError(f"Scan failed: {result.stderr.strip()}")

    if not out_path.exists():
        raise ScannerError("Scan completed but no output file created")

    if progress_callback:
        size_mb = out_path.stat().st_size / (1024 * 1024)
        progress_callback(f"Scan complete: {size_mb:.1f} MB")

    return out_path
