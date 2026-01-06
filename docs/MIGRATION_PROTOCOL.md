# Migration & Deprecation Protocol

This document defines how to migrate from legacy code to SPEC_v3 architecture without breaking the working application, and how to implement new features from spec using test-driven development.

## Quick Reference

| Scenario | Section | Key Pattern |
|----------|---------|-------------|
| Implementing new feature from spec | [New Implementation Protocol](#new-implementation-protocol-spec--code) | TDD: Test → Fail → Implement → Pass |
| Extending a dataclass | [Schema Evolution](#schema-evolution) | Add fields with defaults |
| Replacing legacy module | [Pattern A: Parallel Module](#pattern-a-parallel-module-for-large-replacements) | Build new alongside old |
| Replacing individual function | [Pattern B: Adapter](#pattern-b-adapterfacade-for-gradual-function-replacement) | Delegate to new code |
| Need quick rollback ability | [Pattern C: Config Toggle](#pattern-c-config-driven-toggle) | Feature flag |

## Principles

1. **App must remain launchable** - Never break `python src/main.py`
2. **Parallel implementation** - Build new alongside old, switch when ready
3. **Deprecation warnings first** - Mark old code before removing
4. **Test at boundaries** - Verify behavior matches before/after swap
5. **Tests before implementation** - Write failing tests from spec, then implement

---

## New Implementation Protocol (Spec → Code)

Use this workflow when implementing new features from spec where no legacy code exists.

### Philosophy: Test-Driven Development (TDD)

We prefer TDD for spec implementation because:
- **Specs define behavior** - Tests encode that behavior before code exists
- **Prevents scope creep** - You implement exactly what the spec requires
- **Catches spec ambiguity early** - If you can't write a test, the spec needs clarification
- **Provides regression safety** - Future changes won't silently break spec compliance

### The TDD Cycle

```
┌─────────────────────────────────────────────────────────────┐
│  1. READ SPEC    →   2. WRITE TEST   →   3. RUN (FAIL)     │
│       ↑                                        ↓            │
│       │              5. REFACTOR    ←    4. IMPLEMENT      │
│       │                   ↓                    ↓            │
│       └───────────── 6. RUN (PASS) ←──────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Step-by-Step Workflow

#### Step 1: Read Spec Section Thoroughly

Before writing any code:
- Identify the spec section(s) covering this feature
- List all requirements, constraints, and edge cases
- Note any cross-references to other sections
- Identify data dependencies (what schemas/services does this need?)

**Example for CPU Detection (HARDWARE_DETECTION.md Section 3):**
```markdown
Requirements extracted:
- Detect physical/logical core counts
- Detect CPU model name and architecture
- Detect AVX/AVX2/AVX-512 support (x86 only)
- Classify into tiers: HIGH (16+), MEDIUM (8-15), LOW (4-7), MINIMAL (<4)
- Create CPUProfile dataclass
- Cross-ref: Layer 1 uses cpu_tier for offload viability
- Cross-ref: GGUF models require AVX2
```

#### Step 2: Create/Update Schema First

Schemas define the contract. Implement them before behavior:

```python
# src/schemas/hardware.py

@dataclass
class CPUProfile:
    """CPU detection results per HARDWARE_DETECTION.md Section 3."""
    model_name: str
    physical_cores: int
    logical_cores: int
    architecture: str  # "x86_64", "arm64"
    supports_avx: bool = False
    supports_avx2: bool = False
    supports_avx512: bool = False
    tier: str = "unknown"  # "high", "medium", "low", "minimal"
```

#### Step 3: Write Failing Tests from Spec

Write tests BEFORE implementation. Tests should:
- Cover each requirement from Step 1
- Include edge cases mentioned in spec
- Test error handling paths
- Use spec examples as test cases

```python
# tests/services/test_cpu_detection.py

class TestCPUTierClassification:
    """Tests for HARDWARE_DETECTION.md Section 3.3 tier classification."""
    
    def test_high_tier_16_plus_cores(self):
        """16+ physical cores → HIGH tier."""
        profile = CPUProfile(
            model_name="AMD Ryzen 9 7950X",
            physical_cores=16,
            logical_cores=32,
            architecture="x86_64"
        )
        assert classify_cpu_tier(profile) == "high"
    
    def test_medium_tier_8_to_15_cores(self):
        """8-15 physical cores → MEDIUM tier."""
        profile = CPUProfile(
            model_name="Intel i7-12700K",
            physical_cores=12,
            logical_cores=20,
            architecture="x86_64"
        )
        assert classify_cpu_tier(profile) == "medium"
    
    def test_low_tier_4_to_7_cores(self):
        """4-7 physical cores → LOW tier."""
        profile = CPUProfile(
            model_name="Intel i5-10400",
            physical_cores=6,
            logical_cores=12,
            architecture="x86_64"
        )
        assert classify_cpu_tier(profile) == "low"
    
    def test_minimal_tier_under_4_cores(self):
        """<4 physical cores → MINIMAL tier."""
        profile = CPUProfile(
            model_name="Intel Celeron",
            physical_cores=2,
            logical_cores=2,
            architecture="x86_64"
        )
        assert classify_cpu_tier(profile) == "minimal"
    
    def test_avx2_required_for_gguf_offload(self):
        """GGUF CPU offload requires AVX2 per SPEC_v3 Section 6.7.1."""
        profile = CPUProfile(
            model_name="Old CPU",
            physical_cores=8,
            logical_cores=16,
            architecture="x86_64",
            supports_avx2=False
        )
        assert not can_offload_gguf(profile)
```

#### Step 4: Run Tests (Expect Failure)

```bash
pytest tests/services/test_cpu_detection.py -v
# Expected: ImportError or NotImplementedError for missing functions
```

This confirms your tests are actually testing something.

#### Step 5: Implement Until Tests Pass

Now write the minimal code to pass tests:

```python
# src/services/hardware/cpu.py

def classify_cpu_tier(profile: CPUProfile) -> str:
    """Classify CPU tier per HARDWARE_DETECTION.md Section 3.3."""
    cores = profile.physical_cores
    if cores >= 16:
        return "high"
    elif cores >= 8:
        return "medium"
    elif cores >= 4:
        return "low"
    else:
        return "minimal"

def can_offload_gguf(profile: CPUProfile) -> bool:
    """Check GGUF offload viability per SPEC_v3 Section 6.7.1."""
    if profile.architecture == "x86_64":
        return profile.supports_avx2
    return True  # ARM doesn't require AVX
```

#### Step 6: Run Tests (Expect Pass)

```bash
pytest tests/services/test_cpu_detection.py -v
# Expected: All tests pass
```

#### Step 7: Refactor if Needed

With passing tests, you can safely refactor:
- Extract common patterns
- Improve naming
- Optimize performance

Tests catch any regressions.

#### Step 8: Verify Cross-References

Check that downstream consumers can use your implementation:

```python
# Verify Layer 1 can use CPU tier
def test_constraint_layer_uses_cpu_tier():
    """Layer 1 should check CPU tier for offload decisions."""
    hardware = HardwareProfile(
        # ... other fields
        cpu=CPUProfile(physical_cores=2, tier="minimal", supports_avx2=False)
    )
    # Minimal CPU should reject offload candidates
    result = constraint_layer.can_offload_to_cpu(candidate, hardware)
    assert result == False
```

### Test Organization

```
tests/
├── schemas/
│   └── test_hardware_schema.py      # Schema validation, defaults
├── services/
│   ├── test_cpu_detection.py        # CPU detection + tier classification
│   ├── test_storage_detection.py    # Storage detection + tier classification
│   ├── test_ram_detection.py        # RAM detection + offload calculation
│   └── test_hardware_integration.py # Full HardwareProfile construction
└── conftest.py                      # Shared fixtures (mock hardware, etc.)
```

### Test Fixtures for Hardware

Create reusable fixtures representing spec scenarios:

```python
# tests/conftest.py

import pytest
from src.schemas.hardware import HardwareProfile, CPUProfile, StorageProfile

@pytest.fixture
def workstation_hardware():
    """WORKSTATION tier per SPEC_v3 Section 4.5."""
    return HardwareProfile(
        platform="windows",
        gpu_vendor="nvidia",
        vram_gb=48,
        tier="workstation",
        cpu=CPUProfile(physical_cores=32, tier="high", supports_avx2=True),
        storage=StorageProfile(type="nvme_gen4", tier="fast", free_gb=500)
    )

@pytest.fixture
def entry_laptop_hardware():
    """ENTRY tier laptop with throttling."""
    return HardwareProfile(
        platform="windows",
        gpu_vendor="nvidia",
        vram_gb=6,
        tier="entry",
        is_laptop=True,
        sustained_performance_ratio=0.75,
        cpu=CPUProfile(physical_cores=6, tier="low", supports_avx2=True),
        storage=StorageProfile(type="sata_ssd", tier="moderate", free_gb=100)
    )

@pytest.fixture  
def apple_silicon_hardware():
    """Apple Silicon with unified memory."""
    return HardwareProfile(
        platform="darwin",
        gpu_vendor="apple",
        vram_gb=18,  # 24GB * 0.75 ceiling
        tier="professional",
        cpu=CPUProfile(physical_cores=10, tier="medium", architecture="arm64"),
        storage=StorageProfile(type="nvme_gen3", tier="fast", free_gb=200)
    )
```

### When to Skip TDD

TDD isn't always the right choice:

- **Exploratory prototyping** - When you're unsure what the solution looks like
- **UI/visual work** - Hard to test appearance meaningfully
- **External API integration** - Mock-heavy tests may not catch real issues

In these cases, write tests immediately AFTER implementation, before committing.

---

## Schema Evolution

When extending existing dataclasses (like HardwareProfile), follow these practices to avoid breaking existing code.

### Adding New Fields

Always provide defaults for new fields:

```python
# BEFORE (existing)
@dataclass
class HardwareProfile:
    platform: str
    gpu_vendor: str
    vram_gb: float
    tier: str

# AFTER (extended)
@dataclass
class HardwareProfile:
    platform: str
    gpu_vendor: str
    vram_gb: float
    tier: str
    # NEW FIELDS - all have defaults to maintain backward compatibility
    cpu: Optional[CPUProfile] = None
    storage: Optional[StorageProfile] = None
    ram_available_gb: float = 0.0
    is_laptop: bool = False
    sustained_performance_ratio: float = 1.0
```

### Nested Dataclasses

For complex additions, use nested dataclasses:

```python
@dataclass
class CPUProfile:
    """Extracted to own class for clarity and reusability."""
    model_name: str = ""
    physical_cores: int = 0
    logical_cores: int = 0
    tier: str = "unknown"
    supports_avx2: bool = False

@dataclass
class HardwareProfile:
    # ... existing fields
    cpu: Optional[CPUProfile] = None  # Optional for backward compat
```

### Update Tests First

Before changing schema:

1. **Check existing tests** - Identify tests that construct the dataclass
2. **Add new field tests** - Write tests for new fields with expected behavior
3. **Update fixtures** - Modify `conftest.py` fixtures to include new fields
4. **Run full suite** - Ensure no regressions

```python
# Test that old code still works with new schema
def test_hardware_profile_backward_compat():
    """Old construction without new fields should still work."""
    profile = HardwareProfile(
        platform="windows",
        gpu_vendor="nvidia", 
        vram_gb=24,
        tier="professional"
    )
    # New fields should have safe defaults
    assert profile.cpu is None
    assert profile.is_laptop == False
    assert profile.sustained_performance_ratio == 1.0
```

### Field Deprecation in Schemas

If renaming or removing a field:

```python
@dataclass
class HardwareProfile:
    # ... current fields
    
    # DEPRECATED: Use cpu.tier instead. Remove in v1.1
    @property
    def cpu_tier(self) -> str:
        import warnings
        warnings.warn(
            "cpu_tier is deprecated, use cpu.tier instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.cpu.tier if self.cpu else "unknown"
```

---

## Deprecation Marking

### Step 1: Mark Legacy Code

Add deprecation comments to files/functions being replaced:

```python
# DEPRECATED: This module uses single-pass scoring.
# Replacement: src/services/recommendation/constraint_layer.py (Phase 3)
# Removal target: v1.0 release
# See: SPEC_v3 Section 6

def old_scoring_function():
    """
    .. deprecated::
        Use ConstraintSatisfactionLayer.filter_candidates() instead.
        This function will be removed in v1.0.
    """
    import warnings
    warnings.warn(
        "old_scoring_function is deprecated, use ConstraintSatisfactionLayer",
        DeprecationWarning,
        stacklevel=2
    )
    # ... existing code
```

### Step 2: Track in PLAN_v3.md

Add deprecated items to a tracking table in PLAN_v3.md:

```markdown
## 8. Deprecation Tracker

| File/Function | Deprecated | Replacement | Remove By | Status |
|---------------|------------|-------------|-----------|--------|
| `scoring_service.py` | 2026-01-XX | 3-layer system | v1.0 | Pending |
| `resources.json` models | 2026-01-XX | `models_database.yaml` | v1.0 | Pending |
```

---

## Migration Patterns

### Pattern A: Parallel Module (for large replacements)

Use when replacing entire service architecture.

```
src/services/
├── scoring_service.py           # OLD - deprecated
├── recommendation_service.py    # OLD - uses scoring_service
└── recommendation/              # NEW - parallel implementation
    ├── __init__.py
    ├── constraint_layer.py      # Layer 1
    ├── content_layer.py         # Layer 2
    ├── topsis_layer.py          # Layer 3
    └── engine.py                # New orchestrator
```

**Migration steps:**
1. Build new modules in `recommendation/` subfolder
2. Add feature flag or config toggle
3. Test new path independently
4. Update callers to use new path
5. Remove old files

### Pattern B: Adapter/Facade (for gradual function replacement)

Use when replacing individual functions within a working module.

```python
# system_service.py

def get_gpu_info():
    """Legacy function - delegates to new detector."""
    # OLD implementation commented out, kept for reference
    # return _legacy_gpu_detection()
    
    # NEW implementation via adapter
    from src.services.hardware import get_detector
    detector = get_detector()
    profile = detector.detect()
    return (profile.gpu_vendor, profile.gpu_name, profile.vram_gb)
```

### Pattern C: Config-Driven Toggle

Use when you need to A/B test or rollback quickly.

```python
# config/manager.py
USE_NEW_RECOMMENDATION_ENGINE = False  # Toggle when ready

# recommendation_service.py
from src.config.manager import USE_NEW_RECOMMENDATION_ENGINE

if USE_NEW_RECOMMENDATION_ENGINE:
    from src.services.recommendation.engine import RecommendationEngine
else:
    from src.services.scoring_service import ScoringService as RecommendationEngine
```

---

## File-Specific Migration Plans

### 1. scoring_service.py → 3-layer system

| Phase | Action |
|-------|--------|
| Phase 3 Week 5 | Create `src/services/recommendation/constraint_layer.py` |
| Phase 3 Week 5 | Create `src/services/recommendation/content_layer.py` |
| Phase 3 Week 6 | Create `src/services/recommendation/topsis_layer.py` |
| Phase 3 Week 6 | Create `src/services/recommendation/engine.py` orchestrator |
| Phase 3 Week 6 | Add config toggle, test new engine |
| Phase 6 | Enable new engine by default |
| Post-v1.0 | Delete `scoring_service.py` |

### 2. resources.json models → models_database.yaml

| Phase | Action |
|-------|--------|
| Phase 1 Week 2 | Create `ModelDatabase` class reading from YAML |
| Phase 1 Week 2 | Update `recommendation_service.py` to use `ModelDatabase` |
| Phase 1 Week 2 | Mark model sections in `resources.json` as deprecated |
| Phase 4 | Verify all model reads go through `ModelDatabase` |
| Post-v1.0 | Remove model sections from `resources.json` |

### 3. system_service.py → platform-specific detectors

| Phase | Action |
|-------|--------|
| Phase 1 Week 1 | Create `src/services/hardware/base.py` with `HardwareDetector` |
| Phase 1 Week 1 | Create platform-specific detectors |
| Phase 1 Week 1 | Add `get_detector()` factory function |
| Phase 1 Week 1 | Update `SystemService.get_gpu_info()` to delegate to new detectors |
| Phase 1 Week 2 | Update `scan_full_environment()` to use new `HardwareProfile` |
| Post-v1.0 | Remove legacy detection code from `system_service.py` |

### 4. setup_wizard.py → dual-path onboarding

| Phase | Action |
|-------|--------|
| Phase 2 Week 3 | Create `src/ui/wizard/path_selector.py` |
| Phase 2 Week 3 | Create `src/ui/wizard/quick_flow.py` |
| Phase 2 Week 4 | Create `src/ui/wizard/comprehensive_flow.py` |
| Phase 2 Week 4 | Update `setup_wizard.py` to use path selector → flow |
| Phase 6 | Remove legacy single-path code |

---

## Commit Message Convention

Use conventional commits with migration context:

```
deprecate(scoring): mark scoring_service.py for removal

- Added deprecation warnings to all public functions
- Documented replacement in PLAN_v3.md Section 8
- Removal target: v1.0

migrate(models): switch to models_database.yaml

- ModelDatabase now reads from YAML
- resources.json model sections deprecated
- Existing behavior preserved via adapter

remove(scoring): delete legacy scoring_service.py

BREAKING CHANGE: scoring_service.py removed
- All callers migrated to recommendation.engine
- See SPEC_v3 Section 6 for new architecture
```

---

## Rollback Plan

If a migration causes issues:

1. **Config toggle**: Flip `USE_NEW_X = False`
2. **Git revert**: `git revert <migration-commit>`
3. **Document**: Add issue to PLAN_v3.md Risk Register

Keep deprecated code until at least one full release cycle after migration.

---

## Checklist Before Removing Deprecated Code

- [ ] New implementation passes all tests
- [ ] No remaining imports of deprecated module
- [ ] No config toggles pointing to old code
- [ ] Deprecation has been in place for at least 2 weeks
- [ ] Documented in PLAN_v3.md Section 8 as removed
