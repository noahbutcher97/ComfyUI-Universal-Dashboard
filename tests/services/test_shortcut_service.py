"""
Tests for ShortcutService.

Per SPEC_v3 Section 11.5: Create desktop shortcuts across platforms.
"""

import os
import platform
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Generator

import pytest

from src.services.shortcut_service import (
    ShortcutService,
    ShortcutSpec,
    ShortcutResult,
    ShortcutError,
    ShortcutPermissionError,
)


class TestShortcutSpec:
    """Tests for ShortcutSpec dataclass."""

    def test_shortcut_spec_required_fields(self) -> None:
        """ShortcutSpec requires name and target."""
        spec = ShortcutSpec(name="My App", target="/usr/bin/myapp")
        assert spec.name == "My App"
        assert spec.target == "/usr/bin/myapp"

    def test_shortcut_spec_defaults(self) -> None:
        """ShortcutSpec should have sensible defaults."""
        spec = ShortcutSpec(name="Test", target="/bin/test")
        assert spec.arguments == ""
        assert spec.working_dir is None
        assert spec.icon is None
        assert spec.dest is None

    def test_shortcut_spec_full(self) -> None:
        """ShortcutSpec should accept all fields."""
        spec = ShortcutSpec(
            name="ComfyUI",
            target="python",
            arguments="main.py --port 8188",
            working_dir="/home/user/ComfyUI",
            icon="/path/to/icon.png",
            dest="/home/user/Desktop"
        )
        assert spec.arguments == "main.py --port 8188"
        assert spec.working_dir == "/home/user/ComfyUI"
        assert spec.icon == "/path/to/icon.png"
        assert spec.dest == "/home/user/Desktop"


class TestShortcutResult:
    """Tests for ShortcutResult dataclass."""

    def test_shortcut_result_success(self) -> None:
        """ShortcutResult captures successful creation."""
        result = ShortcutResult(success=True, path=Path("/Desktop/App.command"))
        assert result.success is True
        assert result.path == Path("/Desktop/App.command")
        assert result.error is None

    def test_shortcut_result_failure(self) -> None:
        """ShortcutResult captures failures."""
        result = ShortcutResult(success=False, error="Permission denied")
        assert result.success is False
        assert result.path is None
        assert result.error == "Permission denied"


class TestExceptions:
    """Test custom exception classes."""

    def test_shortcut_error(self) -> None:
        """ShortcutError should be base exception."""
        error = ShortcutError("Creation failed")
        assert str(error) == "Creation failed"
        assert isinstance(error, Exception)

    def test_shortcut_permission_error(self) -> None:
        """ShortcutPermissionError inherits from ShortcutError."""
        error = ShortcutPermissionError("Access denied")
        assert isinstance(error, ShortcutError)


class TestGetDesktopPath:
    """Tests for desktop path detection."""

    def test_windows_desktop_path(self) -> None:
        """Windows should use USERPROFILE/Desktop."""
        with patch('platform.system', return_value='Windows'):
            with patch.dict(os.environ, {'USERPROFILE': 'C:\\Users\\TestUser'}):
                with patch.object(Path, 'exists', return_value=True):
                    desktop = ShortcutService.get_desktop_path()
                    assert str(desktop) == 'C:\\Users\\TestUser\\Desktop'

    def test_macos_desktop_path(self) -> None:
        """macOS should use ~/Desktop."""
        with patch('platform.system', return_value='Darwin'):
            with patch.object(Path, 'home', return_value=Path('/Users/testuser')):
                with patch.object(Path, 'exists', return_value=True):
                    desktop = ShortcutService.get_desktop_path()
                    assert desktop == Path('/Users/testuser/Desktop')

    def test_linux_xdg_desktop_path(self) -> None:
        """Linux should check XDG_DESKTOP_DIR first."""
        with patch('platform.system', return_value='Linux'):
            with patch.dict(os.environ, {'XDG_DESKTOP_DIR': '/custom/desktop'}):
                with patch.object(Path, 'exists', return_value=True):
                    desktop = ShortcutService.get_desktop_path()
                    assert desktop == Path('/custom/desktop')

    def test_linux_fallback_desktop_path(self) -> None:
        """Linux should fall back to ~/Desktop if XDG not set."""
        with patch('platform.system', return_value='Linux'):
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(Path, 'home', return_value=Path('/home/user')):
                    with patch.object(Path, 'exists', return_value=True):
                        desktop = ShortcutService.get_desktop_path()
                        assert desktop == Path('/home/user/Desktop')


