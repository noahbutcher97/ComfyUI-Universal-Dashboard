"""
Configuration Manager v3.0.

Handles persistence of user preferences, installation state, and config versioning.
Supports migration from v1/v2 configs.
"""

import os
import json
import shutil
import keyring
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.utils.logger import log


class ConfigManager:
    """
    Configuration manager with v3.0 schema support.

    Features:
    - Schema versioning (migrates v1/v2 to v3)
    - Nested key access via dot notation
    - Installation state tracking
    - Timestamp tracking (created_at, updated_at)
    - Secure API key storage via keyring
    """

    APP_NAME = "UniversalAISuite"
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".universal_ai_suite")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
    CURRENT_SCHEMA_VERSION = 3

    # Secure keys stored in OS keyring, not config file
    SECURE_KEYS = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GROK_API_KEY",
        "DEEPSEEK_API_KEY",
    ]

    # Default v3 config structure
    DEFAULT_CONFIG = {
        "version": "3.0",
        "schema_version": 3,
        "created_at": None,  # Set on creation
        "updated_at": None,  # Set on every save

        "paths": {
            "comfyui": os.path.join(os.path.expanduser("~"), "ComfyUI"),
            "models": None,  # Derived from comfyui path
            "outputs": None,  # Derived from comfyui path
        },

        "preferences": {
            "theme": "Dark",
            "language": "en",
            "onboarding_completed": False,
            "onboarding_path": None,  # "quick" or "comprehensive"
        },

        "user_profile": {
            "ai_experience": 1,
            "technical_experience": 1,
            "primary_use_cases": [],
            "prefer_simple_setup": 3,
            "prefer_local_processing": 3,
            "prefer_open_source": 3,
        },

        "installation": {
            "status": "pending",  # "pending", "in_progress", "complete", "error"
            "modules": {},
            "models_installed": [],
            "custom_nodes_installed": [],
        },
    }

    def __init__(self):
        """Initialize the config manager and load config."""
        self._ensure_config_dir()
        self.config = self._load_config()
        self._validate_and_migrate()

    def _ensure_config_dir(self) -> None:
        """Ensure config directory exists."""
        if not os.path.exists(self.CONFIG_DIR):
            os.makedirs(self.CONFIG_DIR)

    def _load_config(self) -> Dict[str, Any]:
        """Load config from file or create default."""
        if not os.path.exists(self.CONFIG_FILE):
            config = self._create_default_config()
            self._save_config(config)
            return config

        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            log.error(f"Failed to load config: {e}. Creating new config.")
            config = self._create_default_config()
            self._save_config(config)
            return config

    def _create_default_config(self) -> Dict[str, Any]:
        """Create a new default config with timestamps."""
        config = self._deep_copy(self.DEFAULT_CONFIG)
        now = datetime.utcnow().isoformat()
        config["created_at"] = now
        config["updated_at"] = now
        return config

    def _save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Save config to file with backup."""
        if config is None:
            config = self.config

        # Update timestamp
        config["updated_at"] = datetime.utcnow().isoformat()

        # Backup existing config
        if os.path.exists(self.CONFIG_FILE):
            try:
                shutil.copy2(self.CONFIG_FILE, self.CONFIG_FILE + ".bak")
            except IOError as e:
                log.warning(f"Failed to backup config: {e}")

        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            log.error(f"Failed to save config: {e}")

    def _validate_and_migrate(self) -> None:
        """Validate config and migrate from older versions if needed."""
        schema_version = self.config.get("schema_version", 1)

        if schema_version < self.CURRENT_SCHEMA_VERSION:
            self._migrate_config(schema_version)

        self._validate_structure()
        self._save_config()

    def _migrate_config(self, from_version: int) -> None:
        """Migrate config from older version to current."""
        log.info(f"Migrating config from v{from_version} to v{self.CURRENT_SCHEMA_VERSION}")

        # Backup old config
        backup_file = f"{self.CONFIG_FILE}.v{from_version}.bak"
        try:
            shutil.copy2(self.CONFIG_FILE, backup_file)
            log.info(f"Created backup: {backup_file}")
        except IOError as e:
            log.warning(f"Failed to create migration backup: {e}")

        # Get old values before migration
        old_config = self.config.copy()

        if from_version == 1:
            self._migrate_v1_to_v3(old_config)
        elif from_version == 2:
            self._migrate_v2_to_v3(old_config)

        # Set version
        self.config["version"] = "3.0"
        self.config["schema_version"] = 3

        # Preserve timestamps if migrating
        if "created_at" not in self.config or self.config["created_at"] is None:
            self.config["created_at"] = datetime.utcnow().isoformat()

    def _migrate_v1_to_v3(self, old: Dict[str, Any]) -> None:
        """Migrate v1 config (no version field) to v3."""
        # Start with default v3 structure
        new_config = self._deep_copy(self.DEFAULT_CONFIG)

        # Map old fields to new structure
        if "comfy_path" in old:
            new_config["paths"]["comfyui"] = old["comfy_path"]

        if "theme" in old:
            new_config["preferences"]["theme"] = old["theme"]

        if "first_run" in old:
            new_config["preferences"]["onboarding_completed"] = not old["first_run"]

        # Copy timestamps if they exist
        if "created_at" in old:
            new_config["created_at"] = old["created_at"]

        self.config = new_config

    def _migrate_v2_to_v3(self, old: Dict[str, Any]) -> None:
        """Migrate v2 config to v3."""
        # Start with default v3 structure
        new_config = self._deep_copy(self.DEFAULT_CONFIG)

        # Map old fields to new structure
        if "comfy_path" in old:
            new_config["paths"]["comfyui"] = old["comfy_path"]

        if "theme" in old:
            new_config["preferences"]["theme"] = old["theme"]

        if "first_run" in old:
            new_config["preferences"]["onboarding_completed"] = not old["first_run"]

        if "selected_use_case" in old:
            new_config["user_profile"]["primary_use_cases"] = [old["selected_use_case"]]

        # Copy timestamps if they exist
        if "created_at" in old:
            new_config["created_at"] = old["created_at"]

        self.config = new_config

    def _validate_structure(self) -> None:
        """Ensure config has all required keys with correct types."""
        # Add missing top-level keys
        for key, default in self.DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = self._deep_copy(default)
            elif isinstance(default, dict) and not isinstance(self.config[key], dict):
                # Wrong type - replace with default
                self.config[key] = self._deep_copy(default)
            elif isinstance(default, dict):
                # Recursively check nested dicts
                for subkey, subdefault in default.items():
                    if subkey not in self.config[key]:
                        self.config[key][subkey] = self._deep_copy(subdefault)

    def _deep_copy(self, obj: Any) -> Any:
        """Deep copy a JSON-serializable object."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(i) for i in obj]
        return obj

    # =========================================================================
    # Public API - Get/Set
    # =========================================================================

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a config value by key.

        Supports dot notation for nested keys:
            manager.get("preferences.theme")
            manager.get("installation.modules.comfyui.version")

        Args:
            key: The config key (supports dot notation)
            default: Default value if key not found

        Returns:
            The config value or default
        """
        parts = key.split(".")
        value = self.config

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set a config value by key.

        Supports dot notation for nested keys:
            manager.set("preferences.theme", "Light")

        Args:
            key: The config key (supports dot notation)
            value: The value to set
        """
        parts = key.split(".")

        # Navigate to parent
        parent = self.config
        for part in parts[:-1]:
            if part not in parent:
                parent[part] = {}
            parent = parent[part]

        # Set value
        parent[parts[-1]] = value

        # Save changes
        self._save_config()

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Public method to save config."""
        self._save_config(config)

    def load_config(self) -> Dict[str, Any]:
        """Public method to reload config from disk."""
        self.config = self._load_config()
        return self.config

    # =========================================================================
    # Installation State API
    # =========================================================================

    def set_module_installed(
        self,
        module_id: str,
        version: Optional[str] = None,
        **metadata
    ) -> None:
        """
        Record that a module has been installed.

        Args:
            module_id: Module identifier (e.g., "comfyui", "cli_provider")
            version: Optional version string
            **metadata: Additional metadata (provider, etc.)
        """
        modules = self.get("installation.modules", {})

        modules[module_id] = {
            "installed": True,
            "version": version,
            "install_date": datetime.utcnow().isoformat(),
            **metadata,
        }

        self.set("installation.modules", modules)

    def add_installed_model(self, model_id: str) -> None:
        """
        Record that a model has been installed.

        Args:
            model_id: Model identifier from models_database.yaml
        """
        models = self.get("installation.models_installed", [])

        if model_id not in models:
            models.append(model_id)
            self.set("installation.models_installed", models)

    def remove_installed_model(self, model_id: str) -> None:
        """
        Record that a model has been removed.

        Args:
            model_id: Model identifier
        """
        models = self.get("installation.models_installed", [])

        if model_id in models:
            models.remove(model_id)
            self.set("installation.models_installed", models)

    def add_installed_node(self, node_id: str) -> None:
        """
        Record that a custom node has been installed.

        Args:
            node_id: Custom node identifier (e.g., "ComfyUI-GGUF")
        """
        nodes = self.get("installation.custom_nodes_installed", [])

        if node_id not in nodes:
            nodes.append(node_id)
            self.set("installation.custom_nodes_installed", nodes)

    def set_installation_status(self, status: str) -> None:
        """
        Set the overall installation status.

        Args:
            status: One of "pending", "in_progress", "complete", "error"
        """
        valid_statuses = ["pending", "in_progress", "complete", "error"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

        self.set("installation.status", status)

    # =========================================================================
    # Path API
    # =========================================================================

    def get_comfyui_path(self) -> str:
        """Get the ComfyUI installation path."""
        return self.get("paths.comfyui") or self.DEFAULT_CONFIG["paths"]["comfyui"]

    def set_comfyui_path(self, path: str) -> None:
        """Set the ComfyUI installation path."""
        self.set("paths.comfyui", path)

    def get_models_path(self) -> str:
        """Get the models directory path."""
        models_path = self.get("paths.models")
        if models_path:
            return models_path
        return os.path.join(self.get_comfyui_path(), "models")

    def get_outputs_path(self) -> str:
        """Get the outputs directory path."""
        outputs_path = self.get("paths.outputs")
        if outputs_path:
            return outputs_path
        return os.path.join(self.get_comfyui_path(), "output")

    # =========================================================================
    # Secure Storage API
    # =========================================================================

    def get_secure(self, key: str) -> str:
        """
        Retrieve a sensitive value from OS keyring.

        Args:
            key: The key name (e.g., "ANTHROPIC_API_KEY")

        Returns:
            The value or empty string if not found
        """
        try:
            val = keyring.get_password(self.APP_NAME, key)
            return val if val else ""
        except Exception as e:
            log.error(f"Keyring get error for {key}: {e}")
            return ""

    def set_secure(self, key: str, value: str) -> None:
        """
        Save a sensitive value to OS keyring.

        Args:
            key: The key name
            value: The value to store (empty string to delete)
        """
        try:
            if value:
                keyring.set_password(self.APP_NAME, key, value)
            else:
                try:
                    keyring.delete_password(self.APP_NAME, key)
                except Exception:
                    pass
        except Exception as e:
            log.error(f"Keyring set error for {key}: {e}")

    def migrate_legacy_keys(self) -> None:
        """Migrate API keys from old config.json to Keyring."""
        if "api_keys" in self.config:
            log.info("Migrating legacy API keys to secure storage...")
            for k, v in self.config["api_keys"].items():
                if v:
                    self.set_secure(k, v)
            del self.config["api_keys"]
            self._save_config()

    # =========================================================================
    # Resources API (Legacy compatibility)
    # =========================================================================

    def get_resources(self) -> Dict[str, Any]:
        """
        Load resources from resources.json.

        Note: Model data should be loaded from models_database.yaml via ModelDatabase.
        This method loads non-model resources (use_cases, modules, etc.)
        """
        res_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "resources.json"
        )

        if os.path.exists(res_file):
            try:
                with open(res_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                log.error(f"Failed to load resources: {e}")

        return {}

    def validate_config(self) -> None:
        """Legacy method - validation now happens in __init__."""
        self._validate_structure()
        self._save_config()


# Module-level singleton
config_manager = ConfigManager()
