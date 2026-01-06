"""
Subprocess utilities for safe external command execution.

Per ARCHITECTURE_PRINCIPLES.md Section 1: I/O Data Normalization Standard

All external I/O data must be normalized before use. This module provides
utilities for running subprocesses with proper output normalization.

Usage:
    from src.utils.subprocess_utils import (
        run_powershell,
        run_command,
        extract_number,
        extract_json,
    )

    # Run PowerShell with profile isolation
    output = run_powershell("(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory")
    mem_bytes = extract_number(output)

    # Run general command
    output = run_command(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
"""

import json
import platform
import re
import subprocess
from typing import Optional, Union, List

from src.utils.logger import log


def run_powershell(
    command: str,
    timeout: int = 30,
    hide_window: bool = True
) -> Optional[str]:
    """
    Run a PowerShell command with profile isolation.

    Uses -NoProfile flag to prevent PowerShell profile from injecting
    unexpected text into the output (e.g., ASCII art banners, motd).

    Args:
        command: PowerShell command or script to execute
        timeout: Command timeout in seconds (default: 30)
        hide_window: Hide the PowerShell window on Windows (default: True)

    Returns:
        Cleaned command output with whitespace stripped, or None if execution fails

    Example:
        output = run_powershell("Get-Process | Select -First 1")
        data = extract_json(run_powershell("Get-Disk | ConvertTo-Json"))
    """
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if hide_window else 0

        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            creationflags=creation_flags,
            timeout=timeout
        )

        if result.returncode != 0:
            log.debug(f"PowerShell returned non-zero: {result.returncode}")
            log.debug(f"stderr: {result.stderr[:200] if result.stderr else 'none'}")
            return None

        output = result.stdout.strip()
        if not output:
            return None

        return output

    except subprocess.TimeoutExpired:
        log.debug(f"PowerShell command timed out after {timeout}s: {command[:50]}...")
        return None
    except FileNotFoundError:
        log.debug("PowerShell not found on this system")
        return None
    except Exception as e:
        log.debug(f"PowerShell execution failed: {e}")
        return None


def run_command(
    command: List[str],
    timeout: int = 30,
    hide_window: bool = True,
    env: Optional[dict] = None
) -> Optional[str]:
    """
    Run a shell command with output normalization.

    Args:
        command: Command and arguments as list (e.g., ["nvidia-smi", "--query-gpu=name"])
        timeout: Command timeout in seconds (default: 30)
        hide_window: Hide command window on Windows (default: True)
        env: Optional custom environment variables (default: inherit system env)

    Returns:
        Cleaned command output with whitespace stripped, or None if execution fails

    Example:
        output = run_command(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
        output = run_command(["sysctl", "-n", "hw.memsize"])
    """
    try:
        creation_flags = 0
        if hide_window and platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=creation_flags,
            timeout=timeout,
            env=env
        )

        if result.returncode != 0:
            log.debug(f"Command returned non-zero: {result.returncode}")
            return None

        output = result.stdout.strip()
        return output if output else None

    except subprocess.TimeoutExpired:
        log.debug(f"Command timed out after {timeout}s: {' '.join(command[:3])}...")
        return None
    except FileNotFoundError:
        log.debug(f"Command not found: {command[0]}")
        return None
    except Exception as e:
        log.debug(f"Command execution failed: {e}")
        return None


def extract_number(output: str) -> Optional[Union[int, float]]:
    """
    Extract a numeric value from command output.

    Handles cases where extra text might be in output (e.g., PowerShell
    profile messages, warnings, status lines) by finding lines that
    contain numeric values.

    Args:
        output: Command output string (may contain non-numeric text)

    Returns:
        Numeric value if found (int if whole number, float otherwise), None otherwise

    Example:
        # Handles: "Loading profile...\n16384\n"
        extract_number("Loading profile...\n16384\n")  # Returns 16384

        # Handles: "Value: 16.5 GB"
        extract_number("Value: 16.5 GB")  # Returns 16.5
    """
    if not output:
        return None

    # Try each line from the end (actual output usually at bottom)
    for line in reversed(output.strip().split('\n')):
        line = line.strip()

        # Try whole line as integer
        if line.isdigit():
            return int(line)

        # Try whole line as number (with possible comma separators)
        try:
            cleaned = line.replace(",", "")
            return float(cleaned) if '.' in cleaned else int(cleaned)
        except ValueError:
            pass

        # Try extracting number from line
        # Match integers or decimals, optionally negative
        match = re.search(r'[-+]?\d+\.?\d*', line)
        if match:
            value_str = match.group()
            try:
                return float(value_str) if '.' in value_str else int(value_str)
            except ValueError:
                continue

    return None


def extract_json(output: str) -> Optional[dict]:
    """
    Extract JSON object from command output.

    Handles cases where JSON may be mixed with other text (e.g., warnings,
    status messages, profile output).

    Args:
        output: Command output string containing JSON

    Returns:
        Parsed JSON dict if found, None otherwise

    Example:
        # Handles: "Loading...\n{\"key\": \"value\"}\nDone"
        extract_json('Loading...\n{"key": "value"}\nDone')  # Returns {"key": "value"}
    """
    if not output:
        return None

    # Find JSON object boundaries
    json_start = output.find('{')
    json_end = output.rfind('}') + 1

    if json_start == -1 or json_end <= json_start:
        return None

    try:
        json_str = output[json_start:json_end]
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        log.debug(f"JSON parse failed: {e}")
        return None


def extract_json_array(output: str) -> Optional[list]:
    """
    Extract JSON array from command output.

    Similar to extract_json but handles arrays instead of objects.

    Args:
        output: Command output string containing JSON array

    Returns:
        Parsed JSON list if found, None otherwise

    Example:
        extract_json_array('[{"id": 1}, {"id": 2}]')  # Returns [{"id": 1}, {"id": 2}]
    """
    if not output:
        return None

    # Find JSON array boundaries
    json_start = output.find('[')
    json_end = output.rfind(']') + 1

    if json_start == -1 or json_end <= json_start:
        return None

    try:
        json_str = output[json_start:json_end]
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        log.debug(f"JSON array parse failed: {e}")
        return None


def run_wmic(query: str, timeout: int = 10) -> Optional[str]:
    """
    Run a WMIC query on Windows.

    WMIC is deprecated but still widely available and doesn't have
    profile injection issues like PowerShell.

    Args:
        query: WMIC query (e.g., "ComputerSystem get TotalPhysicalMemory")
        timeout: Command timeout in seconds

    Returns:
        Query output (excluding header line), or None if execution fails

    Example:
        output = run_wmic("ComputerSystem get TotalPhysicalMemory")
        # Returns: "68501946368" (the value on second line)
    """
    if platform.system() != "Windows":
        return None

    try:
        result = subprocess.run(
            ["wmic"] + query.split(),
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=timeout
        )

        if result.returncode != 0:
            return None

        # WMIC output has header on first line, value on second
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            return lines[1].strip()

        return None

    except Exception as e:
        log.debug(f"WMIC query failed: {e}")
        return None
