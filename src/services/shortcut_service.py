"""
Shortcut service for creating desktop shortcuts across platforms.

Per SPEC_v3 Section 11.5: Create desktop shortcuts across platforms.
Supports Windows (.lnk/.bat), macOS (.command), and Linux (.desktop).
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from src.utils.logger import log


class ShortcutError(Exception):
    """Base exception for shortcut creation failures."""
    pass


class ShortcutPermissionError(ShortcutError):
    """Raised when lacking permissions to create shortcut."""
    pass


@dataclass
class ShortcutSpec:
    """
    Specification for a desktop shortcut.

    Per SPEC_v3 Section 11.5: Shortcut configuration dataclass.
    """
    name: str                           # Display name of the shortcut
    target: str                         # Target executable or script
    arguments: str = ""                 # Command line arguments
    working_dir: Optional[str] = None   # Working directory
    icon: Optional[str] = None          # Icon path (platform-specific)
    dest: Optional[str] = None          # Destination folder (defaults to Desktop)


@dataclass
class ShortcutResult:
    """Result of shortcut creation operation."""
    success: bool
    path: Optional[Path] = None
    error: Optional[str] = None


class ShortcutService:
    """
    Creates OS-appropriate desktop shortcuts/launchers.

    Per SPEC_v3 Section 11.5:
    - Windows: .lnk (preferred) or .bat (fallback)
    - macOS: .command script
    - Linux: .desktop file

    Per ARCHITECTURE_PRINCIPLES: Explicit failure, proper logging.
    """

    @staticmethod
    def get_desktop_path() -> Path:
        """
        Returns path to user's Desktop folder.

        Returns:
            Path to desktop folder

        Raises:
            ShortcutError: If desktop path cannot be determined
        """
        system = platform.system()

        try:
            if system == "Windows":
                desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
            elif system == "Darwin":
                desktop = Path.home() / "Desktop"
            else:
                # Linux - check XDG first, fallback to ~/Desktop
                xdg_desktop = os.environ.get("XDG_DESKTOP_DIR")
                if xdg_desktop:
                    desktop = Path(xdg_desktop)
                else:
                    desktop = Path.home() / "Desktop"

            if not desktop.exists():
                log.warning(f"Desktop path does not exist: {desktop}")
                # Don't create it - let caller handle missing desktop

            return desktop

        except Exception as e:
            log.error(f"Failed to determine desktop path: {e}")
            raise ShortcutError(f"Cannot determine desktop path: {e}")

    @staticmethod
    def create_shortcut(
        name: str,
        command: str,
        working_dir: Optional[str] = None,
        icon_path: Optional[str] = None,
        destination: Optional[Path] = None
    ) -> Path:
        """
        Create a desktop shortcut (synchronous).

        Args:
            name: Display name for the shortcut
            command: Command to execute (full path or relative)
            working_dir: Working directory for the command
            icon_path: Path to icon file (optional)
            destination: Destination folder (defaults to Desktop)

        Returns:
            Path to created shortcut

        Raises:
            ShortcutError: If shortcut creation fails
            ShortcutPermissionError: If lacking write permissions
        """
        dest = destination or ShortcutService.get_desktop_path()

        # Ensure destination exists
        if not dest.exists():
            try:
                dest.mkdir(parents=True, exist_ok=True)
                log.debug(f"Created destination directory: {dest}")
            except PermissionError as e:
                raise ShortcutPermissionError(f"Cannot create destination: {e}")
            except OSError as e:
                raise ShortcutError(f"Failed to create destination: {e}")

        system = platform.system()

        try:
            if system == "Windows":
                return ShortcutService._create_windows_shortcut(
                    name, command, working_dir, icon_path, dest
                )
            elif system == "Darwin":
                return ShortcutService._create_mac_shortcut(
                    name, command, working_dir, icon_path, dest
                )
            else:
                return ShortcutService._create_linux_shortcut(
                    name, command, working_dir, icon_path, dest
                )
        except ShortcutError:
            raise
        except Exception as e:
            log.error(f"Shortcut creation failed: {e}")
            raise ShortcutError(f"Failed to create shortcut: {e}")

    @staticmethod
    def create_from_spec(spec: ShortcutSpec) -> ShortcutResult:
        """
        Create a shortcut from a ShortcutSpec.

        Per SPEC_v3 Section 11.5: Preferred method for shortcut creation.

        Args:
            spec: ShortcutSpec containing shortcut configuration

        Returns:
            ShortcutResult with success status and path
        """
        try:
            dest = Path(spec.dest) if spec.dest else None

            # Build command from target and arguments
            command = spec.target
            if spec.arguments:
                command = f"{spec.target} {spec.arguments}"

            path = ShortcutService.create_shortcut(
                name=spec.name,
                command=command,
                working_dir=spec.working_dir,
                icon_path=spec.icon,
                destination=dest
            )

            log.info(f"Created shortcut: {path}")
            return ShortcutResult(success=True, path=path)

        except ShortcutError as e:
            log.error(f"Shortcut creation failed for {spec.name}: {e}")
            return ShortcutResult(success=False, error=str(e))
        except Exception as e:
            log.error(f"Unexpected error creating shortcut {spec.name}: {e}")
            return ShortcutResult(success=False, error=str(e))

    @staticmethod
    def _create_windows_shortcut(
        name: str,
        command: str,
        working_dir: Optional[str],
        icon_path: Optional[str],
        dest_dir: Path
    ) -> Path:
        """
        Create Windows shortcut.

        Attempts to create .lnk file using pywin32 if available,
        falls back to .bat file otherwise.
        """
        # Try to create proper .lnk shortcut using pywin32
        try:
            from win32com.client import Dispatch

            shortcut_path = dest_dir / f"{name}.lnk"

            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(shortcut_path))

            # Parse command to extract executable and arguments
            parts = command.split(maxsplit=1)
            shortcut.Targetpath = parts[0]
            if len(parts) > 1:
                shortcut.Arguments = parts[1]

            if working_dir:
                shortcut.WorkingDirectory = working_dir
            if icon_path:
                shortcut.IconLocation = icon_path

            shortcut.save()
            log.debug(f"Created Windows .lnk shortcut: {shortcut_path}")
            return shortcut_path

        except ImportError:
            log.debug("pywin32 not available, falling back to .bat file")
        except Exception as e:
            log.warning(f"Failed to create .lnk, falling back to .bat: {e}")

        # Fallback to .bat file
        shortcut_path = dest_dir / f"{name}.bat"

        content = "@echo off\n"
        content += f"title {name}\n"
        if working_dir:
            content += f'cd /d "{working_dir}"\n'
        content += f"{command}\n"
        content += "if %ERRORLEVEL% NEQ 0 pause\n"

        try:
            with open(shortcut_path, "w", encoding="utf-8") as f:
                f.write(content)
            log.debug(f"Created Windows .bat shortcut: {shortcut_path}")
            return shortcut_path
        except PermissionError as e:
            raise ShortcutPermissionError(f"Cannot write to {shortcut_path}: {e}")
        except OSError as e:
            raise ShortcutError(f"Failed to write shortcut: {e}")

    @staticmethod
    def _create_mac_shortcut(
        name: str,
        command: str,
        working_dir: Optional[str],
        icon_path: Optional[str],
        dest_dir: Path
    ) -> Path:
        """
        Create macOS .command script.

        Per SPEC_v3: Remove quarantine attribute for smooth execution.
        """
        shortcut_path = dest_dir / f"{name}.command"

        content = "#!/bin/bash\n"
        content += f"# {name} - Created by AI Universal Suite\n\n"

        if working_dir:
            content += f'cd "{working_dir}"\n'

        content += f"{command}\n"

        try:
            with open(shortcut_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Make executable
            os.chmod(shortcut_path, 0o755)

            # Remove quarantine attribute for seamless execution
            try:
                subprocess.run(
                    ["xattr", "-d", "com.apple.quarantine", str(shortcut_path)],
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                log.debug("Could not remove quarantine attribute (non-critical)")

            log.debug(f"Created macOS .command shortcut: {shortcut_path}")
            return shortcut_path

        except PermissionError as e:
            raise ShortcutPermissionError(f"Cannot write to {shortcut_path}: {e}")
        except OSError as e:
            raise ShortcutError(f"Failed to write shortcut: {e}")

    @staticmethod
    def _create_linux_shortcut(
        name: str,
        command: str,
        working_dir: Optional[str],
        icon_path: Optional[str],
        dest_dir: Path
    ) -> Path:
        """
        Create Linux .desktop file.

        Per freedesktop.org Desktop Entry Specification.
        """
        shortcut_path = dest_dir / f"{name}.desktop"

        # Escape special characters in Exec value
        exec_command = command.replace("\\", "\\\\").replace('"', '\\"')

        content = "[Desktop Entry]\n"
        content += "Type=Application\n"
        content += f"Name={name}\n"
        content += f"Exec={exec_command}\n"
        content += "Terminal=true\n"
        content += "Categories=Utility;\n"

        if working_dir:
            content += f"Path={working_dir}\n"
        if icon_path:
            content += f"Icon={icon_path}\n"

        try:
            with open(shortcut_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Make executable (required for .desktop files)
            os.chmod(shortcut_path, 0o755)

            # Try to update desktop database for icon refresh
            try:
                subprocess.run(
                    ["update-desktop-database", str(dest_dir)],
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass  # Not critical if this fails

            log.debug(f"Created Linux .desktop shortcut: {shortcut_path}")
            return shortcut_path

        except PermissionError as e:
            raise ShortcutPermissionError(f"Cannot write to {shortcut_path}: {e}")
        except OSError as e:
            raise ShortcutError(f"Failed to write shortcut: {e}")

    @staticmethod
    def remove_shortcut(name: str, destination: Optional[Path] = None) -> bool:
        """
        Remove a previously created shortcut.

        Args:
            name: Name of the shortcut (without extension)
            destination: Folder containing the shortcut (defaults to Desktop)

        Returns:
            True if shortcut was removed, False if not found
        """
        dest = destination or ShortcutService.get_desktop_path()
        system = platform.system()

        # Determine possible extensions
        if system == "Windows":
            extensions = [".lnk", ".bat"]
        elif system == "Darwin":
            extensions = [".command"]
        else:
            extensions = [".desktop"]

        removed = False
        for ext in extensions:
            shortcut_path = dest / f"{name}{ext}"
            if shortcut_path.exists():
                try:
                    shortcut_path.unlink()
                    log.info(f"Removed shortcut: {shortcut_path}")
                    removed = True
                except OSError as e:
                    log.warning(f"Failed to remove {shortcut_path}: {e}")

        return removed

    @staticmethod
    def shortcut_exists(name: str, destination: Optional[Path] = None) -> bool:
        """
        Check if a shortcut exists.

        Args:
            name: Name of the shortcut (without extension)
            destination: Folder to check (defaults to Desktop)

        Returns:
            True if shortcut exists
        """
        dest = destination or ShortcutService.get_desktop_path()
        system = platform.system()

        if system == "Windows":
            extensions = [".lnk", ".bat"]
        elif system == "Darwin":
            extensions = [".command"]
        else:
            extensions = [".desktop"]

        return any((dest / f"{name}{ext}").exists() for ext in extensions)
