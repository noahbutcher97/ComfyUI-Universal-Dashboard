"""
Unit tests for subprocess utilities.

Tests cover the I/O normalization utilities per ARCHITECTURE_PRINCIPLES.md:
- extract_number: Extracting numeric values from noisy output
- extract_json: Extracting JSON from mixed text
- run_powershell: PowerShell with profile isolation
- run_command: General command execution
"""

import pytest
from unittest.mock import patch, MagicMock
import subprocess

from src.utils.subprocess_utils import (
    extract_number,
    extract_json,
    extract_json_array,
    run_powershell,
    run_command,
    run_wmic,
)


class TestExtractNumber:
    """Tests for extract_number utility."""

    def test_simple_integer(self):
        """Should extract simple integer."""
        assert extract_number("16384") == 16384

    def test_simple_float(self):
        """Should extract float."""
        assert extract_number("16.5") == 16.5

    def test_integer_with_trailing_text(self):
        """Should extract number from line with text."""
        assert extract_number("Value: 16384 bytes") == 16384

    def test_multiline_with_noise(self):
        """Should extract number from noisy multiline output."""
        noisy_output = """Loading profile...
Welcome to PowerShell!
16384
Done."""
        assert extract_number(noisy_output) == 16384

    def test_number_at_end(self):
        """Should prefer numbers at end of output."""
        output = """First: 100
Second: 200
Final: 300"""
        assert extract_number(output) == 300

    def test_negative_number(self):
        """Should handle negative numbers."""
        assert extract_number("-42.5") == -42.5

    def test_comma_separated(self):
        """Should handle comma-separated thousands."""
        assert extract_number("16,384") == 16384

    def test_empty_input(self):
        """Should return None for empty input."""
        assert extract_number("") is None
        assert extract_number(None) is None

    def test_no_numbers(self):
        """Should return None when no numbers present."""
        assert extract_number("Hello World") is None


class TestExtractJson:
    """Tests for extract_json utility."""

    def test_simple_json(self):
        """Should extract simple JSON object."""
        result = extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        """Should extract JSON from mixed text."""
        text = 'Loading...\n{"type": "DDR5", "speed": 6400}\nDone'
        result = extract_json(text)
        assert result == {"type": "DDR5", "speed": 6400}

    def test_nested_json(self):
        """Should handle nested JSON objects."""
        text = '{"outer": {"inner": 42}}'
        result = extract_json(text)
        assert result == {"outer": {"inner": 42}}

    def test_json_with_powershell_profile_output(self):
        """Should extract JSON from PowerShell profile noise."""
        noisy_output = """
==================================
  Welcome to PowerShell 7.4.1
==================================
{"MediaType": "SSD", "BusType": "NVMe"}
Goodbye!
"""
        result = extract_json(noisy_output)
        assert result == {"MediaType": "SSD", "BusType": "NVMe"}

    def test_empty_input(self):
        """Should return None for empty input."""
        assert extract_json("") is None
        assert extract_json(None) is None

    def test_no_json(self):
        """Should return None when no JSON present."""
        assert extract_json("Hello World") is None

    def test_malformed_json(self):
        """Should return None for malformed JSON."""
        assert extract_json('{"key": invalid}') is None


class TestExtractJsonArray:
    """Tests for extract_json_array utility."""

    def test_simple_array(self):
        """Should extract simple JSON array."""
        result = extract_json_array('[{"id": 1}, {"id": 2}]')
        assert result == [{"id": 1}, {"id": 2}]

    def test_array_with_text(self):
        """Should extract array from mixed text."""
        text = 'Results:\n[1, 2, 3]\nEnd'
        result = extract_json_array(text)
        assert result == [1, 2, 3]

    def test_empty_input(self):
        """Should return None for empty input."""
        assert extract_json_array("") is None
        assert extract_json_array(None) is None


class TestRunPowershell:
    """Tests for run_powershell utility."""

    @patch('subprocess.run')
    def test_uses_no_profile(self, mock_run):
        """Should use -NoProfile flag to prevent profile injection."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr=""
        )

        run_powershell("Get-Process")

        # Verify -NoProfile was passed
        args = mock_run.call_args[0][0]
        assert "-NoProfile" in args

    @patch('subprocess.run')
    def test_returns_stripped_output(self, mock_run):
        """Should return stripped output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  output with whitespace  \n",
            stderr=""
        )

        result = run_powershell("Get-Process")
        assert result == "output with whitespace"

    @patch('subprocess.run')
    def test_returns_none_on_error(self, mock_run):
        """Should return None on non-zero exit code."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error"
        )

        result = run_powershell("Bad-Command")
        assert result is None

    @patch('subprocess.run')
    def test_handles_timeout(self, mock_run):
        """Should return None on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

        result = run_powershell("Long-Command", timeout=1)
        assert result is None

    @patch('subprocess.run')
    def test_handles_file_not_found(self, mock_run):
        """Should return None when PowerShell not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = run_powershell("Get-Process")
        assert result is None


class TestRunCommand:
    """Tests for run_command utility."""

    @patch('subprocess.run')
    def test_returns_output(self, mock_run):
        """Should return command output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="command output\n",
            stderr=""
        )

        result = run_command(["echo", "test"])
        assert result == "command output"

    @patch('subprocess.run')
    def test_returns_none_on_error(self, mock_run):
        """Should return None on non-zero exit code."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error"
        )

        result = run_command(["false"])
        assert result is None

    @patch('subprocess.run')
    def test_handles_missing_command(self, mock_run):
        """Should return None for missing command."""
        mock_run.side_effect = FileNotFoundError()

        result = run_command(["nonexistent-command"])
        assert result is None


class TestRunWmic:
    """Tests for run_wmic utility."""

    @patch('platform.system', return_value='Linux')
    def test_returns_none_on_non_windows(self, mock_platform):
        """Should return None on non-Windows systems."""
        result = run_wmic("ComputerSystem get TotalPhysicalMemory")
        assert result is None

    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_returns_value_line(self, mock_run, mock_platform):
        """Should return second line (value) from WMIC output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="TotalPhysicalMemory\n68501946368\n",
            stderr=""
        )

        result = run_wmic("ComputerSystem get TotalPhysicalMemory")
        assert result == "68501946368"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
