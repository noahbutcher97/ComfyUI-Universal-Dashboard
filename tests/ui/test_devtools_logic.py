import unittest
from unittest.mock import MagicMock, patch
import tkinter
import customtkinter as ctk

# Mock Config Manager to avoid loading real files during UI init
with patch('src.config.manager.config_manager.load_config') as mock_load:
    mock_load.return_value = {}
    from src.ui.views.devtools import DevToolsFrame
    from src.services.system_service import SystemService

class TestDevToolsLogic(unittest.TestCase):
    """
    UI Logic Tests (ViewModel-style).
    Verifies that the UI state (enabled/disabled, text colors) reflects the underlying system state.
    """

    @classmethod
    def setUpClass(cls):
        # Initialize root for CTk
        cls.root = ctk.CTk()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        # Create a dummy app mock
        self.app_mock = MagicMock()
        # Create the frame (logic under test)
        self.frame = DevToolsFrame(self.root, self.app_mock)
        # Mock the widgets frame so we don't need to parse actual pack/grid
        self.frame.cli_widgets_frame = MagicMock()
        self.frame.cli_widgets_frame.winfo_children.return_value = []

    @patch.object(SystemService, 'verify_environment')
    @patch('src.services.dev_service.DevService.get_provider_config')
    def test_prerequisite_gating_logic(self, mock_get_conf, mock_env):
        """
        Critical UX Test: Verify that NPM-based AI tools are DISABLED if Node is missing.
        """
        # Scenario: Node.js is MISSING
        mock_env.return_value = {"npm": False}
        
        # Tool Config: Gemini CLI requires NPM
        mock_get_conf.return_value = {"package_type": "npm"}
        
        # Statuses: Gemini is NOT installed
        statuses = {"gemini": False}

        # Run the UI update logic
        # We need to spy on CTkCheckBox to see if it was created with state="disabled"
        with patch('customtkinter.CTkCheckBox') as MockCheckBox:
            self.frame._update_cli_list_ui(statuses)
            
            # Verify CheckBox was created
            self.assertTrue(MockCheckBox.called)
            
            # Verify 'disabled' state was set (since Node is missing)
            # The logic in _update_cli_list_ui: 
            #   chk = ctk.CTkCheckBox(...)
            #   if is_disabled: chk.configure(state="disabled")
            
            # Get the instance created
            checkbox_instance = MockCheckBox.return_value
            checkbox_instance.configure.assert_called_with(state="disabled")

    @patch.object(SystemService, 'verify_environment')
    @patch('src.services.dev_service.DevService.get_provider_config')
    def test_enabled_logic(self, mock_get_conf, mock_env):
        """
        Verify that NPM tools are ENABLED if Node is present.
        """
        # Scenario: Node.js is PRESENT
        mock_env.return_value = {"npm": True}
        mock_get_conf.return_value = {"package_type": "npm"}
        statuses = {"gemini": False}

        with patch('customtkinter.CTkCheckBox') as MockCheckBox:
            self.frame._update_cli_list_ui(statuses)
            
            checkbox_instance = MockCheckBox.return_value
            # configure(state="disabled") should NOT be called
            # (or called with "normal" if explicitly set, but code only sets disabled if blocked)
            
            # We explicitly check that the "disabled" call was NOT made
            calls = [c for c in checkbox_instance.configure.call_args_list if 'state' in c.kwargs and c.kwargs['state'] == 'disabled']
            self.assertEqual(len(calls), 0, "Tool should be enabled when prerequisites are met")

if __name__ == "__main__":
    unittest.main()
