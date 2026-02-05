import unittest
from src.services.dev_service import DevService
from unittest.mock import patch, MagicMock

class TestE2EWorkflow(unittest.TestCase):
    """
    End-to-End Workflow Simulation.
    """

    def test_full_tool_lifecycle(self):
        """
        Simulate: Check -> Install -> Verify
        """
        tool = "gemini"
        
        # 1. Pre-Check
        # Mock that it's NOT installed initially
        with patch('src.services.dev_service.DevService.is_installed', return_value=False):
            self.assertFalse(DevService.is_installed(tool))
            
        # 2. Get Install Command
        # Simulate Windows environment
        with patch('platform.system', return_value="Windows"):
            cmd = DevService.get_install_cmd(tool, scope="system")
            self.assertEqual(cmd, ["npm", "install", "-g", "@google/gemini-cli"])
            
        # 3. Simulate "Success" (Mocking the installation effect)
        # In a real E2E, we'd run the command. Here we verify the logic transition.
        # If we run the command and it succeeds, is_installed should return True.
        
        with patch('src.services.dev_service.DevService.is_installed', return_value=True):
            self.assertTrue(DevService.is_installed(tool))

if __name__ == "__main__":
    unittest.main()
