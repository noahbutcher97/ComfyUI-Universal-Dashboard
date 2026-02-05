import unittest
from unittest.mock import patch, MagicMock
import platform
from src.services.dev_service import DevService

class TestInstallWorkflowIntegration(unittest.TestCase):
    """
    Integration Tests for the Tool Installation Workflow.
    Verifies the pipeline from 'User Request' -> 'Config Resolution' -> 'Command Generation'.
    """

    def setUp(self):
        try:
            DevService.get_install_cmd.cache_clear()
        except AttributeError:
            print("Warning: get_install_cmd has no cache_clear method.")

    @patch("platform.system")
    def test_npm_package_resolution(self, mock_system):
        """Ensure NPM packages resolve to 'npm install -g' correctly."""
        mock_system.return_value = "Windows"
        
        # Test Gemini CLI (which is an NPM package)
        cmd = DevService.get_install_cmd("gemini", scope="system")
        
        # Windows should NOT have sudo
        self.assertEqual(cmd, ["npm", "install", "-g", "@google/gemini-cli"],
                         "System install on Windows should just be npm install -g")

    @patch("platform.system")
    def test_pip_package_resolution_user_scope(self, mock_system):
        """Ensure Pip packages respect user scope logic."""
        mock_system.return_value = "Linux"
        
        # Huggingface (pip)
        # We need to simulate NOT being in a venv for --user to appear
        with patch("sys.prefix", "/usr"), patch("sys.base_prefix", "/usr"):
            cmd = DevService.get_install_cmd("huggingface", scope="user")
            # Should include --user
            self.assertIn("--user", cmd)
            self.assertIn("pip", cmd) # usually [sys.executable, -m, pip, ...]

    @patch("platform.system")
    def test_pip_package_resolution_venv(self, mock_system):
        """Ensure Pip packages inside venv DO NOT use --user."""
        mock_system.return_value = "Linux"
        
        # Simulate active venv (prefix != base_prefix)
        with patch("sys.prefix", "/home/user/venv"), patch("sys.base_prefix", "/usr"):
            cmd = DevService.get_install_cmd("huggingface", scope="user")
            self.assertNotIn("--user", cmd, "Should not use --user inside a venv")

    def test_unknown_provider_handling(self):
        """Ensure requesting an unknown provider returns empty list."""
        cmd = DevService.get_install_cmd("mystery_ai_tool", scope="user")
        self.assertEqual(cmd, [])

if __name__ == "__main__":
    unittest.main()