class TestWindowsShortcuts:
    """Tests for Windows shortcut creation."""

    def test_windows_bat_fallback(self) -> None:
        """Windows should create .bat when pywin32 unavailable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            # Simulate ImportError for win32com
            with patch.dict('sys.modules', {'win32com': None, 'win32com.client': None}):
                path = ShortcutService._create_windows_shortcut(
                    name="TestApp",
                    command="python main.py",
                    working_dir="C:\\Apps\\TestApp",
                    icon_path=None,
                    dest_dir=dest
                )

            assert path.suffix == ".bat"
            assert path.exists()

            content = path.read_text()
            assert "@echo off" in content
            assert "title TestApp" in content
            assert 'cd /d "C:\\Apps\\TestApp"' in content
            assert "python main.py" in content

    def test_windows_bat_error_pause(self) -> None:
        """Windows .bat should pause on error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            with patch.dict('sys.modules', {'win32com': None, 'win32com.client': None}):
                path = ShortcutService._create_windows_shortcut(
                    name="Test",
                    command="test.exe",
                    working_dir=None,
                    icon_path=None,
                    dest_dir=dest
                )

            content = path.read_text()
            assert "if %ERRORLEVEL% NEQ 0 pause" in content


class TestMacOSShortcuts:
    """Tests for macOS shortcut creation."""

    def test_macos_command_creation(self) -> None:
        """macOS should create .command file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            with patch('subprocess.run') as mock_run:
                path = ShortcutService._create_mac_shortcut(
                    name="ComfyUI",
                    command="python main.py",
                    working_dir="/Users/test/ComfyUI",
                    icon_path=None,
                    dest_dir=dest
                )

            assert path.suffix == ".command"
            assert path.exists()

            content = path.read_text()
            assert "#!/bin/bash" in content
            assert 'cd "/Users/test/ComfyUI"' in content
            assert "python main.py" in content

    def test_macos_executable_permissions(self) -> None:
        """macOS .command should be executable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            with patch('subprocess.run'):
                path = ShortcutService._create_mac_shortcut(
                    name="Test",
                    command="./run.sh",
                    working_dir=None,
                    icon_path=None,
                    dest_dir=dest
                )

            # Check executable bit - on Windows os.chmod is a no-op for execute bit
            # but the .command file is still created correctly
            if platform.system() != "Windows":
                mode = path.stat().st_mode
                assert mode & 0o100  # Owner execute on Unix
            else:
                # On Windows, .command files wouldn't run natively anyway
                # Just verify the file was created
                assert path.exists()

    def test_macos_quarantine_removal(self) -> None:
        """macOS should attempt to remove quarantine attribute."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            with patch('subprocess.run') as mock_run:
                ShortcutService._create_mac_shortcut(
                    name="Test",
                    command="./run.sh",
                    working_dir=None,
                    icon_path=None,
                    dest_dir=dest
                )

            # Verify xattr was called
            xattr_calls = [
                call for call in mock_run.call_args_list
                if 'xattr' in str(call)
            ]
            assert len(xattr_calls) > 0


class TestLinuxShortcuts:
    """Tests for Linux shortcut creation."""

    def test_linux_desktop_creation(self) -> None:
        """Linux should create .desktop file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            with patch('subprocess.run'):
                path = ShortcutService._create_linux_shortcut(
                    name="ComfyUI",
                    command="python main.py --port 8188",
                    working_dir="/home/user/ComfyUI",
                    icon_path="/usr/share/icons/comfy.png",
                    dest_dir=dest
                )

            assert path.suffix == ".desktop"
            assert path.exists()

            content = path.read_text()
            assert "[Desktop Entry]" in content
            assert "Type=Application" in content
            assert "Name=ComfyUI" in content
            assert "Exec=python main.py --port 8188" in content
            assert "Path=/home/user/ComfyUI" in content
            assert "Icon=/usr/share/icons/comfy.png" in content
            assert "Terminal=true" in content

    def test_linux_executable_permissions(self) -> None:
        """Linux .desktop should be executable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            with patch('subprocess.run'):
                path = ShortcutService._create_linux_shortcut(
                    name="Test",
                    command="./run.sh",
                    working_dir=None,
                    icon_path=None,
                    dest_dir=dest
                )

            # Check executable bit - on Windows os.chmod is a no-op for execute bit
            if platform.system() != "Windows":
                mode = path.stat().st_mode
                assert mode & 0o100  # Owner execute on Unix
            else:
                # On Windows, .desktop files wouldn't run natively anyway
                # Just verify the file was created with correct content
                assert path.exists()
                assert "[Desktop Entry]" in path.read_text()

    def test_linux_special_char_escaping(self) -> None:
        """Linux should escape special characters in Exec."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            with patch('subprocess.run'):
                path = ShortcutService._create_linux_shortcut(
                    name="Test",
                    command='echo "hello world"',
                    working_dir=None,
                    icon_path=None,
                    dest_dir=dest
                )

            content = path.read_text()
            # Quotes should be escaped
            assert 'Exec=echo \\"hello world\\"' in content


