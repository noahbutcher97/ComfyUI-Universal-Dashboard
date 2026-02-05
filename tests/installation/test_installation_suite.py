import unittest
from unittest.mock import patch, MagicMock, mock_open
import platform
import os
import sys
from src.services.dev_service import DevService
from src.services.system_service import SystemService

class TestInstallationSuite(unittest.TestCase):
    """
    Comprehensive Installation Test Suite.
    Verifies package integrity, dependency resolution, command generation,
    and post-install configuration for all supported tools.
    """

    def setUp(self):
        # Clear caches to ensure isolation
        DevService.get_system_tools_config.cache_clear()
        DevService.get_system_install_cmd.cache_clear()
        DevService.get_install_cmd.cache_clear()
        SystemService.check_dependency.cache_clear()

    def test_schema_integrity(self):
        """
        Verify every tool in resources.json has valid definitions for at least one OS.
        """
        config = DevService.get_system_tools_config()
        definitions = config.get("definitions", {})
        
        for tool_id, tool_def in definitions.items():
            with self.subTest(tool=tool_id):
                self.assertIn("name", tool_def)
                self.assertIn("install", tool_def)
                # Must have at least one OS support
                self.assertTrue(any(k in ["windows", "darwin", "linux"] for k in tool_def["install"].keys()),
                                f"Tool {tool_id} has no installation commands")

    @patch("platform.system", return_value="Windows")
    @patch("shutil.which", return_value="winget.exe")
    def test_command_generation_windows(self, mock_which, mock_system):
        """
        Verify correct install commands are generated for Windows.
        """
        # System Tools
        cmd_python = DevService.get_system_install_cmd("python")
        self.assertIn("winget", cmd_python)
        self.assertIn("--source", cmd_python, "Winget commands must specify source")
        
        # AI Tools (NPM)
        cmd_claude = DevService.get_install_cmd("claude", scope="system")
        self.assertEqual(cmd_claude, ["npm", "install", "-g", "@anthropic-ai/claude-code"])

    @patch("platform.system", return_value="Linux")
    def test_command_generation_linux(self, mock_system):
        """
        Verify Linux command generation logic.
        """
        # Rust (Curl)
        cmd_rust = DevService.get_system_install_cmd("rust")
        self.assertTrue(isinstance(cmd_rust, str) and "curl" in cmd_rust)
        
        # Pip Tool (User Scope)
        with patch("sys.prefix", "/usr"), patch("sys.base_prefix", "/usr"):
            cmd_hf = DevService.get_install_cmd("huggingface", scope="user")
            self.assertIn("--user", cmd_hf)

    @patch("src.services.system_service.SystemService.check_dependency", return_value=False)
    @patch("shutil.which", return_value=None)
    def test_dependency_gating(self, mock_which, mock_check_dep):
        """
        Verify that NPM tools report 'Not Installed' if Node/NPM is missing.
        """
        # Mock NPM missing
        self.assertFalse(DevService.is_installed("claude"))
        
        # Even if we try to check 'is_installed', it should verify NPM dependency first for npm types
        # (This logic is inside is_installed for npm types if binary check fails)

    @patch("platform.system", return_value="Windows")
    @patch.dict("os.environ", {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming", "PATH": "C:\\Windows"})
    @patch("subprocess.check_call")
    @patch("os.path.exists", return_value=True)
    def test_post_install_path_patching(self, mock_exists, mock_call, mock_system):
        """
        Verify add_to_system_path constructs correct PowerShell command.
        """
        # Test NPM tool
        success = DevService.add_to_system_path("claude")
        self.assertTrue(success)
        
        # Verify PowerShell command
        args = mock_call.call_args[0][0] # First arg is the command list
        ps_command = args[3] # ["powershell", ..., "-Command", CMD]
        
        self.assertIn("[Environment]::SetEnvironmentVariable", ps_command)
        self.assertIn("npm", ps_command)
        self.assertIn("User", ps_command)

    def test_full_matrix_generation(self):
        """
        Automated test generation for all AI tools.
        Ensures we can resolve commands for every AI tool in the DB.
        """
        providers = DevService.get_all_providers()
        for tool in providers:
            for os_name in ["Windows", "Darwin", "Linux"]:
                with self.subTest(tool=tool, os=os_name):
                    with patch("platform.system", return_value=os_name):
                        # Mock shutil.which for brew/winget detection
                        with patch("shutil.which", return_value="/bin/mock"):
                            cmd = DevService.get_install_cmd(tool)
                            self.assertIsNotNone(cmd, f"Failed to gen command for {tool} on {os_name}")

if __name__ == "__main__":
    unittest.main()
