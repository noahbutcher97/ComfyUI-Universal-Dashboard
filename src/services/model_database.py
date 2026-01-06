"""
Model Database Service.

Loads and queries the models_database.yaml file which contains all model
definitions with variants, platform support, and capabilities.

This replaces the legacy resources.json model loading.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Iterator
from pathlib import Path
import yaml

from src.utils.logger import log


# =============================================================================
# Data Classes for YAML Schema
# =============================================================================

@dataclass
class PlatformSupport:
    """Platform support configuration for a model variant."""
    supported: bool = False
    min_compute_capability: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class ModelVariant:
    """A specific variant of a model (e.g., fp16, fp8, gguf_q4)."""
    id: str
    precision: str
    vram_min_mb: int
    vram_recommended_mb: int
    download_size_gb: float
    quality_retention_percent: int = 100
    download_url: Optional[str] = None
    platform_support: Dict[str, PlatformSupport] = field(default_factory=dict)
    requires_nodes: List[str] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class ModelCapabilities:
    """Capabilities and scores for a model."""
    primary: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    features: List[Dict[str, Any]] = field(default_factory=list)
    style_strengths: List[str] = field(default_factory=list)
    controlnet_support: List[str] = field(default_factory=list)

    # Video-specific
    video_modes: List[str] = field(default_factory=list)
    max_duration_seconds: Optional[int] = None
    max_resolution: Optional[str] = None
    audio_support: bool = False

    # Audio-specific
    voice_cloning: bool = False
    voice_clone_sample_seconds: Optional[int] = None
    languages: List[str] = field(default_factory=list)
    preset_voices: Optional[int] = None

    # 3D-specific
    output_formats: List[str] = field(default_factory=list)
    pbr_materials: bool = False


@dataclass
class ModelDependencies:
    """Dependencies for a model."""
    required_nodes: List[Dict[str, Any]] = field(default_factory=list)
    paired_models: List[Dict[str, str]] = field(default_factory=list)
    incompatibilities: List[str] = field(default_factory=list)


@dataclass
class ModelExplanation:
    """Pre-written explanation templates for a model."""
    selected: Optional[str] = None
    rejected_vram: Optional[str] = None
    rejected_platform: Optional[str] = None


@dataclass
class CloudInfo:
    """Cloud availability information."""
    partner_node: bool = False
    partner_service: Optional[str] = None
    replicate: bool = False
    estimated_cost_per_generation: Optional[float] = None


@dataclass
class ModelEntry:
    """
    Complete model entry from the database.

    Maps directly to the YAML schema defined in SPEC_v3 Section 7.
    """
    id: str
    name: str
    category: str
    family: str
    release_date: Optional[str] = None
    license: Optional[str] = None
    commercial_use: bool = True

    architecture: Dict[str, Any] = field(default_factory=dict)
    variants: List[ModelVariant] = field(default_factory=list)
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    dependencies: ModelDependencies = field(default_factory=ModelDependencies)
    explanation: ModelExplanation = field(default_factory=ModelExplanation)
    cloud: CloudInfo = field(default_factory=CloudInfo)

    # Cloud-only models (no local variants)
    provider: Optional[str] = None
    pricing: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# Platform Constants
# =============================================================================

PLATFORM_KEYS = {
    "windows_nvidia": ["windows", "nvidia"],
    "mac_mps": ["darwin", "apple", "mps"],
    "linux_rocm": ["linux", "amd", "rocm"],
}


def normalize_platform(gpu_vendor: str, os_platform: str) -> str:
    """
    Convert gpu_vendor and OS to a platform key.

    Args:
        gpu_vendor: "nvidia", "apple", "amd", "none"
        os_platform: "Windows", "Darwin", "Linux"

    Returns:
        Platform key: "windows_nvidia", "mac_mps", "linux_rocm"
    """
    os_lower = os_platform.lower()
    vendor_lower = gpu_vendor.lower()

    if "darwin" in os_lower or "mac" in os_lower:
        return "mac_mps"
    elif "linux" in os_lower:
        if vendor_lower in ("amd", "rocm"):
            return "linux_rocm"
        else:
            return "windows_nvidia"  # Linux + NVIDIA uses same support
    else:
        # Windows
        if vendor_lower == "nvidia":
            return "windows_nvidia"
        elif vendor_lower in ("amd", "rocm"):
            return "linux_rocm"  # Windows AMD similar to Linux ROCm support
        else:
            return "windows_nvidia"  # Default


# =============================================================================
# Model Database Class
# =============================================================================

class ModelDatabase:
    """
    Loads and queries the models_database.yaml file.

    This is the single source of truth for model definitions, replacing
    the legacy resources.json model sections.

    Usage:
        db = ModelDatabase()
        db.load()

        # Get all image generation models
        models = db.get_models_by_category("image_generation")

        # Get models compatible with current platform and VRAM
        candidates = db.get_compatible_models(
            platform="windows_nvidia",
            vram_mb=12000,
            categories=["image_generation", "video_generation"]
        )
    """

    # Default path relative to project root
    DEFAULT_PATH = Path(__file__).parent.parent.parent / "data" / "models_database.yaml"

    # Categories in the YAML file
    CATEGORIES = [
        "image_generation",
        "video_generation",
        "audio_generation",
        "3d_generation",
        "lip_sync",
        "cloud_apis",
    ]

    def __init__(self, yaml_path: Optional[Path] = None):
        """
        Initialize the model database.

        Args:
            yaml_path: Optional path to the YAML file. Defaults to data/models_database.yaml
        """
        self.yaml_path = yaml_path or self.DEFAULT_PATH
        self._raw_data: Dict[str, Any] = {}
        self._models: Dict[str, ModelEntry] = {}  # Keyed by model ID
        self._loaded = False

    def load(self) -> bool:
        """
        Load the model database from YAML.

        Returns:
            True if loaded successfully, False otherwise.
        """
        try:
            with open(self.yaml_path, "r", encoding="utf-8") as f:
                self._raw_data = yaml.safe_load(f) or {}

            self._parse_models()
            self._loaded = True
            log.info(f"Loaded {len(self._models)} models from {self.yaml_path}")
            return True

        except FileNotFoundError:
            log.error(f"Model database not found: {self.yaml_path}")
            return False
        except yaml.YAMLError as e:
            log.error(f"Failed to parse model database: {e}")
            return False
        except Exception as e:
            log.error(f"Error loading model database: {e}")
            return False

    def _parse_models(self) -> None:
        """Parse raw YAML data into ModelEntry objects."""
        self._models.clear()

        for category in self.CATEGORIES:
            category_data = self._raw_data.get(category, {})
            if not isinstance(category_data, dict):
                continue

            for model_id, model_data in category_data.items():
                if not isinstance(model_data, dict):
                    continue

                try:
                    entry = self._parse_model_entry(model_id, category, model_data)
                    self._models[model_id] = entry
                except Exception as e:
                    log.warning(f"Failed to parse model {model_id}: {e}")

    def _parse_model_entry(
        self,
        model_id: str,
        category: str,
        data: Dict[str, Any]
    ) -> ModelEntry:
        """Parse a single model entry from YAML data."""

        # Parse variants
        variants = []
        for var_data in data.get("variants", []):
            variant = self._parse_variant(var_data)
            variants.append(variant)

        # Parse capabilities
        caps_data = data.get("capabilities", {})
        capabilities = ModelCapabilities(
            primary=caps_data.get("primary", []),
            scores=caps_data.get("scores", {}),
            features=caps_data.get("features", []),
            style_strengths=caps_data.get("style_strengths", []),
            controlnet_support=caps_data.get("controlnet_support", []),
            video_modes=caps_data.get("video_modes", []),
            max_duration_seconds=caps_data.get("max_duration_seconds"),
            max_resolution=caps_data.get("max_resolution"),
            audio_support=caps_data.get("audio_support", False),
            voice_cloning=caps_data.get("voice_cloning", False),
            voice_clone_sample_seconds=caps_data.get("voice_clone_sample_seconds"),
            languages=caps_data.get("languages", []),
            preset_voices=caps_data.get("preset_voices"),
            output_formats=caps_data.get("output_formats", []),
            pbr_materials=caps_data.get("pbr_materials", False),
        )

        # Parse dependencies
        deps_data = data.get("dependencies", {})
        dependencies = ModelDependencies(
            required_nodes=deps_data.get("required_nodes", []),
            paired_models=deps_data.get("paired_models", []),
            incompatibilities=deps_data.get("incompatibilities", []),
        )

        # Parse explanation templates
        expl_data = data.get("explanation", {})
        explanation = ModelExplanation(
            selected=expl_data.get("selected"),
            rejected_vram=expl_data.get("rejected_vram"),
            rejected_platform=expl_data.get("rejected_platform"),
        )

        # Parse cloud info
        cloud_data = data.get("cloud", {})
        cloud = CloudInfo(
            partner_node=cloud_data.get("partner_node", False),
            partner_service=cloud_data.get("partner_service"),
            replicate=cloud_data.get("replicate", False),
            estimated_cost_per_generation=cloud_data.get("estimated_cost_per_generation"),
        )

        # Handle cloud-only models (no variants)
        pricing_data = data.get("pricing", {})

        return ModelEntry(
            id=model_id,
            name=data.get("name", model_id),
            category=category,
            family=data.get("family", "unknown"),
            release_date=data.get("release_date"),
            license=data.get("license"),
            commercial_use=data.get("commercial_use", True),
            architecture=data.get("architecture", {}),
            variants=variants,
            capabilities=capabilities,
            dependencies=dependencies,
            explanation=explanation,
            cloud=cloud,
            provider=data.get("provider"),
            pricing=pricing_data,
        )

    def _parse_variant(self, data: Dict[str, Any]) -> ModelVariant:
        """Parse a model variant from YAML data."""

        # Parse platform support
        platform_support = {}
        for platform_key in ["windows_nvidia", "mac_mps", "linux_rocm"]:
            ps_data = data.get("platform_support", {}).get(platform_key, {})
            if isinstance(ps_data, dict):
                platform_support[platform_key] = PlatformSupport(
                    supported=ps_data.get("supported", False),
                    min_compute_capability=ps_data.get("min_compute_capability"),
                    notes=ps_data.get("notes"),
                )
            elif isinstance(ps_data, bool):
                platform_support[platform_key] = PlatformSupport(supported=ps_data)

        return ModelVariant(
            id=data.get("id", "unknown"),
            precision=data.get("precision", "fp16"),
            vram_min_mb=data.get("vram_min_mb", 0),
            vram_recommended_mb=data.get("vram_recommended_mb", 0),
            download_size_gb=data.get("download_size_gb", 0),
            quality_retention_percent=data.get("quality_retention_percent", 100),
            download_url=data.get("download_url"),
            platform_support=platform_support,
            requires_nodes=data.get("requires_nodes", []),
            notes=data.get("notes"),
        )

    # =========================================================================
    # Query Methods
    # =========================================================================

    @property
    def is_loaded(self) -> bool:
        """Check if database is loaded."""
        return self._loaded

    def get_model(self, model_id: str) -> Optional[ModelEntry]:
        """Get a model by ID."""
        return self._models.get(model_id)

    def get_all_models(self) -> List[ModelEntry]:
        """Get all models."""
        return list(self._models.values())

    def get_models_by_category(self, category: str) -> List[ModelEntry]:
        """Get all models in a category."""
        return [m for m in self._models.values() if m.category == category]

    def get_models_by_family(self, family: str) -> List[ModelEntry]:
        """Get all models in a family (e.g., 'flux', 'wan', 'sdxl')."""
        return [m for m in self._models.values() if m.family == family]

    def get_models_by_capability(self, capability: str) -> List[ModelEntry]:
        """Get models that support a specific capability (e.g., 'text_to_image')."""
        return [
            m for m in self._models.values()
            if capability in m.capabilities.primary
        ]

    def get_local_models(self) -> List[ModelEntry]:
        """Get models that can run locally (have variants)."""
        return [m for m in self._models.values() if m.variants]

    def get_cloud_models(self) -> List[ModelEntry]:
        """Get cloud-only models."""
        return [
            m for m in self._models.values()
            if m.category == "cloud_apis" or (m.cloud.partner_node and not m.variants)
        ]

    def get_compatible_variants(
        self,
        model: ModelEntry,
        platform: str,
        vram_mb: int,
        compute_capability: Optional[float] = None,
    ) -> List[ModelVariant]:
        """
        Get variants of a model compatible with the given hardware.

        Args:
            model: The model entry
            platform: Platform key (e.g., "windows_nvidia", "mac_mps")
            vram_mb: Available VRAM in MB
            compute_capability: CUDA compute capability (for FP8 filtering)

        Returns:
            List of compatible variants, sorted by quality retention (highest first)
        """
        compatible = []

        for variant in model.variants:
            # Check VRAM requirement
            if variant.vram_min_mb > vram_mb:
                continue

            # Check platform support
            ps = variant.platform_support.get(platform)
            if not ps or not ps.supported:
                continue

            # Check compute capability for FP8 variants
            if ps.min_compute_capability:
                # If variant requires specific CC but none provided, skip it
                if compute_capability is None:
                    continue
                # If CC provided but too low, skip it
                if compute_capability < ps.min_compute_capability:
                    continue

            # Check MPS K-quant restrictions
            if platform == "mac_mps" and "k_" in variant.precision.lower():
                # K-quants crash on MPS - skip unless explicitly noted as safe
                if not ps.notes or "k-quant" not in ps.notes.lower():
                    continue

            compatible.append(variant)

        # Sort by quality retention (prefer higher quality)
        compatible.sort(key=lambda v: v.quality_retention_percent, reverse=True)

        return compatible

    def get_compatible_models(
        self,
        platform: str,
        vram_mb: int,
        categories: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        compute_capability: Optional[float] = None,
        commercial_only: bool = False,
    ) -> List[tuple[ModelEntry, ModelVariant]]:
        """
        Get all models with at least one compatible variant.

        Args:
            platform: Platform key (e.g., "windows_nvidia", "mac_mps")
            vram_mb: Available VRAM in MB
            categories: Filter to specific categories (None = all)
            capabilities: Filter to models with these capabilities (None = all)
            compute_capability: CUDA compute capability (for FP8 filtering)
            commercial_only: Only include commercially-licensed models

        Returns:
            List of (model, best_variant) tuples
        """
        results = []

        for model in self._models.values():
            # Category filter
            if categories and model.category not in categories:
                continue

            # Capability filter
            if capabilities:
                if not any(c in model.capabilities.primary for c in capabilities):
                    continue

            # Commercial license filter
            if commercial_only and not model.commercial_use:
                continue

            # Get compatible variants
            variants = self.get_compatible_variants(
                model, platform, vram_mb, compute_capability
            )

            if variants:
                # Return best variant (highest quality retention)
                results.append((model, variants[0]))

        return results

    def get_required_nodes(self, model: ModelEntry, variant: ModelVariant) -> List[str]:
        """
        Get all required custom nodes for a model+variant combination.

        Args:
            model: The model entry
            variant: The selected variant

        Returns:
            List of required node package names
        """
        nodes = set()

        # Variant-specific nodes (e.g., ComfyUI-GGUF for GGUF variants)
        nodes.update(variant.requires_nodes)

        # Model-level dependencies
        for dep in model.dependencies.required_nodes:
            if isinstance(dep, dict):
                package = dep.get("package", "")
                required_for = dep.get("required_for", [])

                # Check if this node is required for this variant
                if "all" in required_for or variant.id in required_for:
                    nodes.add(package)
            elif isinstance(dep, str):
                nodes.add(dep)

        return list(nodes)

    def get_paired_models(self, model: ModelEntry) -> List[str]:
        """
        Get model IDs that must be used together with this model.

        Args:
            model: The model entry

        Returns:
            List of paired model IDs
        """
        return [
            pm.get("model_id", "")
            for pm in model.dependencies.paired_models
            if pm.get("model_id")
        ]

    def iter_models(self) -> Iterator[ModelEntry]:
        """Iterate over all models."""
        yield from self._models.values()

    def __len__(self) -> int:
        """Return number of models in database."""
        return len(self._models)

    def __contains__(self, model_id: str) -> bool:
        """Check if a model ID exists."""
        return model_id in self._models


# =============================================================================
# Module-level singleton for convenience
# =============================================================================

_default_database: Optional[ModelDatabase] = None


def get_model_database() -> ModelDatabase:
    """
    Get the default model database instance.

    Loads the database on first call.

    Returns:
        The ModelDatabase singleton instance
    """
    global _default_database

    if _default_database is None:
        _default_database = ModelDatabase()
        _default_database.load()

    return _default_database


def reload_model_database() -> ModelDatabase:
    """
    Reload the model database from disk.

    Returns:
        The reloaded ModelDatabase instance
    """
    global _default_database

    _default_database = ModelDatabase()
    _default_database.load()

    return _default_database
