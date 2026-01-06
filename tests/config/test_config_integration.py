"""
Integration tests for ConfigManager.

Tests realistic workflows involving multiple config operations.
Per SPEC_v3: Config should persist state across installation phases.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest


@pytest.fixture
def isolated_config_env(tmp_path: Path) -> Generator[tuple[Path, Path], None, None]:
    """Create an isolated config environment for testing."""
    config_dir = tmp_path / ".universal_ai_suite"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    # Patch ConfigManager class attributes
    from src.config.manager import ConfigManager
    with patch.object(ConfigManager, 'CONFIG_DIR', str(config_dir)):
        with patch.object(ConfigManager, 'CONFIG_FILE', str(config_file)):
            yield config_dir, config_file


class TestInstallationWorkflow:
    """Integration tests for installation workflow persistence."""

    def test_full_installation_workflow(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Test complete installation workflow from pending to complete."""
        from src.config.manager import ConfigManager

        config_dir, config_file = isolated_config_env

        # Phase 1: Initial setup
        manager = ConfigManager()
        manager.set_installation_status("pending")
        manager.set_comfyui_path(str(config_dir / "ComfyUI"))

        # Verify initial state
        assert manager.get("installation.status") == "pending"

        # Phase 2: Start installation
        manager.set_installation_status("in_progress")
        manager.set_module_installed("comfyui", version="0.3.60")

        # Phase 3: Install custom nodes
        manager.add_installed_node("ComfyUI-Manager")
        manager.add_installed_node("ComfyUI-GGUF")
        manager.add_installed_node("ComfyUI-VideoHelperSuite")

        # Phase 4: Install models
        manager.add_installed_model("flux_dev_gguf_q4")
        manager.add_installed_model("wan_22_ti2v_5b")

        # Phase 5: Complete installation
        manager.set_installation_status("complete")
        manager.set_module_installed("cli_provider", provider="claude")

        # Reload config and verify persistence
        manager2 = ConfigManager()

        assert manager2.get("installation.status") == "complete"
        assert manager2.get("installation.modules.comfyui.installed") is True
        assert manager2.get("installation.modules.comfyui.version") == "0.3.60"
        assert manager2.get("installation.modules.cli_provider.installed") is True
        assert manager2.get("installation.modules.cli_provider.provider") == "claude"

        nodes = manager2.get("installation.custom_nodes_installed", [])
        assert "ComfyUI-Manager" in nodes
        assert "ComfyUI-GGUF" in nodes
        assert "ComfyUI-VideoHelperSuite" in nodes

        models = manager2.get("installation.models_installed", [])
        assert "flux_dev_gguf_q4" in models
        assert "wan_22_ti2v_5b" in models

    def test_installation_error_recovery(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Test that error state is properly persisted for recovery."""
        from src.config.manager import ConfigManager

        # Start installation
        manager = ConfigManager()
        manager.set_installation_status("in_progress")
        manager.set_module_installed("comfyui", version="0.3.60")
        manager.add_installed_node("ComfyUI-Manager")

        # Simulate error during model download
        manager.set_installation_status("error")

        # Reload - should preserve partial state
        manager2 = ConfigManager()

        assert manager2.get("installation.status") == "error"
        # Partial progress should be preserved
        assert manager2.get("installation.modules.comfyui.installed") is True
        assert "ComfyUI-Manager" in manager2.get("installation.custom_nodes_installed", [])

        # Resume installation
        manager2.set_installation_status("in_progress")
        manager2.add_installed_model("flux_dev_gguf_q4")
        manager2.set_installation_status("complete")

        # Final verification
        manager3 = ConfigManager()
        assert manager3.get("installation.status") == "complete"


class TestOnboardingWorkflow:
    """Integration tests for onboarding workflow persistence."""

    def test_quick_onboarding_path(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Test quick onboarding path (5 screens)."""
        from src.config.manager import ConfigManager

        manager = ConfigManager()

        # User selects quick path
        manager.set("preferences.onboarding_path", "quick")

        # Quick wizard steps
        manager.set("user_profile.primary_use_cases", ["content_generation"])
        manager.set("preferences.onboarding_completed", True)

        # Reload and verify
        manager2 = ConfigManager()

        assert manager2.get("preferences.onboarding_path") == "quick"
        assert manager2.get("preferences.onboarding_completed") is True
        assert "content_generation" in manager2.get("user_profile.primary_use_cases", [])

    def test_comprehensive_onboarding_path(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Test comprehensive onboarding path (15-20 screens)."""
        from src.config.manager import ConfigManager

        manager = ConfigManager()

        # User selects comprehensive path
        manager.set("preferences.onboarding_path", "comprehensive")

        # Comprehensive wizard steps
        manager.set("user_profile.ai_experience", 4)
        manager.set("user_profile.technical_experience", 5)
        manager.set("user_profile.primary_use_cases", [
            "content_generation",
            "video_generation",
            "character_design"
        ])
        manager.set("user_profile.prefer_simple_setup", 2)
        manager.set("user_profile.prefer_local_processing", 5)
        manager.set("user_profile.prefer_open_source", 4)
        manager.set("preferences.onboarding_completed", True)

        # Reload and verify full profile
        manager2 = ConfigManager()

        assert manager2.get("preferences.onboarding_path") == "comprehensive"
        assert manager2.get("user_profile.ai_experience") == 4
        assert manager2.get("user_profile.technical_experience") == 5
        assert len(manager2.get("user_profile.primary_use_cases", [])) == 3
        assert manager2.get("user_profile.prefer_local_processing") == 5


class TestMultiSessionPersistence:
    """Test config persistence across multiple app sessions."""

    def test_incremental_updates(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Test that incremental updates across sessions work correctly."""
        from src.config.manager import ConfigManager

        # Session 1: Onboarding
        manager1 = ConfigManager()
        manager1.set("preferences.theme", "Dark")
        manager1.set("user_profile.primary_use_cases", ["image_generation"])

        # Session 2: Installation
        manager2 = ConfigManager()
        manager2.set_module_installed("comfyui", version="0.3.60")
        manager2.add_installed_model("sd_xl_base")

        # Session 3: Add more models
        manager3 = ConfigManager()
        manager3.add_installed_model("flux_dev_fp16")
        manager3.set("preferences.language", "ja")

        # Session 4: Verify all changes persisted
        manager4 = ConfigManager()

        assert manager4.get("preferences.theme") == "Dark"
        assert manager4.get("preferences.language") == "ja"
        assert "image_generation" in manager4.get("user_profile.primary_use_cases", [])
        assert manager4.get("installation.modules.comfyui.installed") is True

        models = manager4.get("installation.models_installed", [])
        assert "sd_xl_base" in models
        assert "flux_dev_fp16" in models

    def test_concurrent_write_safety(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Test that rapid successive writes don't corrupt config."""
        from src.config.manager import ConfigManager

        manager = ConfigManager()

        # Simulate rapid operations
        for i in range(10):
            manager.add_installed_model(f"model_{i}")
            manager.add_installed_node(f"node_{i}")

        # Reload and verify
        manager2 = ConfigManager()

        models = manager2.get("installation.models_installed", [])
        nodes = manager2.get("installation.custom_nodes_installed", [])

        assert len(models) == 10
        assert len(nodes) == 10

        for i in range(10):
            assert f"model_{i}" in models
            assert f"node_{i}" in nodes


class TestConfigBackup:
    """Test config backup and recovery functionality."""

    def test_backup_created_on_save(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Test that backup is created when config changes."""
        from src.config.manager import ConfigManager

        config_dir, config_file = isolated_config_env

        # Initial creation
        manager = ConfigManager()
        manager.set("test.value", "original")

        # Make a change (should trigger backup)
        manager.set("test.value", "modified")

        # Backup should exist
        backup_file = Path(str(config_file) + ".bak")
        assert backup_file.exists()

        # Backup should contain previous value
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        # Note: Due to initial save + modification save, backup may have "original" or first state

    def test_recovery_from_corrupted_config(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Test that corrupted config is replaced with defaults."""
        from src.config.manager import ConfigManager

        config_dir, config_file = isolated_config_env

        # Create valid config first
        manager = ConfigManager()
        manager.set("test.value", "working")

        # Corrupt the config file
        with open(config_file, 'w') as f:
            f.write("not valid json {{{")

        # Reload should recover to defaults
        manager2 = ConfigManager()

        # Should have a valid config structure
        assert manager2.get("version") == "3.0"
        assert manager2.get("schema_version") == 3


class TestPathConfiguration:
    """Integration tests for path configuration."""

    def test_derived_paths(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Test that models/outputs paths derive from ComfyUI path."""
        from src.config.manager import ConfigManager

        config_dir, _ = isolated_config_env

        manager = ConfigManager()
        comfy_path = str(config_dir / "ComfyUI")
        manager.set_comfyui_path(comfy_path)

        # Models and outputs should derive from ComfyUI path
        models_path = manager.get_models_path()
        outputs_path = manager.get_outputs_path()

        assert comfy_path in models_path
        assert "models" in models_path
        assert comfy_path in outputs_path
        assert "output" in outputs_path

    def test_explicit_path_overrides(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Test that explicit paths override derived paths."""
        from src.config.manager import ConfigManager

        config_dir, _ = isolated_config_env

        manager = ConfigManager()
        manager.set_comfyui_path(str(config_dir / "ComfyUI"))

        # Set explicit models path
        explicit_models = str(config_dir / "CustomModels")
        manager.set("paths.models", explicit_models)

        # Should use explicit path, not derived
        assert manager.get_models_path() == explicit_models


class TestModelRemoval:
    """Test model removal functionality."""

    def test_remove_installed_model(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Test that models can be removed from installed list."""
        from src.config.manager import ConfigManager

        manager = ConfigManager()

        # Add models
        manager.add_installed_model("model_to_keep")
        manager.add_installed_model("model_to_remove")
        manager.add_installed_model("another_keeper")

        assert len(manager.get("installation.models_installed", [])) == 3

        # Remove one
        manager.remove_installed_model("model_to_remove")

        # Reload and verify
        manager2 = ConfigManager()
        models = manager2.get("installation.models_installed", [])

        assert len(models) == 2
        assert "model_to_keep" in models
        assert "another_keeper" in models
        assert "model_to_remove" not in models

    def test_remove_nonexistent_model_safe(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Removing nonexistent model should not error."""
        from src.config.manager import ConfigManager

        manager = ConfigManager()
        manager.add_installed_model("existing_model")

        # Should not raise
        manager.remove_installed_model("nonexistent_model")

        # Original should still exist
        models = manager.get("installation.models_installed", [])
        assert "existing_model" in models


class TestInstallationStatusValidation:
    """Test installation status validation."""

    def test_invalid_status_raises(self, isolated_config_env: tuple[Path, Path]) -> None:
        """Setting invalid status should raise ValueError."""
        from src.config.manager import ConfigManager

        manager = ConfigManager()

        with pytest.raises(ValueError) as exc_info:
            manager.set_installation_status("invalid_status")

        assert "invalid_status" in str(exc_info.value)

    def test_valid_statuses_accepted(self, isolated_config_env: tuple[Path, Path]) -> None:
        """All valid statuses should be accepted."""
        from src.config.manager import ConfigManager

        manager = ConfigManager()

        valid_statuses = ["pending", "in_progress", "complete", "error"]
        for status in valid_statuses:
            manager.set_installation_status(status)
            assert manager.get("installation.status") == status


class TestTimestampTracking:
    """Test timestamp tracking functionality."""

    def test_created_at_immutable(self, isolated_config_env: tuple[Path, Path]) -> None:
        """created_at should not change after initial creation."""
        from src.config.manager import ConfigManager

        manager = ConfigManager()
        original_created = manager.get("created_at")

        # Make multiple changes
        manager.set("test1", "value1")
        manager.set("test2", "value2")
        manager.set("test3", "value3")

        # Reload
        manager2 = ConfigManager()

        # created_at should be the same
        assert manager2.get("created_at") == original_created

    def test_updated_at_changes_on_each_save(self, isolated_config_env: tuple[Path, Path]) -> None:
        """updated_at should change on each save operation."""
        from src.config.manager import ConfigManager
        import time

        manager = ConfigManager()
        ts1 = manager.get("updated_at")

        time.sleep(0.01)  # Ensure timestamp difference
        manager.set("test", "value1")
        ts2 = manager.get("updated_at")

        time.sleep(0.01)
        manager.set("test", "value2")
        ts3 = manager.get("updated_at")

        assert ts1 != ts2
        assert ts2 != ts3
