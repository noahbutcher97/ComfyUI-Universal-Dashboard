"""
Unit tests for ModelDatabase service.

Tests cover loading, parsing, and querying the models_database.yaml file.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import yaml

from src.services.model_database import (
    ModelDatabase,
    ModelEntry,
    ModelVariant,
    ModelCapabilities,
    PlatformSupport,
    normalize_platform,
    get_model_database,
    reload_model_database,
)


# =============================================================================
# Test Data
# =============================================================================

SAMPLE_YAML = """
image_generation:
  test_model:
    name: "Test Model"
    family: "test"
    release_date: "2025-01-01"
    license: "mit"
    commercial_use: true

    architecture:
      type: "transformer"
      parameters_b: 1.5

    variants:
      - id: "fp16"
        precision: "fp16"
        vram_min_mb: 8000
        vram_recommended_mb: 12000
        download_url: "https://example.com/model.safetensors"
        download_size_gb: 3.5
        quality_retention_percent: 100
        platform_support:
          windows_nvidia: {supported: true}
          mac_mps: {supported: true}
          linux_rocm: {supported: true}

      - id: "fp8"
        precision: "fp8"
        vram_min_mb: 4000
        vram_recommended_mb: 6000
        download_size_gb: 1.8
        quality_retention_percent: 98
        platform_support:
          windows_nvidia: {supported: true, min_compute_capability: 8.9}
          mac_mps: {supported: false}
          linux_rocm: {supported: false}

      - id: "gguf_q4"
        precision: "gguf_q4_k_m"
        vram_min_mb: 2000
        vram_recommended_mb: 3000
        download_size_gb: 1.0
        quality_retention_percent: 85
        platform_support:
          windows_nvidia: {supported: true}
          mac_mps: {supported: true, notes: "Use Q4_0 variant"}
          linux_rocm: {supported: true}
        requires_nodes: ["ComfyUI-GGUF"]

    capabilities:
      primary: ["text_to_image", "image_to_image"]
      scores:
        photorealism: 0.85
        artistic_quality: 0.90
        speed: 0.6
      style_strengths: ["photorealistic", "anime"]

    dependencies:
      required_nodes:
        - package: "ComfyUI-GGUF"
          repo: "https://github.com/city96/ComfyUI-GGUF"
          required_for: ["gguf_q4"]

    explanation:
      selected: "Great balance of quality and speed"
      rejected_vram: "Requires more VRAM"

video_generation:
  test_video_model:
    name: "Test Video Model"
    family: "test_video"
    commercial_use: true

    variants:
      - id: "fp16"
        precision: "fp16"
        vram_min_mb: 12000
        vram_recommended_mb: 16000
        download_size_gb: 8.0
        platform_support:
          windows_nvidia: {supported: true}
          mac_mps: {supported: false}
          linux_rocm: {supported: true}

    capabilities:
      primary: ["text_to_video", "image_to_video"]
      video_modes: ["t2v", "i2v"]
      max_duration_seconds: 5
      scores:
        motion_quality: 0.88

cloud_apis:
  test_cloud:
    name: "Test Cloud API"
    family: "cloud"
    provider: "test_provider"
    partner_node: true

    capabilities:
      primary: ["text_to_video"]

    pricing:
      estimated_cost_per_generation: 0.10