class TestCreateFromSpec:
    """Tests for create_from_spec method."""

    def test_create_from_spec_success(self) -> None:
        """create_from_spec should return ShortcutResult on success."""
        with tempfile.TemporaryDirectory() as temp_dir:
            spec = ShortcutSpec(
                name="TestApp",
                target="python",
                arguments="main.py",
                dest=temp_dir
            )

            with patch('platform.system', return_value='Linux'):
                with patch('subprocess.run'):
                    result = ShortcutService.create_from_spec(spec)

            assert result.success is True
            assert result.path is not None
            assert result.error is None

    def test_create_from_spec_failure(self) -> None:
        """create_from_spec should capture errors."""
        spec = ShortcutSpec(
            name="TestApp",
            target="python",
            dest="/nonexistent/path/that/doesnt/exist"
        )

        # Force failure by using non-writable directory
        with patch.object(ShortcutService, 'create_shortcut',
                         side_effect=ShortcutError("Test error")):
            result = ShortcutService.create_from_spec(spec)

        assert result.success is False
        assert result.error is not None
        assert "Test error" in result.error


class TestRemoveShortcut:
    """Tests for remove_shortcut method."""

    def test_remove_existing_shortcut(self) -> None:
        """remove_shortcut should delete existing shortcut."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            # Create a shortcut first
            with patch('platform.system', return_value='Linux'):
                with patch('subprocess.run'):
                    path = ShortcutService.create_shortcut(
                        name="ToRemove",
                        command="test",
                        destination=dest
                    )

            assert path.exists()

            # Remove it
            with patch('platform.system', return_value='Linux'):
                removed = ShortcutService.remove_shortcut("ToRemove", dest)

            assert removed is True
            assert not path.exists()

    def test_remove_nonexistent_shortcut(self) -> None:
        """remove_shortcut should return False if not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            with patch('platform.system', return_value='Linux'):
                removed = ShortcutService.remove_shortcut("NonExistent", dest)

            assert removed is False


class TestShortcutExists:
    """Tests for shortcut_exists method."""

    def test_shortcut_exists_true(self) -> None:
        """shortcut_exists returns True for existing shortcut."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            with patch('platform.system', return_value='Linux'):
                with patch('subprocess.run'):
                    ShortcutService.create_shortcut(
                        name="Existing",
                        command="test",
                        destination=dest
                    )

            with patch('platform.system', return_value='Linux'):
                exists = ShortcutService.shortcut_exists("Existing", dest)

            assert exists is True

    def test_shortcut_exists_false(self) -> None:
        """shortcut_exists returns False for non-existing shortcut."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            with patch('platform.system', return_value='Linux'):
                exists = ShortcutService.shortcut_exists("NonExistent", dest)

            assert exists is False


class TestCrossplatformBehavior:
    """Tests for cross-platform consistency."""

    @pytest.mark.parametrize("system,extension", [
        ("Windows", ".bat"),  # .bat fallback without pywin32
        ("Darwin", ".command"),
        ("Linux", ".desktop"),
    ])
    def test_platform_extensions(self, system: str, extension: str) -> None:
        """Each platform should use correct extension."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            with patch('platform.system', return_value=system):
                with patch('subprocess.run'):
                    # Simulate no pywin32 on Windows
                    if system == "Windows":
                        with patch.dict('sys.modules',
                                       {'win32com': None, 'win32com.client': None}):
                            path = ShortcutService.create_shortcut(
                                name="Test",
                                command="test",
                                destination=dest
                            )
                    else:
                        path = ShortcutService.create_shortcut(
                            name="Test",
                            command="test",
                            destination=dest
                        )

            assert path.suffix == extension

    def test_working_dir_handling(self) -> None:
        """Working directory should be respected on all platforms."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            for system in ["Windows", "Darwin", "Linux"]:
                with patch('platform.system', return_value=system):
                    with patch('subprocess.run'):
                        if system == "Windows":
                            with patch.dict('sys.modules',
                                           {'win32com': None, 'win32com.client': None}):
                                path = ShortcutService.create_shortcut(
                                    name=f"Test_{system}",
                                    command="test",
                                    working_dir="/custom/path",
                                    destination=dest
                                )
                        else:
                            path = ShortcutService.create_shortcut(
                                name=f"Test_{system}",
                                command="test",
                                working_dir="/custom/path",
                                destination=dest
                            )

                content = path.read_text()
                assert "/custom/path" in content
