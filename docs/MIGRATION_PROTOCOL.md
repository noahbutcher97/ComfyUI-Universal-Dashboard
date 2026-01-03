# Migration & Deprecation Protocol

This document defines how to migrate from legacy code to SPEC_v3 architecture without breaking the working application.

## Principles

1. **App must remain launchable** - Never break `python src/main.py`
2. **Parallel implementation** - Build new alongside old, switch when ready
3. **Deprecation warnings first** - Mark old code before removing
4. **Test at boundaries** - Verify behavior matches before/after swap

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