"""


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_yaml_path(tmp_path):
    """Create a temporary YAML file with sample data."""
    yaml_file = tmp_path / "test_models.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    return yaml_file


@pytest.fixture
def model_db(sample_yaml_path):
    """Create a ModelDatabase loaded with sample data."""
    db = ModelDatabase(sample_yaml_path)
    db.load()
    return db


# =============================================================================
# Test: Loading
# =============================================================================

class TestModelDatabaseLoading:
    """Tests for loading the model database."""

    def test_load_success(self, sample_yaml_path):
        """Should load YAML file successfully."""
        db = ModelDatabase(sample_yaml_path)
        result = db.load()

        assert result is True
        assert db.is_loaded is True
        assert len(db) == 3  # test_model, test_video_model, test_cloud

    def test_load_file_not_found(self, tmp_path):
        """Should return False when file not found."""
        db = ModelDatabase(tmp_path / "nonexistent.yaml")
        result = db.load()

        assert result is False
        assert db.is_loaded is False

    def test_load_invalid_yaml(self, tmp_path):
        """Should return False for invalid YAML."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("invalid: yaml: content: [")

        db = ModelDatabase(yaml_file)
        result = db.load()

        assert result is False

    def test_load_empty_file(self, tmp_path):
        """Should handle empty YAML file."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        db = ModelDatabase(yaml_file)
        result = db.load()

        assert result is True
        assert len(db) == 0


# =============================================================================
# Test: Parsing
# =============================================================================

class TestModelDatabaseParsing:
    """Tests for parsing model entries."""

    def test_parse_model_entry(self, model_db):
        """Should parse model entry correctly."""
        model = model_db.get_model("test_model")

        assert model is not None
        assert model.id == "test_model"
        assert model.name == "Test Model"
        assert model.family == "test"
        assert model.category == "image_generation"
        assert model.license == "mit"
        assert model.commercial_use is True

    def test_parse_variants(self, model_db):
        """Should parse all variants."""
        model = model_db.get_model("test_model")

        assert len(model.variants) == 3

        fp16 = model.variants[0]
        assert fp16.id == "fp16"
        assert fp16.precision == "fp16"
        assert fp16.vram_min_mb == 8000
        assert fp16.download_size_gb == 3.5

    def test_parse_platform_support(self, model_db):
        """Should parse platform support correctly."""
        model = model_db.get_model("test_model")
        fp8 = model.variants[1]

        nvidia = fp8.platform_support.get("windows_nvidia")
        assert nvidia is not None
        assert nvidia.supported is True
        assert nvidia.min_compute_capability == 8.9

        mps = fp8.platform_support.get("mac_mps")
        assert mps is not None
        assert mps.supported is False

    def test_parse_capabilities(self, model_db):
        """Should parse capabilities correctly."""
        model = model_db.get_model("test_model")

        assert "text_to_image" in model.capabilities.primary
        assert model.capabilities.scores["photorealism"] == 0.85
        assert "photorealistic" in model.capabilities.style_strengths

    def test_parse_video_capabilities(self, model_db):
        """Should parse video-specific capabilities."""
        model = model_db.get_model("test_video_model")

        assert "t2v" in model.capabilities.video_modes
        assert model.capabilities.max_duration_seconds == 5

    def test_parse_dependencies(self, model_db):
        """Should parse dependencies correctly."""
        model = model_db.get_model("test_model")

        assert len(model.dependencies.required_nodes) == 1
        node = model.dependencies.required_nodes[0]
        assert node["package"] == "ComfyUI-GGUF"

    def test_parse_cloud_model(self, model_db):
        """Should parse cloud-only models."""
        model = model_db.get_model("test_cloud")

        assert model.provider == "test_provider"
        assert model.category == "cloud_apis"
        assert len(model.variants) == 0


# =============================================================================
# Test: Query Methods
# =============================================================================

class TestModelDatabaseQueries:
    """Tests for query methods."""

    def test_get_model(self, model_db):
        """Should get model by ID."""
        model = model_db.get_model("test_model")
        assert model is not None
        assert model.name == "Test Model"

    def test_get_model_not_found(self, model_db):
        """Should return None for unknown model."""
        model = model_db.get_model("nonexistent")
        assert model is None

    def test_get_all_models(self, model_db):
        """Should return all models."""
        models = model_db.get_all_models()
        assert len(models) == 3

    def test_get_models_by_category(self, model_db):
        """Should filter by category."""
        image_models = model_db.get_models_by_category("image_generation")
        assert len(image_models) == 1
        assert image_models[0].id == "test_model"

        video_models = model_db.get_models_by_category("video_generation")
        assert len(video_models) == 1

    def test_get_models_by_family(self, model_db):
        """Should filter by family."""
        models = model_db.get_models_by_family("test")
        assert len(models) == 1
        assert models[0].id == "test_model"

    def test_get_models_by_capability(self, model_db):
        """Should filter by capability."""
        t2i_models = model_db.get_models_by_capability("text_to_image")
        assert len(t2i_models) == 1

        t2v_models = model_db.get_models_by_capability("text_to_video")
        assert len(t2v_models) == 2  # test_video_model and test_cloud

    def test_get_local_models(self, model_db):
        """Should return only local models (with variants)."""
        local = model_db.get_local_models()
        assert len(local) == 2
        assert all(m.variants for m in local)

    def test_get_cloud_models(self, model_db):
        """Should return cloud-only models."""
        cloud = model_db.get_cloud_models()
        assert len(cloud) == 1
        assert cloud[0].id == "test_cloud"

    def test_contains(self, model_db):
        """Should support 'in' operator."""
        assert "test_model" in model_db
        assert "nonexistent" not in model_db

    def test_iter(self, model_db):
        """Should support iteration."""
        model_ids = [m.id for m in model_db.iter_models()]
        assert "test_model" in model_ids
        assert len(model_ids) == 3


# =============================================================================
# Test: Compatibility Filtering
# =============================================================================

class TestCompatibilityFiltering:
    """Tests for hardware compatibility filtering."""

    def test_get_compatible_variants_vram(self, model_db):
        """Should filter variants by VRAM."""
        model = model_db.get_model("test_model")

        # 8GB VRAM - should get fp16 and gguf_q4
        variants = model_db.get_compatible_variants(
            model, "windows_nvidia", 8000
        )
        assert len(variants) == 2  # fp16 (8000) and gguf_q4 (2000), not fp8 (needs 8.9 CC)

    def test_get_compatible_variants_platform(self, model_db):
        """Should filter variants by platform support."""
        model = model_db.get_model("test_model")

        # Mac MPS - should NOT get fp8 (not supported)
        variants = model_db.get_compatible_variants(
            model, "mac_mps", 16000
        )
        variant_ids = [v.id for v in variants]
        assert "fp8" not in variant_ids
        assert "fp16" in variant_ids

    def test_get_compatible_variants_compute_capability(self, model_db):
        """Should filter FP8 by compute capability."""
        model = model_db.get_model("test_model")

        # CC 8.9+ - should include fp8
        variants = model_db.get_compatible_variants(
            model, "windows_nvidia", 8000, compute_capability=8.9
        )
        variant_ids = [v.id for v in variants]
        assert "fp8" in variant_ids

        # CC 8.6 - should NOT include fp8
        variants = model_db.get_compatible_variants(
            model, "windows_nvidia", 8000, compute_capability=8.6
        )
        variant_ids = [v.id for v in variants]
        assert "fp8" not in variant_ids

    def test_get_compatible_variants_sorted_by_quality(self, model_db):
        """Should sort variants by quality retention (highest first)."""
        model = model_db.get_model("test_model")

        variants = model_db.get_compatible_variants(
            model, "windows_nvidia", 16000
        )

        # Should be sorted: fp16 (100%), gguf_q4 (85%)
        # Note: fp8 not included without CC
        assert variants[0].quality_retention_percent >= variants[-1].quality_retention_percent

    def test_get_compatible_models(self, model_db):
        """Should return models with compatible variants."""
        results = model_db.get_compatible_models(
            platform="windows_nvidia",
            vram_mb=16000,
            categories=["image_generation", "video_generation"],
        )

        assert len(results) == 2  # test_model and test_video_model
        for model, variant in results:
            assert variant.vram_min_mb <= 16000

    def test_get_compatible_models_vram_filter(self, model_db):
        """Should exclude models exceeding VRAM."""
        # 4GB - too low for video model (needs 12GB)
        results = model_db.get_compatible_models(
            platform="windows_nvidia",
            vram_mb=4000,
            categories=["video_generation"],
        )

        assert len(results) == 0

    def test_get_compatible_models_commercial_only(self, model_db):
        """Should filter by commercial license."""
        results = model_db.get_compatible_models(
            platform="windows_nvidia",
            vram_mb=16000,
            commercial_only=True,
        )

        for model, _ in results:
            assert model.commercial_use is True


# =============================================================================
# Test: Helper Methods
# =============================================================================

class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_required_nodes(self, model_db):
        """Should return required nodes for model+variant."""
        model = model_db.get_model("test_model")

        # fp16 variant - no extra nodes
        fp16 = model.variants[0]
        nodes = model_db.get_required_nodes(model, fp16)
        assert "ComfyUI-GGUF" not in nodes

        # gguf_q4 variant - needs ComfyUI-GGUF
        gguf = model.variants[2]
        nodes = model_db.get_required_nodes(model, gguf)
        assert "ComfyUI-GGUF" in nodes

    def test_get_paired_models(self, model_db):
        """Should return paired model IDs."""
        model = model_db.get_model("test_model")
        paired = model_db.get_paired_models(model)
        assert isinstance(paired, list)


# =============================================================================
# Test: Platform Normalization
# =============================================================================

class TestPlatformNormalization:
    """Tests for platform key normalization."""

    def test_normalize_windows_nvidia(self):
        """Should normalize Windows + NVIDIA."""
        assert normalize_platform("nvidia", "Windows") == "windows_nvidia"
        assert normalize_platform("NVIDIA", "windows") == "windows_nvidia"

    def test_normalize_mac_mps(self):
        """Should normalize macOS + Apple."""
        assert normalize_platform("apple", "Darwin") == "mac_mps"
        assert normalize_platform("apple", "macOS") == "mac_mps"

    def test_normalize_linux_rocm(self):
        """Should normalize Linux + AMD."""
        assert normalize_platform("amd", "Linux") == "linux_rocm"
        assert normalize_platform("rocm", "linux") == "linux_rocm"

    def test_normalize_linux_nvidia(self):
        """Should treat Linux + NVIDIA like Windows."""
        assert normalize_platform("nvidia", "Linux") == "windows_nvidia"

    def test_normalize_fallback(self):
        """Should fall back to windows_nvidia."""
        assert normalize_platform("unknown", "Windows") == "windows_nvidia"
        assert normalize_platform("none", "Windows") == "windows_nvidia"


# =============================================================================
# Test: Singleton
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_model_database_returns_same_instance(self):
        """Should return same instance on repeated calls."""
        # Note: This test may affect global state
        db1 = get_model_database()
        db2 = get_model_database()
        assert db1 is db2

    def test_reload_creates_new_instance(self):
        """Should create new instance on reload."""
        db1 = get_model_database()
        db2 = reload_model_database()
        # After reload, singleton is updated
        db3 = get_model_database()
        assert db2 is db3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
